# Arquitetura do Zowsup

## Visão geral
- Projeto Python que implementa o protocolo WhatsApp multi-dispositivo, baseado em um fork do Yowsup e integrado com Axolotl/Signal (criptografia) e Noise (handshake/transport).
- Principais pastas:
  - `app/`: API de alto nível, gerenciamento de contas, ambientes, bot e camada de envio.
  - `yowsup/`: stack de protocolo WhatsApp (camadas, entidades, registradores).
  - `axolotl/`: implementação Signal (Double Ratchet, pre-keys, identities, sessions).
  - `consonance/`: implementação Noise / transporte.
  - `conf/`: configuração base (`config.conf`), constantes e metadados.
  - `script/`: entrypoints CLI (login, import/export conta, registro companion, reset 2FA).
  - `common/`: utilidades e base do console.
  - `proto/`: mensagens Protobuf usadas pelo protocolo.
  - `settings/`: configuração global via Pydantic (`ZOWSUP_*`).
  - `docs/`: guias funcionais (anti-ban, múltiplas contas, grupos, handshake).

## Configuração e isolamento
- Configuração principal vem de `Settings` (pydantic BaseSettings) em `settings/conf.py`, lendo `.env`/variáveis `ZOWSUP_*` (incluindo `ZOWSUP_CONFIG` para o arquivo conf).
- `SysVar` permanece para compatibilidade, mas valores padrões de caminho/env vêm de `Settings`.
- Caminhos são criados automaticamente (`SysVar.ensure_dirs`).
- Config global adicional via Pydantic (`settings/conf.py`), incluindo `ZOWSUP_DB_URL` (padrão `sqlite:///zowsup.db`).

## Banco de dados unificado
- SQLAlchemy (`app/db.py`) com modelos em `app/models.py`.
- Tabelas principais:
  - `accounts`: status da conta (env, login, initialized, restriction).
  - Stores Axolotl: `identities`, `prekeys`, `signed_prekeys`, `sessions`, `sender_keys`, `polls/poll_options`, `app_state_keys`.
  - Contatos e histórico: `contacts`, `trusted_contacts`, `broadcasts`, `sent_messages`.
- Helpers: `update_account_status`, `register_sent_message`, `get_sent_messages_count`, `export_contacts_to_vcard`, `get_all_imported_accounts`.
- `init_db()` cria o esquema completo.

## Ambientes e rede
- Perfis de dispositivo em `app/device_env_config/` (android, smb_android, ios, smb_ios) com user-agents/versões/FDID. `DeviceEnv` gera instâncias randômicas ou específicas.
- Rede: `NetworkEnv` suporta `direct` ou `proxy` (`host:port:user:pass`), com placeholders `[location]` e `[session_id]` para rotação dinâmica.
- `BotEnv` combina `DeviceEnv` + `NetworkEnv` para construir a identidade do bot.

## Núcleo do bot e stack
- `YowBot` (`app/yowbot.py`):
  - Constrói a stack Yowsup (`YowStackBuilder.pushDefaultLayers().push(SendLayer)`).
  - Define props de ambiente, ping interval, callbacks.
  - Registra comandos com `@BotCmd` (msg.send, msg.sendmedia, msg.revoke, account.init, md.link/md.remove, group.*, contact.sync, avatar, email, 2FA etc).
- `SendLayer` (`app/yowbot_layer.py`):
  - Implementa envio e recepção de mensagens/media/grupos/reações, app-state, history sync.
  - Watchdog de liveness e reconexão com backoff; flags para detecção de handshake falho.
  - Controles anti-ban (rate limiting por destinatário, contagem diária, invalidação de números).
  - Suporte a registro companion (QR/linkcode) via `YowQrCodeThread`.
  - Integração direta com Axolotl store e Protobuf (`wsend_pb2`, `wa_struct_pb2`).

