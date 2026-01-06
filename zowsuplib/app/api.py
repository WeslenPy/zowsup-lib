import base64
import random
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

import names
from loguru import logger
from zowsuplib.consonance.structs.keypair import KeyPair
from zowsuplib.proto import wsend_pb2
from zowsuplib.yowsup.axolotl.factory import AxolotlManagerFactory
from zowsuplib.yowsup.common.tools import WATools
from zowsuplib.yowsup.config.v1.config import Config
from zowsuplib.yowsup.layers import YowLayerEvent
from zowsuplib.yowsup.layers.network import YowNetworkLayer
from zowsuplib.yowsup.layers.protocol_iq.layer import YowIqProtocolLayer
from zowsuplib.yowsup.profile.profile import YowProfile
from zowsuplib.yowsup.stacks import YowStackBuilder
from zowsuplib.yowsup.structs import ProtocolEntity

from zowsuplib.app import models
from zowsuplib.app.bot_env import BotEnv
from zowsuplib.app.device_env import DeviceEnv
from zowsuplib.app.message import MessageDefault
from zowsuplib.app.network_env import NetworkEnv
from zowsuplib.app.yowbot_layer import SendLayer
from zowsuplib.app.yowbot_values import YowBotType
from zowsuplib.app.db import SessionLocal, record_group
from zowsuplib.common.utils import Utils
from zowsuplib.settings.conf import settings

