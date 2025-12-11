# Rotação Automática de Ambiente para Erros de Handshake

Este documento descreve o sistema implementado para detectar erros de handshake durante o login e rotacionar automaticamente entre diferentes tipos de ambiente até encontrar um que funcione.

## Problema

Erros de handshake podem ocorrer quando o tipo de ambiente (android, smb_android, ios, smb_ios) não corresponde ao que o WhatsApp espera para a conta. Isso pode resultar em falhas de conexão mesmo com credenciais válidas.

## Solução Implementada

O sistema agora detecta automaticamente erros de handshake e tenta diferentes tipos de ambiente em sequência até encontrar um que funcione.

### Tipos de Ambiente Disponíveis

1. **smb_android** - WhatsApp Business para Android (padrão recomendado)
2. **android** - WhatsApp padrão para Android
3. **smb_ios** - WhatsApp Business para iOS
4. **ios** - WhatsApp padrão para iOS

### Ordem de Tentativa

Quando há erro de handshake, o sistema tenta os ambientes na seguinte ordem:
1. smb_android
2. android
3. smb_ios
4. ios

O ambiente atual é tentado por último (após os outros).

## Funcionalidades

### 1. Detecção Automática de Erros de Handshake

O sistema detecta erros de handshake através de:
- Evento `EVENT_HANDSHAKE_FAILED` do YowNoiseLayer
- Mensagens de "failure" com reason contendo "handshake"
- Exceções `HandshakeFailedException`

### 2. Rotação Automática

Quando um erro de handshake é detectado:
1. O sistema desconecta a conta atual
2. Tenta o próximo tipo de ambiente na lista
3. Se bem-sucedido, atualiza o `env` no banco de dados
4. Se falhar, tenta o próximo ambiente
5. Continua até encontrar um que funcione ou esgotar todas as opções

### 3. Atualização Automática no Banco de Dados

Quando encontra um ambiente que funciona, o sistema:
- Atualiza o campo `env` da conta no banco de dados
- Salva o ambiente bem-sucedido para uso futuro

## Como Usar

### Método 1: AccountManager.connect_with_env_rotation()

```python
from app.account_manager import AccountManager

manager = AccountManager.get_instance()

# Conecta com rotação automática
client = manager.connect_with_env_rotation(
    "5511999999999",
    initial_env="smb_android",  # Opcional: ambiente inicial
    wait_login=True
)

if client and client.is_connected():
    print("Conectado com sucesso!")
```

### Método 2: ZowsupClient.connect() com retry_with_env_rotation

```python
from app.account_manager import AccountManager

manager = AccountManager.get_instance()
client = manager.add_account("5511999999999", env="android", auto_connect=False)

# Conecta com rotação automática
success = client.connect(
    wait_login=True,
    retry_with_env_rotation=True  # Ativa rotação automática
)
```

### Método 3: Carregar Todas as Contas com Rotação

```python
from app.account_manager import AccountManager

manager = AccountManager.get_instance()

# Carrega todas as contas
clients = manager.load_all_imported_accounts(auto_connect=False)

# Conecta cada uma com rotação automática
for phone, client in clients.items():
    client.connect(wait_login=True, retry_with_env_rotation=True)
```

## Detalhes Técnicos

### Detecção de Erros de Handshake

O sistema detecta erros de handshake em múltiplos pontos:

1. **EventCallback no SendLayer**:
   ```python
   @EventCallback(YowNoiseLayer.EVENT_HANDSHAKE_FAILED)
   def onHandshakeFailed(self, event):
       # Detecta e marca erro de handshake
   ```

2. **Verificação no onFailure**:
   ```python
   @ProtocolEntityCallback("failure")
   def onFailure(self, entity):
       # Verifica se é erro de handshake
       if "handshake" in reason.lower():
           self._handshake_error_detected = True
   ```

### Processo de Rotação

1. **Identifica ambiente atual**: Extrai o tipo do ambiente atual
2. **Cria lista de ambientes**: Remove o atual e adiciona no final
3. **Para cada ambiente**:
   - Cria novo `DeviceEnv` e `BotEnv`
   - Recria o `YowBot` com novo ambiente
   - Tenta conectar
   - Se sucesso: atualiza banco e retorna
   - Se falha: tenta próximo

### Atualização no Banco de Dados

```python
from app.db import update_account_status

# Atualiza o env quando encontra um que funciona
update_account_status(phone, env=env_name)
```

## Logs e Monitoramento

O sistema registra logs detalhados:

```
[AccountManager] Conectando 5511999999999 com rotação de ambiente. Ordem: ['smb_android', 'android', 'smb_ios', 'ios']
[AccountManager] [5511999999999] Tentando ambiente: smb_android
[ZowsupClient:5511999999999] Erro de handshake detectado, tentando rotação de ambiente...
[ZowsupClient:5511999999999] Tentando rotação de ambiente. Ordem: ['android', 'smb_ios', 'ios', 'smb_android']
[ZowsupClient:5511999999999] Tentando conectar com ambiente: android
[ZowsupClient:5511999999999] ✓ Login bem-sucedido com ambiente: android
```

## Exemplo Completo

```python
from app.account_manager import AccountManager
from loguru import logger

manager = AccountManager.get_instance()

# Carrega todas as contas
clients = manager.load_all_imported_accounts(
    auto_connect=False,
    only_initialized=True
)

# Conecta cada uma com rotação automática
for phone, client in clients.items():
    logger.info(f"Conectando {phone}...")
    
    success = client.connect(
        wait_login=True,
        retry_with_env_rotation=True  # Rotação automática
    )
    
    if success and client.is_connected():
        env_name = client.bot_env.deviceEnv.obj.__class__.__name__
        logger.info(f"✓ {phone} conectada (env: {env_name})")
    else:
        logger.warning(f"✗ {phone} falhou ao conectar")
```

## Benefícios

1. **Aumenta taxa de sucesso de login**: Tenta automaticamente diferentes ambientes
2. **Reduz intervenção manual**: Não precisa testar manualmente cada tipo
3. **Aprende o ambiente correto**: Salva o ambiente que funcionou no banco
4. **Resiliente a mudanças**: Adapta-se se o WhatsApp mudar requisitos

## Limitações

- A rotação só funciona se o erro for de handshake
- Outros tipos de erro (403, 401, etc.) não disparam rotação
- Pode demorar mais tempo (tenta até 4 ambientes)
- Requer que pelo menos um ambiente funcione

## Troubleshooting

### Rotação não está funcionando

1. **Verifique os logs**: Procure por "Erro de handshake detectado"
2. **Verifique se o evento está sendo capturado**: Procure por "onHandshakeFailed"
3. **Teste manualmente**: Tente diferentes ambientes manualmente

### Todos os ambientes falham

1. **Verifique as credenciais**: Pode ser problema de autenticação, não handshake
2. **Verifique restrições**: Conta pode estar banida/restrita
3. **Verifique conexão**: Problemas de rede podem causar falhas

## Conclusão

O sistema de rotação automática de ambiente aumenta significativamente a taxa de sucesso de login ao tentar automaticamente diferentes tipos de ambiente quando há erros de handshake. Isso reduz a necessidade de intervenção manual e melhora a experiência geral do sistema.