## API de alto nível (`ZowsupClient`)
- Local: `app/api.py`. Fornece fachada programática isolada por conta.
- Construtor usa `Settings`, cria diretórios por conta, instancia `BotEnv` e stack com `SendLayer`, e conecta automaticamente (opcional).
- Operações principais:
  - `connect`/`disconnect`/`ensure_connected`.
  - Envio: `send_text`, `send_text_reply`, `send_media`, `send_reaction` (opção `wait_for_id`).
  - Grupos: `create_group`, `list_groups`, `group_add`.
  - Contatos: `sync_contacts`.
  - Inicialização: `initialize` (sequência pós-primeiro login).
  - Auto-responder: `enable_auto_reply`/`disable_auto_reply` com handler custom.
  - Importação 6-part: `import_account_from_six_parts` cria `ProfileConfig`, Axolotl store e registro em DB (reconstrói chaves e fdid/ids).
- Suporte a rotação de ambiente em falha de handshake (`_retry_connect_with_env_rotation`).

## Gerenciamento multi-conta
- `AccountManager` (`app/account_manager.py`) singleton:
  - `add_account` cria `ZowsupClient` isolado e guarda contexto SysVar.
  - `connect_in_thread` aplica contexto e conecta.
  - `connect_with_env_rotation` tenta envs em ordem (smb_android → android → smb_ios → ios).
  - `sync_all_accounts` sincroniza contatos entre contas.
  - `load_all_imported_accounts` carrega contas do DB com filtros (inic/ativas/sem restrição).

## CLI e exemplos
- Entry principal: `python script/main.py <phone> [command] [params] --env <env> --proxy host:port:user:pass`.
  - Sem comando: abre modo interativo (`CMD >`).
  - Comando direto: executa via `CmdProcess`.
- Registro companion:
  - QR: `python script/regwithscan.py`
  - Linkcode: `python script/regwithlinkcode.py <phone>`
- Import/export conta 6-part: `script/import6.py` / `script/export6.py`.
- Exemplos em `examples/`: envio, sync, múltiplas contas, exportar contatos.

## Fluxo típico (alto nível)
1) Ajustar `.env` ou variáveis `ZOWSUP_*` (ex.: `ZOWSUP_CONFIG`, `ZOWSUP_ACCOUNT_PATH`, `ZOWSUP_DEFAULT_ENV`).
2) `settings = Settings()` (autoload) → criação de `ZowsupClient` ou execução de `script/main.py`.
3) `YowBot.runAsThread()` inicia stack; `SendLayer.waitLogin()` aguarda login. Em erro de handshake, rotação automática de ambiente.
4) Envio de mensagens via `ZowsupClient` (bypass direto no SendLayer ou via comandos); pode esperar `message_id`.
5) Eventos chegam em callbacks do bot/SendLayer; auto-reply opcional; status/estatísticas persistidos no DB.

## Anti-ban e robustez
- Controles no `SendLayer`: rate limit por destinatário, contagem diária, liveness watchdog, reconexão com backoff.
- Proxy com placeholders para variar IP por sessão; troca de sessão por país/CC.
- Docs de apoio: `docs/ANTI_BAN_STRATEGY.md`, `docs/HANDSHAKE_ROTATION.md`.

## Onde estender
- Novos comandos: adicionar método em `YowBot` com `@BotCmd` e implementar no `SendLayer`.
- Novas operações de alto nível: encapsular em `ZowsupClient` usando `_run_command` ou chamando `send_layer`.
- Novos ambientes/dispositivos: adicionar perfis em `app/device_env_config` e mapear em `DeviceEnv.ENV_MAP`.
- Métricas/telemetria: aproveitar `register_sent_message` e `get_sent_messages_count`.

## Referências rápidas
- Config: `settings/conf.py` (`Settings` via `.env`/variáveis `ZOWSUP_*`).
- API: `app/api.py` (`ZowsupClient`, `ZowsupError`, `CommandResponse`).
- Bot/stack: `app/yowbot.py`, `app/yowbot_layer.py`.
- DB: `app/db.py`, `app/models.py`, `settings/conf.py` (ZOWSUP_DB_URL).
- Multi-conta: `app/account_manager.py`.
- CLI: `script/main.py` e scripts auxiliares (import/export, registro, reset 2FA).