class ZowsupError(Exception):
    """
    Erro de alto nível disparado pela API ZowsupClient.

    Encapsula o código e a mensagem retornados pela camada de comando (YowBot).
    """

    def __init__(self, code: Optional[int], message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass
class CommandResponse:
    """
    Resultado genérico de um comando de alto nível.

    Nem todos os comandos retornam dados estruturados; em muitos casos o
    resultado será None, indicando apenas sucesso após o tempo de espera.
    """

    data: Any = None


@dataclass
class ClientConfig:
    account_path: Path
    download_path: Path
    upload_path: Path
    log_path: Path
    default_env: str
    cmd_wait: Optional[int] = None


class _CommandDispatcher:
    """
    Orquestra comandos assíncronos do SendLayer com sincronização thread-safe.
    """

    def __init__(self, log_prefix: str) -> None:
        self._handlers: Dict[str, Callable[[list, Dict[str, Any]], Any]] = {}
        self._events: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._log_prefix = log_prefix

    def register(self, name: str, handler: Callable[[list, Dict[str, Any]], Any]) -> None:
        self._handlers[name] = handler

    def call(self, name: str, params: Optional[list], options: Optional[Dict[str, Any]]):
        params = params or []
        options = options or {}

        handler = self._handlers.get(name)
        if handler is None:
            return None, {"code": -2, "msg": "Command Not Found"}

        try:
            cmd_id = handler(params, options)
        except Exception as exc:
            logger.error(f"{self._log_prefix} Erro ao executar comando {name}: {exc}", exc_info=True)
            return None, {"code": -1, "msg": str(exc)}

        if cmd_id is None:
            return None, {"code": -3, "msg": "No CmdId Return"}

        # Sempre cria evento para aguardar resultados (100% orientado a eventos)
        # Mesmo "JUSTWAIT" pode ter resultados assíncronos
        if cmd_id not in ("TIMEOUT",):
            with self._lock:
                if cmd_id not in self._events:
                    self._events[cmd_id] = {"event": threading.Event()}

        return cmd_id, None

    def set_result(self, cmd_id: str, result: Any) -> None:
        with self._lock:
            obj = self._events.get(cmd_id, {"event": threading.Event()})
            obj["result"] = result
            obj["event"].set()
            self._events[cmd_id] = obj

    def set_error(self, cmd_id: str, error: Any) -> None:
        with self._lock:
            obj = self._events.get(cmd_id, {"event": threading.Event()})
            obj["error"] = error
            obj["event"].set()
            self._events[cmd_id] = obj

    def wait_result(self, cmd_id: str, wait_time: int):
        """
        Aguarda resultado de um comando via evento (100% orientado a eventos).
        
        Se o evento não existir ainda, cria um para aguardar resultados assíncronos.
        """
        with self._lock:
            obj = self._events.get(cmd_id)
            if obj is None:
                # Cria evento se não existir (para comandos que retornam JUSTWAIT)
                obj = {"event": threading.Event()}
                self._events[cmd_id] = obj
        
        event = obj["event"]
        if not event.wait(wait_time):
            # Timeout: remove evento se não houve resultado
            with self._lock:
                self._events.pop(cmd_id, None)
            return None, {"code": -999, "msg": "timeout"}

        with self._lock:
            obj = self._events.pop(cmd_id, obj)

        if "error" in obj:
            return None, obj["error"]
        return obj.get("result"), None


@dataclass
class _SendLayerBotAdapter:
    """
    Adaptador mínimo para que o SendLayer funcione sem YowBot.
    """

    client: "ZowsupClient"
    botId: str
    bot_type: Any = YowBotType.TYPE_RUN_AUTO
    callback: Optional[Callable] = None
    idType: int = ProtocolEntity.ID_TYPE_ANDROID
    wa_old: Optional[str] = None
    pairLinkCode: Optional[str] = None
    pairPhoneNumber: Optional[str] = None
    _stack: Any = None

    def __post_init__(self) -> None:
        # Compat: alguns fluxos acessam bot_api.botId
        self.bot_api = self

    def setCmdResult(self, cmdId: str, result: Any) -> None:
        self.client._set_cmd_result(cmdId, result)

    def setCmdError(self, cmdId: str, error: Any) -> None:
        self.client._set_cmd_error(cmdId, error)


class ZowsupClient:
    """
    Cliente de alto nível para uso programático do Zowsup.
    
    Cada instância de ZowsupClient é completamente isolada:
    - Profile isolado (YowProfile)
    - Stack isolado (YowStack)
    - Bot isolado (YowBot)
    - SendLayer isolado
    - Callbacks isolados
    - Estado de conexão isolado
    
    Para gerenciar múltiplas contas simultaneamente, use AccountManager:
    
        from zowsuplib.app.account_manager import AccountManager
        
        manager = AccountManager.get_instance()
        client1 = manager.add_account("5511999999999")
        client2 = manager.add_account("5511888888888")

    Exemplos de uso:

        from zowsuplib.app.api import ZowsupClient

        # Uso básico
        client = ZowsupClient(account_id="5511999999999")
        client.connect()
        client.send_text("5511888888888", "Olá do Zowsup!")
        client.disconnect()

        # Auto responder
        client = ZowsupClient(account_id="5511999999999")
        client.connect()
        client.enable_auto_reply("Olá! Estou ocupado no momento.")
        # ... o bot responderá automaticamente às mensagens recebidas
        client.disable_auto_reply()
    """

    @staticmethod
    def import_account_from_six_parts(
        six_parts_data: str,
        *,
        env: str = "android",
        config_path: Optional[str] = None,
    ) -> str:
        """
        Importa uma conta nova a partir de uma string no formato 6-parts.

        A string deve ter 6 campos separados por vírgula, no formato gerado
        pelo script export6.py:

            phone,pk1,sk1,pk2,sk2,sixth

        Retorna o número de telefone (account_id) da conta importada.

        A importação realiza, em alto nível:
        - verifica se a conta já existe no banco de dados (se sim, retorna sem importar)
        - cria/atualiza o registro da conta no DB unificado (`Account`)
        - persiste a configuração de perfil (Config) em `ProfileConfig`
        - grava as chaves de identidade locais na store Axolotl (SqlAxolotlStore)
        """

        parts = [p.strip() for p in six_parts_data.split(",")]
        if len(parts) != 6:
            raise ValueError("6-parts-account-data inválido: esperado 6 campos separados por vírgula")

        phone, pk1, sk1, pk2, sk2, sixth = parts
        
        # Verifica se a conta já existe no banco de dados
        db_session = SessionLocal()
        try:
            existing_id = db_session.query(models.Account.id).filter_by(phone=phone).scalar()
            if existing_id is not None:
                logger.info(f"Conta {phone} já existe no banco de dados, pulando importação")
                return phone
        except Exception as e:
            logger.warning(f"Erro ao verificar se conta {phone} existe: {e}, continuando com importação")
        finally:
            db_session.close()
        
        logger.info(f"Importando conta {phone}...")

        # Reconstrói o client_static_keypair a partir de pk1/sk1 (mesma lógica de import6.py)
        client_static_keypair_str = base64.b64encode(
            base64.b64decode(sk1) + base64.b64decode(pk1)
        ).decode()
        kp = KeyPair.from_bytes(base64.b64decode(client_static_keypair_str))

        # Decodifica o sexto campo e extrai o id (últimos 20 bytes)
        if len(sixth) % 4 != 0:
            sixth = sixth + "=" * (4 - len(sixth) % 4)
        sixth_bytes = base64.b64decode(sixth)
        account_id_bytes = sixth_bytes[-20:]

        # Cria um ambiente mínimo apenas para gerar fdid de forma consistente
        device_env = DeviceEnv(env, random=True)
        network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)
        fake_bot_env = BotEnv(deviceEnv=device_env, networkEnv=network_env)

        # Deriva país (código de chamada) e escolhe um par mcc/mnc plausível
        cc = Utils.getMobileCC(phone)
        mccmnc = Utils.getMccMnc(cc) if cc else {"mcc": "000", "mnc": "000"}

        config = Config(
            pushname=names.get_full_name() + "X",
            cc=cc,
            mcc=mccmnc["mcc"],
            mnc=mccmnc["mnc"],
            sim_mcc=mccmnc["mcc"],
            sim_mnc=mccmnc["mnc"],
            phone=phone,
            client_static_keypair=kp,
            fdid=WATools.generatePhoneId(fake_bot_env),
            expid=WATools.generateDeviceId(),
            id=account_id_bytes,
            os_name=device_env.getOSName(),
            os_version=device_env.getOSVersion(),
            manufacturer=device_env.getManufacturer(),
            device_name=device_env.getDeviceName2(),
            device_model_type=device_env.getDeviceModelType(),
        )

        # Garante que a conta exista e atualiza alguns metadados básicos
        db_session = SessionLocal()
        try:
            account = db_session.query(models.Account).filter_by(phone=phone).one_or_none()
            if account is None:
                account = models.Account(phone=phone)
                db_session.add(account)
            account.pushname = config.pushname
            account.env = env
            # Inicializa os campos de status com valores padrão
            account.is_logged_in = False
            account.has_restriction = False
            account.is_initialized = False
            db_session.commit()
        finally:
            db_session.close()

        # Persiste a configuração do perfil usando o mecanismo padrão (ProfileConfig em DB)
        profile = YowProfile(phone)
        profile.write_config(config)

        # Atualiza as chaves de identidade na base Axolotl (store unificada)
        db = AxolotlManagerFactory().get_manager(phone, phone)

        pub_raw = base64.b64decode(pk2)
        if len(pub_raw) == 32:
            pub_key = b"\x05" + pub_raw
        else:
            logger.info("6-parts account pode estar em formato não padrão; usando chave pública como recebido")
            pub_key = pub_raw

        priv_key = base64.b64decode(sk2)

        # Backend único (SqlAxolotlStore) – grava identidade local no DB
        db._store.updateLocalIdentityKeys(db.registration_id, pub_key, priv_key, deviceid=0)

        logger.info(f"Conta {phone} importada com sucesso no DB unificado")
        return phone

    @staticmethod
    def delete_account(account_id: str, *, remove_files: bool = True) -> bool:
        """
        Remove completamente uma conta do sistema.
        
        Esta função remove:
        - A conta do banco de dados (Account e todos os dados relacionados via CASCADE)
        - A conta do AccountManager se estiver ativa
        - Desconecta a conta se estiver conectada
        - Remove diretórios de arquivos (download, upload, log) se remove_files=True
        - Remove arquivos de perfil se existirem
        
        Args:
            account_id: Número da conta (phone) a ser removida
            remove_files: Se True, remove também diretórios e arquivos relacionados
        
        Returns:
            True se a conta foi removida com sucesso, False se a conta não existia
        
        Example:
            # Remove completamente uma conta
            ZowsupClient.delete_account("5511999999999")
            
            # Remove apenas do banco de dados, mantendo arquivos
            ZowsupClient.delete_account("5511999999999", remove_files=False)
        """
        from zowsuplib.app.account_manager import AccountManager
        
        logger.info(f"Removendo conta {account_id} completamente...")
        
        # 1. Verifica se a conta existe no banco de dados
        db_session = SessionLocal()
        try:
            account = db_session.query(models.Account).filter_by(phone=account_id).one_or_none()
            if account is None:
                logger.warning(f"Conta {account_id} não encontrada no banco de dados")
                return False
        except Exception as e:
            logger.error(f"Erro ao verificar se conta {account_id} existe: {e}")
            return False
        finally:
            db_session.close()
        
        # 2. Remove do AccountManager se estiver ativo e desconecta
        try:
            manager = AccountManager.get_instance()
            if manager.has_account(account_id):
                logger.info(f"Desconectando e removendo conta {account_id} do AccountManager")
                manager.remove_account(account_id, disconnect=True)
        except Exception as e:
            logger.warning(f"Erro ao remover conta {account_id} do AccountManager: {e}")
        
        # 4. Remove do banco de dados (CASCADE remove todos os dados relacionados)
        db_session = SessionLocal()
        try:
            account = db_session.query(models.Account).filter_by(phone=account_id).one_or_none()
            if account:
                db_session.delete(account)
                db_session.commit()
                logger.info(f"Conta {account_id} removida do banco de dados com sucesso")
                return True
            else:
                logger.warning(f"Conta {account_id} não encontrada no banco de dados para remoção")
                return False
        except Exception as e:
            db_session.rollback()
            logger.error(f"Erro ao remover conta {account_id} do banco de dados: {e}")
            return False
        finally:
            db_session.close()

    def _build_account_config(self) -> ClientConfig:
        """
        Cria configuração isolada por conta (sem AppConfig).
        """
        account_dir = Path(settings.account_path)
        download_dir = Path(settings.download_path) / self.account_id
        upload_dir = Path(settings.upload_path) / self.account_id
        log_dir = Path(settings.log_path) / self.account_id

        for path in (account_dir, download_dir, upload_dir, log_dir):
            path.mkdir(parents=True, exist_ok=True)

        return ClientConfig(
            account_path=account_dir,
            download_path=download_dir,
            upload_path=upload_dir,
            log_path=log_dir,
            default_env=settings.default_env,
            cmd_wait=settings.cmd_wait,
        )

    def _bind_sysvar_context(self) -> None:
        """Compat: não usa mais SysVar; mantido para chamadas existentes."""
        return None

    # ------------------------------------------------------------------ #
    # Infra de SendLayer (sem YowBot)                                    #
    # ------------------------------------------------------------------ #

    def _build_id_type(self, device_env: DeviceEnv) -> int:
        return (
            ProtocolEntity.ID_TYPE_ANDROID
            if device_env.getOSName() in ["Android", "SMBA"]
            else ProtocolEntity.ID_TYPE_IOS
        )

    def _default_bot_callback(
        self,
        event=None,
        message=None,
        cmdresult=None,
        logger=logger,
        caller=None,
    ):
        """
        Callback padrão usado pelo SendLayer (compat com assinatura esperada).
        """
        try:
            if cmdresult is not None:
                logger.info(cmdresult)

            if event is not None:
                if event.HasField("contact_update"):
                    logger.info(
                        f"Contact {event.contact_update.target} notification:  "
                        f"{event.contact_update.key} : {event.contact_update.value}"
                    )
                elif event.HasField("msg_log"):
                    if event.msg_log.error_code:
                        logger.info(
                            f"MsgLog {wsend_pb2.MsgLogItem.Status.Name(event.msg_log.status)}"
                            f"-{event.msg_log.error_code} (ID={event.msg_log.msg_id}) from {event.bot_id}"
                        )
                    else:
                        logger.info(
                            f"MsgLog {wsend_pb2.MsgLogItem.Status.Name(event.msg_log.status)}"
                            f"(ID={event.msg_log.msg_id}) from {event.msg_log.target}"
                        )
                else:
                    logger.info(
                        f"Event {wsend_pb2.BotEvent.Event.Name(event.event)} from {event.bot_id}"
                    )

            if message is not None:
                if message.HasField("participant"):
                    src = f"{message.sender}::{message.participant}"
                else:
                    src = message.sender
                dst = message.target
                if message.HasField("text_message"):
                    logger.info(
                        f'Receive text message "{message.text_message.text}" from {src} to {dst}'
                    )
                else:
                    logger.info(
                        f"Receive {wsend_pb2.Message.Type.Name(message.type)} message from {src} to {dst}"
                    )
        except Exception as exc:  # pragma: no cover - defensivo
            logger.error(f"Erro no callback padrão: {exc}", exc_info=True)

    def _init_send_layer_stack(
        self, device_env: DeviceEnv, network_env: NetworkEnv
    ) -> None:
        """
        Constrói o stack Yowsup diretamente com SendLayer (sem YowBot).
        """
        self.bot_env = BotEnv(deviceEnv=device_env, networkEnv=network_env)
        self.bot = _SendLayerBotAdapter(
            client=self,
            botId=self.account_id,
            bot_type=YowBotType.TYPE_RUN_AUTO,
            callback=self._default_bot_callback,
        )

        self.send_layer = SendLayer(self.bot)

        # Perfil isolado por conta (compat com YowBot)
        profile = YowProfile(self.account_id)
        self.send_layer.db = profile.axolotl_manager

        stack_builder = YowStackBuilder()
        self._stack = stack_builder.pushDefaultLayers().push(self.send_layer).build()

        # Linka stack no adapter (para callbacks internos do SendLayer)
        self.bot._stack = self._stack

        id_type = self._build_id_type(device_env)
        self.bot.idType = id_type

        self._stack.setProp("env", self.bot_env)
        self._stack.setProp("ID_TYPE", id_type)
        self._stack.setProp("botId", self.account_id)
        self._stack.setProp(YowIqProtocolLayer.PROP_PING_INTERVAL, 30)
        self._stack.setProp("botType", self.bot.bot_type)
        self._stack.setProp("profile", profile)
        self._stack.setProfile(profile)

        self.send_layer.handshake_failed_callback = self._on_handshake_failed

        # Dispatcher central para comandos e eventos assíncronos
        self._dispatcher = _CommandDispatcher(self._log_prefix)
        self._register_command_handlers()

    def _start_stack_thread(self) -> threading.Thread:
        """
        Inicia o loop do stack em thread dedicada.
        """
        def _runner():
            self._run_stack_loop()

        t = threading.Thread(
            target=_runner, name=f"stack-{self.account_id}", daemon=True
        )
        t.start()
        return t

    def _run_stack_loop(self) -> None:
        """
        Executa o loop do stack (equivalente ao YowBot.run()).
        """
        logger.info(f"{self._log_prefix} Login start")
        try:
            self._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
            self._stack.loop()
            logger.info(f"{self._log_prefix} LOOP ENDED")
        except Exception as exc:  # pragma: no cover - defensivo
            logger.error(f"{self._log_prefix} Erro no loop do stack: {exc}", exc_info=True)
            try:
                self.disconnect()
            except Exception:
                pass

    def _register_command_handlers(self) -> None:
        """
        Registra os handlers de comando no dispatcher.
        """
        handlers: Dict[str, Callable[[list, Dict[str, Any]], Any]] = {
            "msg.send": self.send_layer.sendMsg,
            "msg.sendmedia": self.send_layer.sendMediaMsg,
            "status.send": self.send_layer.sendStatus,
            "status.sendmedia": self.send_layer.sendStatusMedia,
            "group.create": self.send_layer.createGroup,
            "group.list": self.send_layer.listGroups,
            "group.add": self.send_layer.groupAdd,
            "group.info": self.send_layer.groupInfo,
            "group.getinvite": self.send_layer.getGroupInvite,
            "group.join": self.send_layer.joinGroupWithCode,
            "contact.sync": self.send_layer.syncContacts,
            "account.init": self._command_account_init,
            "integrity.check": self.send_layer.integrityCheck,
        }
        for name, handler in handlers.items():
            self._dispatcher.register(name, handler)

    def _execute_command(
        self, name: str, params: Optional[list], options: Optional[Dict[str, Any]]
    ):
        """
        Executa um comando registrado no dispatcher.
        """
        return self._dispatcher.call(name, params, options)

    def _set_cmd_result(self, cmd_id: str, result: Any) -> None:
        """
        Recebe resultados enviados pelo SendLayer (callback de IQs).
        """
        self._dispatcher.set_result(cmd_id, result)

    def _set_cmd_error(self, cmd_id: str, error: Any) -> None:
        self._dispatcher.set_error(cmd_id, error)

    def _get_cmd_result(self, cmd_id: str, wait_time: int):
        return self._dispatcher.wait_result(cmd_id, wait_time)

    @staticmethod
    def _extract_group_id(data: Dict[str, Any]) -> Optional[str]:
        return data.get("groupId") 

    def _command_account_init(self, params: list, options: Dict[str, Any]):
        """
        Implementa o fluxo antigo de account.init sem YowBot.
        """
        # Gera um cmd_id único para este comando
        cmd_id = str(uuid.uuid4())
        
        # Executa a inicialização de forma assíncrona para não bloquear
        def _init_async():
            try:
                name = params[0] if params else None
                time.sleep(1)  # Delay operacional para estabilização
                self.send_layer.getConfig(params, options)
                time.sleep(2)  # Delay operacional para estabilização
                self._set_self_name(name)

                if self.account_id:
                    from zowsuplib.app.db import update_account_status
                    update_account_status(self.account_id, is_initialized=True)
                
                # Define resultado após completar (orientado a eventos)
                result = {"status": "ok", "message": "Account initialized successfully"}
                self._set_cmd_result(cmd_id, result)
            except Exception as e:
                logger.error(f"{self._log_prefix} Erro ao inicializar conta: {e}", exc_info=True)
                self._set_cmd_error(cmd_id, {"code": -1, "msg": str(e)})
        
        # Executa em thread separada para não bloquear
        thread = threading.Thread(target=_init_async, daemon=True)
        thread.start()
        
        return cmd_id

    def _set_self_name(self, name: Optional[str] = None) -> None:
        """
        Ajusta o pushname da conta, compatível com o fluxo antigo do YowBot.
        """
        chosen_name = name or names.get_full_name()
        profile = self._stack.getProp("profile")
        profile.config.pushname = chosen_name
        profile.write_config(profile.config)

        if self.bot_env.deviceEnv.getOSName() in ["SMBA", "SMB iOS"]:
            try:
                self.send_layer.setBusinessName([chosen_name], {})
            except Exception as exc:
                logger.warning(f"{self._log_prefix} Erro ao definir nome de negócio: {exc}")

    def __init__(
        self,
        account_id: str,
        *,
        env: Optional[str] = None,
        proxy: Optional[str] = None,
        auto_connect: bool = False,
    ) -> None:
        """
        Cria um novo cliente de alto nível completamente isolado.

        - account_id: número da conta (como string, ex: "5511999999999")
        - env: nome do ambiente de device (android, ios, smb_android, smb_ios)
        - proxy: string de proxy no formato "host:port:username:password" ou "DIRECT"
        - auto_connect: se True, já inicia a conexão e espera login
        
        Cada instância é completamente isolada - pode criar múltiplas sem conflitos.
        """
        self.account_id = account_id
        self._log_prefix = f"[ZowsupClient:{account_id}]"
        
        logger.info(f"{self._log_prefix} Inicializando cliente isolado (env={env}, proxy={'DIRECT' if not proxy or proxy.upper() == 'DIRECT' else 'PROXY'})")
        
        # Cria config isolada por conta (sem AppConfig)
        self.config = self._build_account_config()
        # Resolve env: prioridade para argumento, depois env salvo na Account, depois default
        account_env = None
        if env is None:
            try:
                with SessionLocal() as _db:
                    account_env = (
                        _db.query(models.Account.env)
                        .filter_by(phone=account_id)
                        .scalar()
                    )
            except Exception as exc:
                logger.warning(f"{self._log_prefix} Não foi possível ler env da conta no DB: {exc}")

        device_env_name = env or account_env or self.config.default_env
        device_env = DeviceEnv(device_env_name, random=True)

        if proxy and proxy.upper() != "DIRECT":
            network_env = NetworkEnv(NetworkEnv.TYPE_PROXY, proxyStr=proxy)
            logger.debug(f"{self._log_prefix} Usando proxy: {proxy}")
        else:
            network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)
            logger.debug(f"{self._log_prefix} Usando conexão direta (sem proxy)")

        # Constrói stack direto com SendLayer (sem YowBot)
        self._init_send_layer_stack(device_env, network_env)

        self._started = False
        self._stack_thread: Optional[threading.Thread] = None
        # Histórico de ambientes que já conectaram com sucesso (não rotacionar se já funcionou)
        self._successful_envs: Set[str] = set()
        self._auto_reply_enabled = False
        self._auto_reply_config: Optional[Dict[str, Any]] = None
        self._original_callback = self.bot.callback
        self._last_login_error: Optional[str] = None

        logger.info(f"{self._log_prefix} Cliente inicializado com sucesso (isolado)")

        if auto_connect:
            logger.debug(f"{self._log_prefix} auto_connect=True, conectando automaticamente")
            self.connect(wait_login=True)
            self.initialize()

    # ------------------------------------------------------------------ #
    # Ciclo de vida / conexão
    # ------------------------------------------------------------------ #

    def _default_wait_time(self, command_name: str) -> int:
        """
        Calcula tempo padrão de espera para comandos, compatível com CLI.
        """
        if self.config.cmd_wait is not None:
            return self.config.cmd_wait

        # Ajustes específicos para alguns comandos conhecidos
        if command_name in ("account.init", "init"):
            return 10
        if command_name in ("md.link", "mdlink"):
            return 60
        if command_name in ("status.send", "status.sendmedia"):
            return 30  # Timeout padrão para status

        if command_name in ("login",):
            return 120

        return 20

    def connect(self, wait_login: bool = True, retry_with_env_rotation: bool = True) -> bool:
        """
        Inicia o bot em thread separada e, opcionalmente, espera o login.
        
        Se retry_with_env_rotation=True e houver erro de handshake, tenta
        automaticamente outros tipos de ambiente.

        Retorna True se o login foi concluído com sucesso dentro do timeout
        padrão, False em caso de timeout.
        """
        self._bind_sysvar_context()

        if self._started:
            logger.debug(f"{self._log_prefix} Já está conectado, ignorando chamada")
            return True

        logger.info(f"{self._log_prefix} Iniciando conexão (wait_login={wait_login}, retry_with_env_rotation={retry_with_env_rotation})")
        self._last_login_error = None
        if hasattr(self.send_layer, "_last_stream_conflict"):
            self.send_layer._last_stream_conflict = False
        if hasattr(self.send_layer, "_last_iq_error"):
            self.send_layer._last_iq_error = None
        
        # Configura callback para detectar erros de handshake
        if retry_with_env_rotation:
            self.send_layer.handshake_failed_callback = self._on_handshake_failed
        self._stack_thread = self._start_stack_thread()
        self._started = True

        if not wait_login:
            logger.debug(f"{self._log_prefix} Conexão iniciada (sem esperar login)")
            return True

        wait_time = self._default_wait_time("login")
        logger.debug(f"{self._log_prefix} Aguardando login (timeout base={wait_time}s)")
        # waitLogin agora usa timeout adaptativo internamente
        ok = self.send_layer.waitLogin()
        
        # Se falhou e retry_with_env_rotation está ativo, verifica se foi erro de handshake
        if not ok and retry_with_env_rotation:
            if getattr(self.send_layer, "_handshake_error_detected", False):
                logger.warning(f"{self._log_prefix} Erro de handshake detectado, tentando rotação de ambiente...")
                return self._retry_connect_with_env_rotation()
        
        # Marca ambiente atual como bem-sucedido (para evitar rotação futura deste env)
        if ok:
            current_env_name = self._get_current_env_name()
            self._mark_env_success(current_env_name)
            self._last_login_error = None
        
        if not ok:
            logger.warning(f"{self._log_prefix} Login timeout após {wait_time}s")
            # Verifica erros IQ primeiro (podem ocorrer durante a conexão)
            iq_error = getattr(self.send_layer, "_last_iq_error", None)
            if iq_error:
                self._last_login_error = iq_error
            elif getattr(self.send_layer, "_handshake_error_detected", False):
                self._last_login_error = "handshake_failed"
            elif getattr(self.send_layer, "_last_stream_conflict", False):
                self._last_login_error = "conflict_replaced"
            else:
                self._last_login_error = "timeout_or_unknown"
        else:
            logger.info(f"{self._log_prefix} Login concluído com sucesso")
        return ok

    def login_without_message_notifications(
        self,
        *,
        retry_with_env_rotation: bool = True,
    ) -> bool:
        """
        Realiza o login desativando notificações de mensagens recebidas.

        Útil para cenários em que o cliente só precisa enviar mensagens ou
        inicializar a sessão sem processar callbacks de mensagens (ex.: workers
        headless).

        Args:
            retry_with_env_rotation: tenta rotação de ambiente em caso de erro
                de handshake (mesma semântica de `connect`).

        Returns:
            True se o login foi concluído com sucesso; False em caso de timeout.
        """
        if self.send_layer is None:
            raise ZowsupError(-1, "SendLayer não disponível")

        try:
            self.send_layer.disableMessageNotifications()
            logger.info(f"{self._log_prefix} Notificações de mensagem desativadas antes do login")
        except Exception as exc:  # pragma: no cover - defensivo
            logger.warning(f"{self._log_prefix} Não foi possível desativar notificações de mensagem: {exc}")

        return self.connect(wait_login=True, retry_with_env_rotation=retry_with_env_rotation)

    def get_last_login_error(self) -> Optional[str]:
        """
        Retorna o último erro de login detectado:
        - None: último login bem-sucedido
        - "handshake_failed": erro de handshake
        - "conflict_replaced": sessão substituída por outra conexão
        - "iq_error_463_account_reachout_restricted": conta com restrição de alcance (erro IQ 463)
        - "iq_error_<code>_<text>": outros erros IQ detectados
        - "timeout_or_unknown": não conectou dentro do tempo ou erro não identificado
        """
        # Verifica se há erro IQ mais recente que o erro de login
        iq_error = getattr(self.send_layer, "_last_iq_error", None)
        if iq_error:
            return iq_error
        return self._last_login_error
    
    def get_last_iq_error(self) -> Optional[str]:
        """
        Retorna o último erro IQ detectado (pode ocorrer durante ou após o login):
        - None: nenhum erro IQ detectado
        - "iq_error_463_account_reachout_restricted": conta com restrição de alcance
        - "iq_error_<code>_<text>": outros erros IQ detectados
        """
        return getattr(self.send_layer, "_last_iq_error", None)

    def disable_message_notifications(self) -> None:
        """
        Desativa as notificações de mensagem.
        """
        self.send_layer.disableMessageNotifications()
        logger.info(f"{self._log_prefix} Notificações de mensagem desativadas")
    def enable_message_notifications(self) -> None:
        """
        Reativa as notificações de mensagem.
        """
        self.send_layer.enableMessageNotifications()
        logger.info(f"{self._log_prefix} Notificações de mensagem reativadas")

    def connect_in_thread(self, *, wait_login: bool = True, retry_with_env_rotation: bool = True) -> threading.Thread:
        """
        Inicia a conexão desta conta em uma thread dedicada, aplicando o contexto SysVar correto.
        """
        def _run():
            self._bind_sysvar_context()
            try:
                self.connect(wait_login=wait_login, retry_with_env_rotation=retry_with_env_rotation)
            except Exception as exc:  # pragma: no cover - defensivo
                logger.error(f"{self._log_prefix} Erro ao conectar em thread: {exc}", exc_info=True)

        t = threading.Thread(target=_run, name=f"connect-{self.account_id}", daemon=True)
        t.start()
        return t

    def ensure_connected(
        self,
        *,
        auto_connect: bool = True,
        wait_login: bool = True,
        retry_with_env_rotation: bool = True,
        use_thread: bool = True,
    ) -> bool:
        """
        Fallback: garante que a conta esteja conectada, disparando conexão se necessário.

        Returns True se já estava conectada ou se o fluxo de conexão foi iniciado.
        """
        self._bind_sysvar_context()

        if self.is_connected():
            return True

        if not auto_connect:
            logger.debug(f"{self._log_prefix} Conta desconectada e auto_connect desabilitado")
            return False

        if use_thread:
            self.connect_in_thread(wait_login=wait_login, retry_with_env_rotation=retry_with_env_rotation)
            return True

        return self.connect(wait_login=wait_login, retry_with_env_rotation=retry_with_env_rotation)
    
    def _on_handshake_failed(self, reason=None, bot_id=None):
        """Callback chamado quando há erro de handshake."""
        logger.error(f"{self._log_prefix} Handshake falhou: {reason}")
    
    def _get_current_env_name(self) -> str:
        """Retorna o nome curto do ambiente atual."""
        env_map = {
            "EnvAndroid": "android",
            "EnvSmbAndroid": "smb_android",
            "EnvIos": "ios",
            "EnvSmbIos": "smb_ios"
        }
        current_env = self.bot_env.deviceEnv.obj.__class__.__name__
        return env_map.get(current_env, "smb_android")

    def _mark_env_success(self, env_name: str) -> None:
        """Marca um ambiente como já conectado com sucesso."""
        self._successful_envs.add(env_name)

    def _retry_connect_with_env_rotation(self) -> bool:
        """
        Tenta reconectar com diferentes tipos de ambiente quando há erro de handshake.
        
        Returns:
            True se conseguiu conectar com algum ambiente, False caso contrário
        """
        self._bind_sysvar_context()

        from zowsuplib.app.device_env import DeviceEnv
        from zowsuplib.app.bot_env import BotEnv
        from zowsuplib.app.network_env import NetworkEnv
        from zowsuplib.app.db import update_account_status
        
        # Lista de ambientes para tentar (ordem de prioridade)
        env_types = ["smb_android", "android", "smb_ios", "ios"]
        
        # Remove o ambiente atual da lista
        current_env_name = self._get_current_env_name()
        
        # Se este ambiente já conectou com sucesso antes, não rotacionar
        if current_env_name in self._successful_envs:
            logger.warning(f"{self._log_prefix} Ambiente '{current_env_name}' já teve sucesso antes; não será realizada rotação.")
            return False
        
        # Reordena para tentar o atual por último
        if current_env_name in env_types:
            env_types.remove(current_env_name)
            env_types.append(current_env_name)  # Tenta o atual por último
        
        logger.info(f"{self._log_prefix} Tentando rotação de ambiente. Ordem: {env_types}")
        
        # Desconecta antes de tentar novamente
        try:
            self.disconnect()
            time.sleep(2)  # Aguarda desconexão completa
        except:
            pass
        
        for env_name in env_types:
            try:
                logger.info(f"{self._log_prefix} Tentando conectar com ambiente: {env_name}")
                
                # Cria novo ambiente
                device_env = DeviceEnv(env_name, random=True)
                network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)
                
                # Recria stack/SendLayer direto
                self._init_send_layer_stack(device_env, network_env)
                self.send_layer.handshake_failed_callback = self._on_handshake_failed
                self.send_layer._handshake_error_detected = False  # Reset flag
                self._started = False
                
                # Tenta conectar
                self._stack_thread = self._start_stack_thread()
                self._started = True
                
                wait_time = self._default_wait_time("login")
                ok = self.send_layer.waitLogin()
                
                if ok:
                    logger.info(f"{self._log_prefix} ✓ Login bem-sucedido com ambiente: {env_name}")
                    
                    # Atualiza o env no banco de dados
                    update_account_status(self.account_id, env=env_name)
                    
                    # Atualiza o bot_env local (já setado dentro de _init_send_layer_stack)
                    # Marca sucesso para não rotacionar esse env no futuro
                    self._mark_env_success(env_name)
                    
                    return True
                else:
                    logger.warning(f"{self._log_prefix} ✗ Falha ao conectar com ambiente: {env_name}")
                    # Verifica se foi erro de handshake novamente
                    if self.send_layer._handshake_error_detected:
                        logger.warning(f"{self._log_prefix} Erro de handshake persistente com {env_name}")
                    else:
                        # Pode ser outro tipo de erro, mas ainda tenta próximo ambiente
                        pass
                
                # Desconecta antes de tentar próximo
                try:
                    self.disconnect()
                    time.sleep(1)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"{self._log_prefix} Erro ao tentar ambiente {env_name}: {e}", exc_info=True)
                try:
                    self.disconnect()
                    time.sleep(1)
                except:
                    pass
                continue
        
        logger.error(f"{self._log_prefix} ✗ Falha ao conectar com todos os tipos de ambiente testados")
        return False

    def disconnect(self) -> None:
        """
        Encerra a conexão do bot de forma controlada.
        """
        if not self._started:
            logger.debug(f"{self._log_prefix} Já está desconectado, ignorando chamada")
            return
        
        logger.info(f"{self._log_prefix} Desconectando...")
        try:
            self.send_layer.userQuit = True
            self.send_layer.setProp("FORCEQUIT", 1)
            if self._stack is not None:
                self._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
            else:
                self.send_layer.onDisconnected(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
            self._started = False
            logger.info(f"{self._log_prefix} Desconectado com sucesso")
        except Exception as e:
            logger.error(f"{self._log_prefix} Erro ao desconectar: {e}", exc_info=True)
            self._started = False

    # ------------------------------------------------------------------ #
    # Acesso direto ao SendLayer
    # ------------------------------------------------------------------ #

    def get_send_layer(self):
        """
        Retorna a referência direta ao SendLayer para acesso avançado.
        
        Returns:
            SendLayer: Instância do SendLayer para operações diretas
        """
        logger.debug(f"{self._log_prefix} get_send_layer() chamado")
        return self.send_layer

    def is_connected(self) -> bool:
        """
        Verifica se a conexão está ativa.
        
        Returns:
            bool: True se conectado, False caso contrário
        """
        if not self._started:
            logger.debug(f"{self._log_prefix} is_connected() = False (não iniciado)")
            return False
        if self.send_layer is None:
            logger.debug(f"{self._log_prefix} is_connected() = False (send_layer é None)")
            return False
        connected = self.send_layer.isConnected
        logger.debug(f"{self._log_prefix} is_connected() = {connected}")
        return connected
    
    def get_account_id(self) -> str:
        """
        Retorna o ID da conta (número de telefone).
        
        Returns:
            account_id da conta
        """
        return self.account_id
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna o status atual da conta.
        
        Returns:
            Dict com informações de status:
            - account_id: ID da conta
            - connected: Se está conectada
            - started: Se foi iniciada
            - auto_reply_enabled: Se auto responder está habilitado
        """
        return {
            "account_id": self.account_id,
            "connected": self.is_connected(),
            "started": self._started,
            "auto_reply_enabled": self._auto_reply_enabled,
        }

    # ------------------------------------------------------------------ #
    # Operações de alto nível
    # ------------------------------------------------------------------ #

    def send_text_reply(
        self,
        to: str,
        text: str,
        reply_to_message_id: str,
        *,
        reply_to_participant: Optional[str] = None,
        quoted_text: Optional[str] = None,
        wait_for_id: bool = False,
        wait_msg_id_timeout: Optional[int] = None,
        **options: Any,
    ) -> CommandResponse:
        """
        Envia uma mensagem de texto marcando outra mensagem como resposta (reply/quote).
        
        Args:
            to: JID do destinatário (grupo ou contato individual)
            text: Texto da mensagem de resposta
            reply_to_message_id: ID da mensagem original que está sendo respondida
            reply_to_participant: Para grupos, o JID do participante que enviou a mensagem original (opcional)
            quoted_text: Texto opcional da mensagem original para mostrar na quote (opcional)
            wait_for_id: Se True, retorna o ID da mensagem enviada
            wait_msg_id_timeout: Timeout em segundos para obter o ID (padrão: 20)
            options: Opções adicionais repassadas para a camada de envio
        
        Returns:
            CommandResponse com o resultado. Se wait_for_id=True, contém 'message_id'.
        
        Example:
            # Responder a uma mensagem individual
            client.send_text_reply(
                "5511888888888",
                "Entendi sua mensagem!",
                "3EB0123456789ABCDEF"
            )
            
            # Responder a uma mensagem em grupo
            client.send_text_reply(
                "120363123456789012@g.us",
                "Concordo!",
                "3EB0123456789ABCDEF",
                reply_to_participant="5511999999999@s.whatsapp.net",
                quoted_text="Mensagem original aqui"
            )
        """
        self._bind_sysvar_context()

        # Prepara cmdParams: [to, text, reply_to_message_id, reply_to_participant]
        cmdParams = [to, text, reply_to_message_id]
        if reply_to_participant:
            cmdParams.append(reply_to_participant)
        
        # Prepara options
        opts = dict(options)
        if quoted_text:
            opts["quoted_text"] = quoted_text
        
        # Usa sendTextReply do SendLayer diretamente
        if self.send_layer is not None:
            try:
                if wait_for_id:
                    timeout = wait_msg_id_timeout or self._default_wait_time("msg.send")
                    opts["waitMsgId"] = str(timeout)
                    
                    msg_id = self.send_layer.sendTextReply(cmdParams, opts)
                    
                    if msg_id == "TIMEOUT":
                        raise ZowsupError(-999, "Timeout ao aguardar ID da mensagem de reply")
                    
                    logger.info(f"{self._log_prefix} Mensagem de reply enviada (ID={msg_id}) para {to} respondendo {reply_to_message_id}")
                    return CommandResponse(data={"message_id": msg_id})
                else:
                    result = self.send_layer.sendTextReply(cmdParams, opts)
                    logger.info(f"{self._log_prefix} Mensagem de reply enviada para {to} respondendo {reply_to_message_id}")
                    return CommandResponse(data={"success": True})
            except Exception as e:
                logger.error(f"{self._log_prefix} Erro ao enviar mensagem de reply: {e}", exc_info=True)
                raise ZowsupError(-1, f"Erro ao enviar mensagem de reply: {str(e)}")
        else:
            raise ZowsupError(-1, "SendLayer não disponível")
    
    def send_text(
        self,
        to: str,
        text: str,
        *,
        wait_for_id: bool = False,
        wait_msg_id_timeout: Optional[int] = None,
        use_direct_layer: bool = True,
        **options: Any,
    ) -> CommandResponse:
        """
        Envia uma mensagem de texto.
        
        Suporta envio para contatos individuais e grupos:
        - Contato individual: "5511888888888" ou "5511888888888@s.whatsapp.net"
        - Grupo: "120363423921763948" ou "120363423921763948@g.us"
        
        O JID é normalizado automaticamente. Grupos são detectados se:
        - O ID contém hífen (-), OU
        - O ID tem 15+ caracteres sem ".", ":" ou "@"
        
        Args:
            to: número de destino ou JID (ex: "5511888888888" ou "120363423921763948@g.us")
            text: conteúdo da mensagem
            wait_for_id: se True, retorna o ID da mensagem atribuído pelo WhatsApp
            wait_msg_id_timeout: timeout (segundos) para obter o ID (quando wait_for_id=True)
            use_direct_layer: se True, usa SendLayer diretamente (mais rápido, bypass do comando)
            options: opções adicionais repassadas para a camada de envio
        
        Returns:
            CommandResponse com o resultado. Se wait_for_id=True, contém 'message_id'.
        
        Example:
            # Enviar para contato individual
            client.send_text("5511888888888", "Olá!")
            
            # Enviar para grupo (ID será normalizado para @g.us automaticamente)
            client.send_text("120363423921763948", "Olá grupo!")
            
            # Enviar para grupo com JID completo
            client.send_text("120363423921763948@g.us", "Olá grupo!")
            
            # Enviar como reply usando opções
            client.send_text(
                "5511888888888",
                "Resposta aqui",
                reply="3EB0123456789ABCDEF"  # ID da mensagem original
            )
            
            # Enviar como reply em grupo usando opções
            client.send_text(
                "120363123456789012@g.us",
                "Resposta aqui",
                reply={
                    "message_id": "3EB0123456789ABCDEF",
                    "participant": "5511999999999@s.whatsapp.net"
                }
            )
        """
        self._bind_sysvar_context()

        # Integração direta com SendLayer (bypass do sistema de comandos)
        if use_direct_layer and self.send_layer is not None:
            try:
                if wait_for_id:
                    opts = dict(options)
                    timeout = wait_msg_id_timeout or self._default_wait_time("msg.send")
                    opts["waitMsgId"] = str(timeout)
                    opts["ctxId"] = str(uuid.uuid4())
                    
                    msg_id = self.send_layer.sendMsg([to, text], opts)
                    if msg_id == "TIMEOUT":
                        raise ZowsupError(-999, "Timeout ao aguardar ID da mensagem")
                    return CommandResponse(data={"message_id": msg_id})
                else:
                    self.send_layer.sendMsg([to, text], options)
                    # time.sleep(self._default_wait_time("msg.send"))
                    return CommandResponse()
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem via SendLayer direto: {e}")
                # Fallback para método padrão
                pass

        # Método padrão via sistema de comandos
        if wait_for_id:
            opts = dict(options)
            timeout = wait_msg_id_timeout or self._default_wait_time("msg.send")
            # Semântica especial: quando waitMsgId é usado, o sendMsg retorna
            # diretamente o msgId (sem usar getCmdResult)
            opts["waitMsgId"] = str(timeout)

            cmd_id, err = self._execute_command("msg.send", [to, text], opts)

            if err is not None:
                raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

            if cmd_id == "TIMEOUT":
                raise ZowsupError(-999, "Timeout ao aguardar ID da mensagem")

            return CommandResponse(data={"message_id": cmd_id})

        # Comportamento padrão: aguarda resultado via evento (100% orientado a eventos)
        cmd_id, err = self._execute_command("msg.send", [to, text], options)
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

        wait_time = self._default_wait_time("msg.send")
        # Sempre aguarda resultado via evento, mesmo se retornou JUSTWAIT
        # (o comando pode ainda retornar um resultado assíncrono)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))

        return CommandResponse(data=result)

    def send_text_to_self(
        self,
        text: str,
        *,
        wait_for_id: bool = False,
        wait_msg_id_timeout: Optional[int] = None,
        use_direct_layer: bool = True,
        **options: Any,
    ) -> CommandResponse:
        """
        Envia uma mensagem de texto para o próprio número da conta.
        
        Útil para:
        - Testar a conta
        - Criar notas pessoais
        - Verificar se a conta está funcionando corretamente
        
        Args:
            text: conteúdo da mensagem
            wait_for_id: se True, retorna o ID da mensagem atribuído pelo WhatsApp
            wait_msg_id_timeout: timeout (segundos) para obter o ID (quando wait_for_id=True)
            use_direct_layer: se True, usa SendLayer diretamente (mais rápido, bypass do comando)
            options: opções adicionais repassadas para a camada de envio
        
        Returns:
            CommandResponse com o resultado. Se wait_for_id=True, contém 'message_id'.
        
        Example:
            # Enviar mensagem para si próprio
            client.send_text_to_self("Nota pessoal: lembrar de fazer algo")
            
            # Enviar e obter o ID da mensagem
            response = client.send_text_to_self("Teste", wait_for_id=True)
            print(f"Mensagem enviada com ID: {response.data['message_id']}")
        """
        return self.send_text(
            to=self.account_id,
            text=text,
            wait_for_id=wait_for_id,
            wait_msg_id_timeout=wait_msg_id_timeout,
            use_direct_layer=use_direct_layer,
            **options,
        )

    def send_media(
        self,
        to: str,
        media_type: str,
        file_path_or_url: str,
        *,
        wait_for_id: bool = False,
        wait_msg_id_timeout: Optional[int] = None,
        caption: Optional[str] = None,
        **options: Any,
    ) -> CommandResponse:
        """
        Envia uma mensagem de mídia (imagem, vídeo, áudio, documento ou sticker).

        Args:
            to: número de destino
            media_type: "image", "video", "audio", "document" ou "sticker"
            file_path_or_url: caminho local ou URL do arquivo
            wait_for_id: se True, retorna o ID da mensagem
            wait_msg_id_timeout: timeout (segundos) para obter o ID
            caption: legenda opcional (não aplicável para stickers)
            options: opções adicionais:
                - Para stickers:
                  - is_animated: bool - se o sticker é animado (padrão: False)
                  - is_avatar: bool - se é um sticker de avatar (padrão: False)
                  - is_ai_sticker: bool - se é um sticker gerado por IA (padrão: False)
                  - is_lottie: bool - se é um sticker Lottie (padrão: False)
                - Para documentos:
                  - fileName: str - nome do arquivo
        """
        self._bind_sysvar_context()

        if media_type not in ("image", "video", "audio", "document", "sticker"):
            raise ValueError("media_type deve ser um de: image, video, audio, document, sticker")

        opts = dict(options)
        if caption is not None:
            opts["caption"] = caption

        if wait_for_id:
            timeout = wait_msg_id_timeout or self._default_wait_time("msg.sendmedia")
            opts["waitMsgId"] = str(timeout)

            cmd_id, err = self._execute_command("msg.sendmedia", [to, media_type, file_path_or_url], opts)
            if err is not None:
                raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

            if cmd_id == "TIMEOUT":
                raise ZowsupError(-999, "Timeout ao aguardar ID da mensagem de mídia")

            return CommandResponse(data={"message_id": cmd_id})

        cmd_id, err = self._execute_command("msg.sendmedia", [to, media_type, file_path_or_url], opts)
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

        wait_time = self._default_wait_time("msg.sendmedia")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        
        return CommandResponse(data=result)

    def send_status(
        self,
        text: Optional[str] = None,
        media_type: Optional[str] = None,
        file_path_or_url: Optional[str] = None,
        *,
        wait_for_id: bool = False,
        wait_msg_id_timeout: Optional[int] = None,
        text_color: Optional[int] = None,
        background_color: Optional[int] = None,
        font: Optional[int] = None,
        **options: Any,
    ) -> CommandResponse:
        """
        Envia um status (story) para o WhatsApp.
        
        Pode enviar status de texto (com cores e fonte) ou status de mídia (imagem/vídeo).
        O status é enviado para status@broadcast, que é o destinatário padrão para status no WhatsApp.
        
        Args:
            text: Texto do status (obrigatório se media_type não for fornecido)
            media_type: Tipo de mídia ("image" ou "video") - obrigatório se text não for fornecido
            file_path_or_url: Caminho local ou URL do arquivo de mídia (obrigatório se media_type for fornecido)
            wait_for_id: Se True, retorna o ID da mensagem
            wait_msg_id_timeout: Timeout (segundos) para obter o ID
            text_color: Cor do texto em formato ARGB (ex: 0xFFFFFFFF para branco)
            background_color: Cor de fundo em formato ARGB (ex: 0xFF000000 para preto)
            font: Tipo de fonte (0=SANS_SERIF, 1=SERIF, 2=NORICAN_REGULAR, 3=BRYNDAN_WRITE, 4=BEBASNEUE_REGULAR, 5=OSWALD_HEAVY)
            options: Opções adicionais:
                - caption: Legenda para mídia
                - preview_type: Tipo de preview (0=NONE, 1=VIDEO)
                - invite_link_group_type_v2: Tipo de grupo para convites (0=DEFAULT)
        
        Returns:
            CommandResponse com o resultado. Se wait_for_id=True, contém 'message_id'.
        
        Example:
            # Status de texto simples
            client.send_status("Meu status de texto")
            
            # Status de texto com cores e fonte
            client.send_status(
                "Status colorido",
                text_color=0xFFFFFFFF,      # Texto branco
                background_color=0xFF000000, # Fundo preto
                font=2                      # Fonte NORICAN_REGULAR
            )
            
            # Status de imagem
            client.send_status(
                media_type="image",
                file_path_or_url="/path/to/image.jpg"
            )
            
            # Status de vídeo
            client.send_status(
                media_type="video",
                file_path_or_url="/path/to/video.mp4",
                caption="Meu vídeo de status"
            )
        """
        self._bind_sysvar_context()
        
        STATUS_BROADCAST = "status@broadcast"
        
        # Validação: deve ter texto OU mídia
        if not text and not media_type:
            raise ValueError("Deve fornecer 'text' ou 'media_type' com 'file_path_or_url'")
        
        if media_type and not file_path_or_url:
            raise ValueError("'file_path_or_url' é obrigatório quando 'media_type' é fornecido")
        
        if media_type and media_type not in ("image", "video"):
            raise ValueError("media_type deve ser 'image' ou 'video' para status")
        
        opts = dict(options)
        
        # Se for status de texto, adiciona opções de cor e fonte
        if text:
            if text_color is not None:
                opts["text_color"] = text_color
            if background_color is not None:
                opts["background_color"] = background_color
            if font is not None:
                opts["font"] = font
            opts["preview_type"] = opts.get("preview_type", 0)
            opts["invite_link_group_type_v2"] = opts.get("invite_link_group_type_v2", 0)
        
        # Se for status de mídia, adiciona caption se fornecido
        if media_type and "caption" in options:
            opts["caption"] = options["caption"]
        
        if wait_for_id:
            timeout = wait_msg_id_timeout or self._default_wait_time("status.send")
            opts["waitMsgId"] = str(timeout)
            opts["ctxId"] = str(uuid.uuid4())
            
            if text:
                # Status de texto
                if self.send_layer is not None:
                    try:
                        msg_id = self.send_layer.sendStatus([STATUS_BROADCAST, text], opts)
                        if msg_id == "TIMEOUT":
                            raise ZowsupError(-999, "Timeout ao aguardar ID do status")
                        return CommandResponse(data={"message_id": msg_id})
                    except Exception as e:
                        logger.error(f"Erro ao enviar status via SendLayer direto: {e}")
                
                cmd_id, err = self._execute_command("status.send", [STATUS_BROADCAST, text], opts)
            else:
                # Status de mídia
                if self.send_layer is not None:
                    try:
                        msg_id = self.send_layer.sendStatusMedia([STATUS_BROADCAST, media_type, file_path_or_url], opts)
                        if msg_id == "TIMEOUT":
                            raise ZowsupError(-999, "Timeout ao aguardar ID do status")
                        return CommandResponse(data={"message_id": msg_id})
                    except Exception as e:
                        logger.error(f"Erro ao enviar status de mídia via SendLayer direto: {e}")
                
                cmd_id, err = self._execute_command("status.sendmedia", [STATUS_BROADCAST, media_type, file_path_or_url], opts)
            
            if err is not None:
                raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
            
            if cmd_id == "TIMEOUT":
                raise ZowsupError(-999, "Timeout ao aguardar ID do status")
            
            return CommandResponse(data={"message_id": cmd_id})
        
        # Envio sem aguardar ID
        if text:
            if self.send_layer is not None:
                try:
                    self.send_layer.sendStatus([STATUS_BROADCAST, text], opts)
                    return CommandResponse()
                except Exception as e:
                    logger.error(f"Erro ao enviar status via SendLayer direto: {e}")
            
            cmd_id, err = self._execute_command("status.send", [STATUS_BROADCAST, text], opts)
        else:
            if self.send_layer is not None:
                try:
                    self.send_layer.sendStatusMedia([STATUS_BROADCAST, media_type, file_path_or_url], opts)
                    return CommandResponse()
                except Exception as e:
                    logger.error(f"Erro ao enviar status de mídia via SendLayer direto: {e}")
            
            cmd_id, err = self._execute_command("status.sendmedia", [STATUS_BROADCAST, media_type, file_path_or_url], opts)
        
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        
        wait_time = self._default_wait_time("status.send")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        
        return CommandResponse(data=result)

    def create_group(self, subject: str, participants: list[str]=[]) -> CommandResponse:
        """
        Cria um grupo com o assunto e participantes informados.

        - subject: nome do grupo
        - participants: string com jids separados por vírgula
        """
        cmd_id, err = self._execute_command("group.create", [subject, ",".join(participants) if participants else ""], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        wait_time = self._default_wait_time("group.create")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        # Persistência de grupo + participantes (owner + lista recebida)
        group_id = self._extract_group_id(result or {})
        try:
            if group_id:
                record_group(
                    group_jid=group_id,
                    creator_phone=self.account_id,
                    participants=[self.account_id] + participants,
                    subject=subject,
                )
        except Exception as exc:
            logger.error(f"{self._log_prefix} Erro ao registrar grupo no banco: {exc}")
        return CommandResponse(data=result)

    def get_group_invite(self, group_id: str) -> CommandResponse:
        """
        Obtém o código de convite de um grupo.

        Args:
            group_id: ID ou JID completo do grupo

        Returns:
            CommandResponse com dados retornados pela API, incluindo o código de convite (invite/code/inviteCode).
        """
        cmd_id, err = self._execute_command("group.getinvite", [group_id], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

        wait_time = self._default_wait_time("group.getinvite")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        if isinstance(result, dict):
            code = result.get("code") or result.get("invite") or result.get("inviteCode")
            if code:
                result["link"] = f"https://chat.whatsapp.com/{code}"
                
        return CommandResponse(data=result)

    def join_group_with_code(self, invite_code: str) -> CommandResponse:
        """
        Entra em um grupo usando o código/link de convite.

        Args:
            invite_code: hash de convite ou link completo. Se for link, o hash será extraído.

        Returns:
            CommandResponse com o resultado da operação.
        """
        code = invite_code
        if "chat.whatsapp.com/" in invite_code:
            code = invite_code.split("chat.whatsapp.com/")[-1].strip()

        cmd_id, err = self._execute_command("group.join", [code], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

        wait_time = self._default_wait_time("group.join")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        # Tenta registrar o participante no grupo retornado
        try:
            group_id = None
            if isinstance(result, dict):
                group_id = self._extract_group_id(result)
            if group_id:
                record_group(
                    group_jid=group_id,
                    creator_phone=None,
                    participants=[self.account_id],
                    subject=None,
                )
        except Exception as exc:
            logger.error(f"{self._log_prefix} Erro ao registrar participação no grupo: {exc}")
        return CommandResponse(data=result)

    def list_groups(self) -> CommandResponse:
        """
        Lista grupos da conta atual, quando suportado pela API.
        """
        cmd_id, err = self._execute_command("group.list", [], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        wait_time = self._default_wait_time("group.list")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        return CommandResponse(data=result)
    
    def group_add(self, group_id: str, participant_phones: str) -> CommandResponse:
        """
        Adiciona participantes a um grupo.
        
        Args:
            group_id: ID do grupo (pode ser apenas o ID ou JID completo)
            participant_phones: String com phones separados por vírgula (ex: "5511999999999,5511888888888")
        
        Returns:
            CommandResponse com successCount, successJids, errorCount, errorJids
        """
        logger.debug(f"{self._log_prefix} group_add(group_id={group_id}, participants={participant_phones})")
        cmd_id, err = self._execute_command("group.add", [group_id, participant_phones], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        wait_time = self._default_wait_time("group.add")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        return CommandResponse(data=result)

    def sync_contacts(self, numbers: list[str]) -> CommandResponse:
        """
        Sincroniza contatos informados (string de números separados por vírgula).
        """
        cmd_id, err = self._execute_command("contact.sync", [",".join(numbers)], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        wait_time = self._default_wait_time("contact.sync")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        return CommandResponse(data=result)

    def integrity_check(self, phones: list[str]) -> CommandResponse:
        """
        Executa a checagem de integridade (BizIntegrityQuery) para IDs separados por vírgula.
        """

        phones_str = ",".join(phones)


        cmd_id, err = self._execute_command("integrity.check", [phones_str], {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        wait_time = self._default_wait_time("integrity.check")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        return CommandResponse(data=result)
    
    def send_reaction(
        self,
        to: str,
        message_id: str,
        emoji: str,
        *,
        participant: Optional[str] = None,
    ) -> CommandResponse:
        """
        Envia uma reação (emoji) para uma mensagem.
        
        Args:
            to: JID do destinatário (grupo ou contato individual)
            message_id: ID da mensagem que está sendo reagida
            emoji: Emoji da reação (ex: "👍", "❤️", "😂")
            participant: Para grupos, o JID do participante que enviou a mensagem original (opcional)
        
        Returns:
            CommandResponse com o resultado da operação
        
        Example:
            # Reagir a uma mensagem individual
            client.send_reaction("5511999999999", "3EB0123456789ABCDEF", "👍")
            
            # Reagir a uma mensagem em grupo
            client.send_reaction(
                "120363123456789012@g.us",
                "3EB0123456789ABCDEF",
                "❤️",
                participant="5511999999999@s.whatsapp.net"
            )
        """
        self._bind_sysvar_context()

        import time
        from zowsuplib.yowsup.layers.protocol_messages.protocolentities.message_reaction import ReactionMessageProtocolEntity
        from zowsuplib.yowsup.layers.protocol_messages.protocolentities.attributes.attributes_reaction import ReactionAttributes
        from zowsuplib.yowsup.layers.protocol_messages.protocolentities.message import MessageMetaAttributes
        from zowsuplib.yowsup.common.tools import Jid
        
        # Normaliza o JID
        normalized_to = Jid.normalize(to)
        if not normalized_to:
            raise ValueError(f"JID inválido: {to}")
        
        # Prepara o remote_jid (grupo ou contato)
        remote_jid = normalized_to
        
        # Prepara o participant se for grupo
        if participant:
            participant_normalized = Jid.normalize(participant)
            if participant_normalized:
                participant = participant_normalized
        
        # Cria ReactionAttributes
        # Inclui participant no ReactionAttributes para que seja incluído no key do protobuf (necessário para grupos)
        participant_for_key = participant if participant and "@g.us" in normalized_to else None
        reaction_attr = ReactionAttributes(
            msgid=message_id,
            remote_jid=remote_jid,
            from_me=False,  # A mensagem original não foi enviada por nós
            text=emoji,
            sender_timestamp_ms=int(time.time() * 1000),  # Timestamp em milissegundos
            participant=participant_for_key  # Participant para grupos (será incluído no key)
        )
        
        # Cria MessageMetaAttributes
        # Para grupos, o participant precisa ser incluído no MessageMetaAttributes
        meta_attrs = MessageMetaAttributes(
            id=self.bot.idType,
            recipient=normalized_to,
            timestamp=int(time.time()),
            participant=participant if participant and "@g.us" in normalized_to else None
        )
        
        # Cria a entidade de reação
        reaction_entity = ReactionMessageProtocolEntity(
            reaction_attr,
            message_meta_attributes=meta_attrs
        )
        
        # Envia através do SendLayer
        if self.send_layer is not None:
            try:
                # Para mensagens protomessage (como reaction), precisamos passar pela camada de mensagens
                # que processa corretamente o tipo "reaction"
                from zowsuplib.yowsup.layers.protocol_messages.layer import YowMessagesProtocolLayer
                
                # Obtém a camada de mensagens do stack
                messages_layer = self.send_layer.getLayerInterface(YowMessagesProtocolLayer)
                
                if messages_layer:
                    # Usa send() que chama sendMessageEntity() para processar a entidade
                    # send() verifica o handleMap e chama sendMessageEntity() que processa "reaction"
                    messages_layer.send(reaction_entity)
                else:
                    # Fallback: converte manualmente e envia diretamente
                    # ReactionMessageProtocolEntity.toProtocolTreeNode() retorna um ProtocolTreeNode válido
                    reaction_node = reaction_entity.toProtocolTreeNode()
                    # Passa o node diretamente para toLower (não a entidade)
                    self.send_layer.toLower(reaction_node)
                
                logger.info(f"{self._log_prefix} Reação {emoji} enviada para mensagem {message_id} em {normalized_to}")
                return CommandResponse(data={"success": True, "message_id": message_id, "emoji": emoji})
            except Exception as e:
                logger.error(f"{self._log_prefix} Erro ao enviar reação: {e}", exc_info=True)
        else:
            raise ZowsupError(-1, "SendLayer não disponível")

    def initialize(self, name: Optional[str] = None) -> CommandResponse:
        """
        Inicializa a conta (para o primeiro login).

        Este método executa uma sequência de operações necessárias após o primeiro
        login bem-sucedido:
        - Aguarda 5 segundos para estabilização
        - Obtém configurações do servidor (Push IQ e Props IQ)
        - Aguarda 2 segundos
        - Define o nome da conta (pushname)

        - name: nome opcional para a conta. Se não fornecido, será gerado
          automaticamente um nome aleatório.

        Retorna CommandResponse sem dados específicos (apenas indica sucesso).

        Nota: Se a conta já foi inicializada anteriormente, este método não
        executará a inicialização novamente e retornará sucesso imediatamente.
        """
        from zowsuplib.app.db import is_account_initialized

        # Verifica se a conta já foi inicializada
        # if is_account_initialized(self.bot.botId):
        #     logger.info(f"Conta {self.bot.botId} já foi inicializada anteriormente. Pulando inicialização.")
        #     return CommandResponse(data={"message": "Conta já inicializada", "skipped": True})

        self._bind_sysvar_context()

        params = [name] if name else []
        cmd_id, err = self._execute_command("account.init", params, {})
        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))
        wait_time = self._default_wait_time("account.init")
        # Aguarda resultado via evento (orientado a eventos)
        result, err2 = self._get_cmd_result(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))
        return CommandResponse(data=result)

    # ------------------------------------------------------------------ #
    # Auto responder
    # ------------------------------------------------------------------ #

    def enable_auto_reply(
        self,
        message: Optional[str] = None,
        *,
        ignore_groups: bool = True,
        allowed_contacts: Optional[Set[str]] = None,
        blocked_contacts: Optional[Set[str]] = None,
        custom_handler: Optional[Callable[[str, str], Optional[str]]] = None,
    ) -> None:
        """
        Habilita o auto responder para esta conta.
        
        Args:
            message: Mensagem padrão de resposta (opcional)
            ignore_groups: Se True, ignora mensagens de grupos
            allowed_contacts: Set de contatos permitidos (None = todos)
            blocked_contacts: Set de contatos bloqueados
            custom_handler: Função customizada para gerar respostas
        
        Habilita o auto responder para mensagens recebidas.

        - message: mensagem de resposta automática. Se None, será usada uma
          mensagem aleatória da classe MessageDefault.
        - ignore_groups: se True, ignora mensagens de grupos (padrão: True)
        - allowed_contacts: conjunto de números permitidos para receber resposta.
          Se None, responde para todos (exceto bloqueados).
        - blocked_contacts: conjunto de números bloqueados que não receberão resposta.
        - custom_handler: função customizada que recebe (sender, message_text) e
          retorna a mensagem de resposta ou None para não responder.
          Exemplo: lambda sender, text: "Olá!" if "oi" in text.lower() else None

        Exemplos de uso:

            # Resposta simples para todos
            client.enable_auto_reply("Olá! Estou ocupado no momento.")

            # Resposta apenas para contatos específicos
            client.enable_auto_reply(
                "Olá!",
                allowed_contacts={"5511999999999", "5511888888888"}
            )

            # Handler customizado
            def my_handler(sender, text):
                if "help" in text.lower():
                    return "Como posso ajudar?"
                return None

            client.enable_auto_reply(custom_handler=my_handler)
        """
        self._bind_sysvar_context()

        if self._auto_reply_enabled:
            logger.warning("Auto responder já está habilitado. Desabilite antes de reconfigurar.")
            return

        self._auto_reply_config = {
            "message": message,
            "ignore_groups": ignore_groups,
            "allowed_contacts": allowed_contacts or set(),
            "blocked_contacts": blocked_contacts or set(),
            "custom_handler": custom_handler,
        }

        # Salva o callback original do bot
        self._original_callback = self.bot.callback
        
        # Configura o callback customizado diretamente no SendLayer
        # Integração direta via referência self.send_layer
        if self.send_layer is not None:
            self.send_layer.setMessageCallback(self._auto_reply_callback)
            logger.info(f"Auto responder habilitado para conta {self.bot.botId} via SendLayer (integração direta)")
        else:
            # Fallback: usa o callback do bot se SendLayer não estiver disponível
            self.bot.callback = self._auto_reply_callback
            logger.warning(f"SendLayer não disponível, usando callback do bot como fallback")
        
        self._auto_reply_enabled = True
        logger.debug(f"Callback original do bot: {self._original_callback}")

    def disable_auto_reply(self) -> None:
        """
        Desabilita o auto responder e restaura o callback original.
        """
        self._bind_sysvar_context()

        if not self._auto_reply_enabled:
            logger.warning("Auto responder já está desabilitado.")
            return

        # Remove o callback customizado do SendLayer (integração direta)
        if self.send_layer is not None:
            self.send_layer.setMessageCallback(None)
        
        # Restaura o callback original do bot (se foi alterado)
        if self._original_callback is not None:
            self.bot.callback = self._original_callback
            self._original_callback = None

        self._auto_reply_enabled = False
        self._auto_reply_config = None
        logger.info(f"Auto responder desabilitado para conta {self.bot.botId}")

    def _auto_reply_callback(
        self,
        event=None,
        message=None,
        cmdresult=None,
        logger=None,
        caller=None,
    ) -> None:
        """
        Callback customizado que intercepta mensagens e envia respostas automáticas.
        
        Pode ser chamado de duas formas:
        1. Pelo SendLayer: apenas com message, logger, caller
        2. Pelo bot callback: com event, message, cmdresult, logger, caller
        """
        # Usa o logger passado ou o padrão do módulo (importado no topo)
        # Importa novamente para evitar conflito com o parâmetro 'logger'
        from loguru import logger as module_logger
        log = logger if logger is not None else module_logger
        
        log.info(f"[AUTO_REPLY] Callback chamado - message: {message is not None}, event: {event is not None}, cmdresult: {cmdresult is not None}, enabled: {self._auto_reply_enabled}")


        logger.info(f"[AUTO_REPLY] message: {message}")


        reply_to_message_id = message.msg_id if message.HasField("msg_id") else None
        # Verifica se o auto responder ainda está habilitado
        if not self._auto_reply_enabled or self._auto_reply_config is None:
            log.warning("[AUTO_REPLY] Auto responder não está habilitado ou config não existe")
            return
        
        # Processa apenas mensagens de texto recebidas
        if message is None:
            log.debug("[AUTO_REPLY] message é None, ignorando")
            return
            
        if not message.HasField("text_message"):
            log.debug(f"[AUTO_REPLY] mensagem não é de texto (type: {message.type if hasattr(message, 'type') else 'unknown'}), ignorando")
            return
            
        # Determina o sender real (participant em grupos, sender em individuais)
        is_group = message.HasField("participant")
        if is_group:
            # Em grupos: sender é o grupo, participant é quem enviou
            # if self._auto_reply_config["ignore_groups"]:
            #     log.debug(f"[AUTO_REPLY] Mensagem de grupo ignorada (ignore_groups=True)")
            #     return
            sender = message.sender  # Quem enviou no grupo
            group_jid = message.sender  # JID do grupo
            log.info(f"[AUTO_REPLY] Mensagem de grupo {group_jid} de {sender}")
        else:
            # Mensagem individual
            sender = message.sender
            log.info(f"[AUTO_REPLY] Mensagem individual de {sender}")

        # Normaliza o sender (remove @s.whatsapp.net ou @lid se presente)
        sender_normalized = sender.split("@")[0] if "@" in sender else sender

        # Verifica se o contato está bloqueado
        if sender_normalized in self._auto_reply_config["blocked_contacts"]:
            log.debug(f"[AUTO_REPLY] Contato {sender_normalized} está bloqueado, ignorando")
            return

        # Verifica se está na lista de permitidos (se houver)
        allowed = self._auto_reply_config["allowed_contacts"]
        if allowed and sender_normalized not in allowed:
            log.debug(f"[AUTO_REPLY] Contato {sender_normalized} não está na lista de permitidos, ignorando")
            return

        # Obtém o texto da mensagem
        text = message.text_message.text

        # Tenta usar o handler customizado primeiro
        reply_message = None
        custom_handler = self._auto_reply_config["custom_handler"]
        if custom_handler is not None:
            try:
                reply_message = custom_handler(sender_normalized, text)
            except Exception as e:
                log.error(f"Erro no handler customizado de auto responder: {e}")

        # Se o handler não retornou mensagem, usa a mensagem configurada ou padrão
        if reply_message is None:
            if self._auto_reply_config["message"] is not None:
                reply_message = self._auto_reply_config["message"]
            else:
                # Usa mensagem aleatória da classe MessageDefault
                msg_default = MessageDefault()
                reply_message = msg_default.get_message()

        # Para grupos: envia reação com delay de 5s
        if is_group:
            # Lista de emojis aleatórios para reação
            emojis = ["👍", "❤️", "😂", "😮", "😢", "🙏", "👏", "🔥", "💯", "🎉", "✨", "⭐"]
            random_emoji = random.choice(emojis)
            
            log.info(f"[AUTO_REPLY] Mensagem de grupo detectada. Aguardando 5s antes de enviar reação {random_emoji}...")
            
            # Aguarda 5 segundos
            # time.sleep(5)
            
            # Envia reação com emoji aleatório usando sendReaction do SendLayer
            # try:
            #     message_id = message.msg_id
            #     group_jid = message.sender
            #     participant_jid = sender  # O participante que enviou a mensagem original
                
            #     log.info(f"[AUTO_REPLY] Enviando reação {random_emoji} para mensagem {message_id} no grupo {group_jid} (participant: {participant_jid})")
                
            #     # Usa sendReaction do SendLayer diretamente
            #     if self.send_layer is not None:
            #         # Prepara cmdParams: [to, message_id, emoji, participant]
            #         cmdParams = [group_jid, message_id, random_emoji]
            #         if participant_jid and participant_jid != group_jid:
            #             cmdParams.append(participant_jid)
                    
            #         # Envia sem aguardar ID (JUSTWAIT)
            #         result = self.send_layer.sendReaction(cmdParams, {"reply":{"message_id":message_id,
            #                                                                     "participant":participant_jid,
            #                                                                     "remote_jid":group_jid}})
            #         log.info(f"[AUTO_REPLY] Reação {random_emoji} enviada com sucesso para grupo {group_jid} (result: {result})")
            #     else:
            #         # Fallback para método via API (caso SendLayer não esteja disponível)
            #         log.warning("[AUTO_REPLY] SendLayer não disponível, usando método via API")
            #         self.send_reaction(
            #             to=group_jid,
            #             message_id=message_id,
            #             emoji=random_emoji,
            #             participant=participant_jid if participant_jid != group_jid else None
            #         )
            #         log.info(f"[AUTO_REPLY] Reação {random_emoji} enviada com sucesso para grupo {group_jid}")
            # except Exception as e:
            #     log.error(f"[AUTO_REPLY] Erro ao enviar reação para grupo: {e}", exc_info=True)
            
        # Para mensagens individuais: envia resposta de texto normalmente
        # Envia a resposta automática (sem esperar resultado)
        if reply_message:
            try:
                to = sender_normalized

                logger.info(f"[AUTO_REPLY] Enviando auto resposta para {to}: {reply_message}")

                # Usa SendLayer diretamente para envio mais rápido (bypass do sistema de comandos)
                try:
                    resp = self.send_text(to, reply_message,wait_for_id=True,use_direct_layer=True)
                    print(resp)
                    log.info(f"[AUTO_REPLY] Auto resposta enviada para {sender_normalized}: {reply_message}")
                except Exception as e2:
                    log.error(f"[AUTO_REPLY] Erro ao enviar auto resposta via SendLayer: {e2}, tentando via comandos")
                    self.send_text(to, reply_message, wait_for_id=False,use_direct_layer=False)

            except Exception as e:
                log.error(f"[AUTO_REPLY] Erro ao enviar auto resposta para {sender_normalized}: {e}")



        logger.info(f"[AUTO_REPLY] Aguardando 10 segundos...")
        time.sleep(random.uniform(1, 2))

    
    @staticmethod
    def export_contacts_to_vcard(
        output_file: Optional[str] = None,
        include_groups: bool = False,
    ) -> str:
        """
        Exporta todos os contatos da conta para formato vCard.
        
        Args:
            output_file: Caminho do arquivo de saída (opcional). Se None, retorna apenas a string.
            include_groups: Se True, inclui grupos na exportação (padrão: False)
        
        Returns:
            String com o conteúdo vCard ou caminho do arquivo se output_file foi fornecido
        
        Example:
            # Exportar para string
            vcard_content = client.export_contacts_to_vcard()
            
            # Exportar para arquivo
            client.export_contacts_to_vcard(output_file="contacts.vcf")
            
            # Exportar incluindo grupos
            client.export_contacts_to_vcard(output_file="all_contacts.vcf", include_groups=True)
        """
        from zowsuplib.app.db import export_contacts_to_vcard
        
        return export_contacts_to_vcard(
            output_file=output_file,
            include_groups=include_groups,
        )

    # ------------------------------------------------------------------ #
    # Master account helper
    # ------------------------------------------------------------------ #
    @classmethod
    def get_master_client(
        cls,
        *,
        env: Optional[str] = None,
        proxy: Optional[str] = None,
        auto_connect: bool = True,
    ) -> "ZowsupClient":
        """
        Retorna um cliente para a conta marcada como master no banco.

        Args:
            env: override de ambiente (default: usa env da conta ou Settings.default_env)
            proxy: proxy ou "DIRECT"
            auto_connect: se True, conecta automaticamente

        Raises:
            ValueError se nenhuma conta master existir.
        """
        session = SessionLocal()
        row = None
        try:
            row = (
                session.query(models.Account.phone, models.Account.env)
                .filter_by(master=True)
                .order_by(models.Account.id.desc())
                .first()
            )
            # Fallback: última conta logada caso não exista master
            if row is None:
                row = (
                    session.query(models.Account.phone, models.Account.env)
                    .filter_by(is_logged_in=True)
                    .order_by(models.Account.updated_at.desc())
                    .first()
                )
        finally:
            session.close()

        if row is None:
            raise ValueError("Nenhuma conta master ou conta logada encontrada no banco de dados")

        account_phone, account_env = row
        resolved_env = env or account_env or settings.default_env

        return cls(
            account_id=account_phone,
            env=resolved_env,
            proxy=proxy,
            auto_connect=auto_connect,
        )




