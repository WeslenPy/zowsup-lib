import logging
import time
import base64
from dataclasses import dataclass
from typing import Any, Dict, Optional
from pathlib import Path

import names
from consonance.structs.keypair import KeyPair
from yowsup.axolotl.factory import AxolotlManagerFactory
from yowsup.config.v1.config import Config
from yowsup.profile.profile import YowProfile
from yowsup.common.tools import WATools

from conf.constants import SysVar
from common.utils import Utils
from app.bot_env import BotEnv
from app.device_env import DeviceEnv
from app.network_env import NetworkEnv
from app.yowbot import YowBot
from app.config import AppConfig


logger = logging.getLogger(__name__)


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


class ZowsupClient:
    """
    Cliente de alto nível para uso programático do Zowsup.

    Exemplos de uso:

        from app.api import ZowsupClient

        client = ZowsupClient(account_id="5511999999999")
        client.connect()
        client.send_text("5511888888888", "Olá do Zowsup!")
        client.disconnect()
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
        """
        # Garante que SysVar.* está inicializado e diretórios criados
        app_config = AppConfig.load(config_path)
        app_config.apply_to_sysvar()

        parts = six_parts_data.split(",")
        if len(parts) != 6:
            raise ValueError("6-parts-account-data inválido: esperado 6 campos separados por vírgula")

        phone, pk1, sk1, pk2, sk2, sixth = parts

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

        config = Config(
            pushname=names.get_full_name() + "X",
            cc=Utils.getMobileCC(phone),
            mcc="000",
            mnc="000",
            phone=phone,
            sim_mcc="000",
            sim_mnc="000",
            client_static_keypair=kp,
            fdid=WATools.generatePhoneId(fake_bot_env),
            expid=WATools.generateDeviceId(),
            id=account_id_bytes,
        )

        account_dir = Path(SysVar.ACCOUNT_PATH + phone)
        account_dir.mkdir(parents=True, exist_ok=True)

        profile = YowProfile(SysVar.ACCOUNT_PATH + phone)
        profile.write_config(config)

        # Atualiza as chaves de identidade na base axolotl
        db = AxolotlManagerFactory().get_manager(SysVar.ACCOUNT_PATH + phone, phone)

        q = "UPDATE identities SET public_key=? , private_key=? WHERE recipient_id=-1 AND recipient_type=0"
        c = db._store.identityKeyStore.dbConn.cursor()

        pub_raw = base64.b64decode(pk2)
        if len(pub_raw) == 32:
            pub_key = b"\x05" + pub_raw
        else:
            logger.info("6-parts account pode estar em formato não padrão; usando chave pública como recebido")
            pub_key = pub_raw

        priv_key = base64.b64decode(sk2)

        c.execute(q, (pub_key, priv_key))
        db._store.identityKeyStore.dbConn.commit()

        logger.info("Conta %s importada com sucesso em %s", phone, account_dir)
        return phone

    def __init__(
        self,
        account_id: str,
        *,
        config: Optional[AppConfig] = None,
        config_path: Optional[str] = None,
        env: Optional[str] = None,
        proxy: Optional[str] = None,
        auto_connect: bool = True,
    ) -> None:
        """
        Cria um novo cliente de alto nível.

        - account_id: número da conta (como string, ex: "5511999999999")
        - config: instância pré-carregada de AppConfig (opcional)
        - config_path: caminho para config.conf, se quiser sobrescrever o padrão
        - env: nome do ambiente de device (android, ios, smb_android, smb_ios)
        - proxy: string de proxy no formato "host:port:username:password" ou "DIRECT"
        - auto_connect: se True, já inicia a conexão e espera login
        """
        self.config = config or AppConfig.load(config_path)
        # Garante que código legado que usa SysVar continue funcionando
        self.config.apply_to_sysvar()

        device_env_name = env or self.config.default_env
        device_env = DeviceEnv(device_env_name, random=True)

        if proxy and proxy.upper() != "DIRECT":
            network_env = NetworkEnv(NetworkEnv.TYPE_PROXY, proxyStr=proxy)
        else:
            network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)

        self.bot_env = BotEnv(deviceEnv=device_env, networkEnv=network_env)
        self.bot = YowBot(bot_id=account_id, env=self.bot_env)
        self._started = False

        if auto_connect:
            self.connect()

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

        return 20

    def connect(self, wait_login: bool = True) -> bool:
        """
        Inicia o bot em thread separada e, opcionalmente, espera o login.

        Retorna True se o login foi concluído com sucesso dentro do timeout
        padrão, False em caso de timeout.
        """
        if self._started:
            return True

        self.bot.runAsThread()
        self._started = True

        if not wait_login:
            return True

        wait_time = self._default_wait_time("login")
        ok = self.bot.waitLogin()
        if not ok:
            logger.info("Login timeout para conta %s", self.bot.botId)
        return ok

    def disconnect(self) -> None:
        """
        Encerra a conexão do bot de forma controlada.
        """
        if not self._started:
            return
        self.bot.quit()
        self._started = False

    # ------------------------------------------------------------------ #
    # Execução genérica de comandos
    # ------------------------------------------------------------------ #

    def _run_command(
        self,
        name: str,
        params: Optional[list] = None,
        options: Optional[Dict[str, Any]] = None,
        *,
        wait_for_result: bool = True,
    ) -> CommandResponse:
        """
        Executa um comando YowBot genérico com semântica semelhante ao CLI.

        - Se o comando retornar "JUSTWAIT", o método apenas aguarda o tempo
          padrão configurado e retorna sem dados.
        - Caso contrário, tenta buscar o resultado via getCmdResult.
        """
        params = params or []
        options = options or {}

        cmd_id, err = self.bot.callDirect(name, params, options)

        if err is not None:
            raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

        # Para chamadas que não esperam resultado (fire-and-forget)
        if not wait_for_result:
            return CommandResponse(data=cmd_id)

        wait_time = self._default_wait_time(name)

        if cmd_id == "JUSTWAIT":
            # Mesmo comportamento do CLI: apenas esperar N segundos
            logger.info("Command %s retornou JUSTWAIT, aguardando %d segundos", name, wait_time)
            time.sleep(wait_time)
            return CommandResponse()

        result, err2 = self.bot.getCmdResult(cmd_id, wait_time)
        if err2 is not None:
            raise ZowsupError(err2.get("code"), err2.get("msg", "Command error"))

        return CommandResponse(data=result)

    # ------------------------------------------------------------------ #
    # Operações de alto nível
    # ------------------------------------------------------------------ #

    def send_text(
        self,
        to: str,
        text: str,
        *,
        wait_for_id: bool = False,
        wait_msg_id_timeout: Optional[int] = None,
        **options: Any,
    ) -> CommandResponse:
        """
        Envia uma mensagem de texto.

        - to: número de destino (ex: "5511888888888" ou JID completo)
        - text: conteúdo da mensagem
        - wait_for_id: se True, retorna o ID da mensagem atribuído pelo WhatsApp
        - wait_msg_id_timeout: timeout (segundos) para obter o ID (quando wait_for_id=True)
        - options: opções adicionais repassadas para a camada de envio
        """
        if wait_for_id:
            opts = dict(options)
            timeout = wait_msg_id_timeout or self._default_wait_time("msg.send")
            # Semântica especial: quando waitMsgId é usado, o sendMsg retorna
            # diretamente o msgId (sem usar getCmdResult)
            opts["waitMsgId"] = str(timeout)

            cmd_id, err = self.bot.callDirect("msg.send", [to, text], opts)
            if err is not None:
                raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

            if cmd_id == "TIMEOUT":
                raise ZowsupError(-999, "Timeout ao aguardar ID da mensagem")

            return CommandResponse(data={"message_id": cmd_id})

        # Comportamento padrão: igual ao CLI, apenas aguarda alguns segundos
        resp = self._run_command("msg.send", [to, text], options)
        return resp

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
        Envia uma mensagem de mídia (imagem, vídeo, áudio ou documento).

        - to: número de destino
        - media_type: "image", "video", "audio" ou "document"
        - file_path_or_url: caminho local ou URL do arquivo
        - wait_for_id: se True, retorna o ID da mensagem
        - wait_msg_id_timeout: timeout (segundos) para obter o ID
        - caption: legenda opcional
        - options: opções adicionais repassadas para a camada de envio
        """
        if media_type not in ("image", "video", "audio", "document"):
            raise ValueError("media_type deve ser um de: image, video, audio, document")

        opts = dict(options)
        if caption is not None:
            opts["caption"] = caption

        if wait_for_id:
            timeout = wait_msg_id_timeout or self._default_wait_time("msg.sendmedia")
            opts["waitMsgId"] = str(timeout)

            cmd_id, err = self.bot.callDirect("msg.sendmedia", [to, media_type, file_path_or_url], opts)
            if err is not None:
                raise ZowsupError(err.get("code"), err.get("msg", "Command error"))

            if cmd_id == "TIMEOUT":
                raise ZowsupError(-999, "Timeout ao aguardar ID da mensagem de mídia")

            return CommandResponse(data={"message_id": cmd_id})

        resp = self._run_command("msg.sendmedia", [to, media_type, file_path_or_url], opts)
        return resp

    def create_group(self, subject: str, participants: str) -> CommandResponse:
        """
        Cria um grupo com o assunto e participantes informados.

        - subject: nome do grupo
        - participants: string com jids separados por vírgula
        """
        result = self._run_command("group.create", [subject, participants])
        return result

    def list_groups(self) -> CommandResponse:
        """
        Lista grupos da conta atual, quando suportado pela API.
        """
        result = self._run_command("group.list", [])
        return result

    def sync_contacts(self, numbers: str) -> CommandResponse:
        """
        Sincroniza contatos informados (string de números separados por vírgula).
        """
        result = self._run_command("contact.sync", [numbers])
        return result


