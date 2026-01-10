from ...layers.noise.workers.handshake import WANoiseProtocolHandshakeWorker
from ...layers import YowLayer, EventCallback
from ...layers.auth.layer_authentication import YowAuthenticationProtocolLayer
from ...layers.network.layer import YowNetworkLayer
from ...layers.noise.layer_noise_segments import YowNoiseSegmentsLayer
from ...layers import YowLayerEvent
from ...structs.protocoltreenode import ProtocolTreeNode
from ...layers.coder.encoder import WriteEncoder
from ...layers.coder.tokendictionary import TokenDictionary
from ...common.tools import WATools
from zowsuplib.consonance.protocol import WANoiseProtocol
from zowsuplib.consonance.config.client import ClientConfig
from zowsuplib.consonance.config.useragent import UserAgentConfig
from zowsuplib.consonance.streams.segmented.blockingqueue import BlockingQueueSegmentedStream
from zowsuplib.consonance.structs.keypair import KeyPair
import threading,logging,uuid,base64,os
from zowsuplib.common.utils import Utils
from zowsuplib.app.yowbot_values import YowBotType
from zowsuplib.settings.conf import settings

from loguru import logger
try:
    import Queue
except ImportError:
    import queue as Queue
class YowNoiseLayer(YowLayer):
    DEFAULT_PUSHNAME = "yowsup"
    HEADER = b'WA\x06\x03'
    EDGE_HEADER = b'ED\x00\x01'
    EVENT_HANDSHAKE_FAILED = "org.whatsapp.yowsup.layer.noise.event.handshake_failed"
    def __init__(self):
        super(YowNoiseLayer, self).__init__()
        self._wa_noiseprotocol = WANoiseProtocol(
            6, 3, 
            protocol_state_callbacks=self._on_protocol_state_changed,
            recovery_callback=self._maybe_retry_handshake
        )  # type: WANoiseProtocol

        self._handshake_worker = None
        self._stream = BlockingQueueSegmentedStream()  # type: BlockingQueueSegmentedStream
        self._read_buffer = bytearray()
        self._flush_lock = threading.Lock()
        self._incoming_segments_queue = Queue.Queue()
        self._profile = None
        self._rs = None
        self._handshake_attempt = 0
        self._last_handshake_attempt = None
        self._last_segment_preview = None

    def __str__(self):
        return "Noise Layer"

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def on_disconnected(self, event):
        import threading
        from loguru import logger
        
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        thread_id = threading.current_thread().ident
        
        logger.info(f"[HANDSHAKE-DEBUG] on_disconnected chamado | account={account_id} thread_id={thread_id}")
        
        # Resetar protocolo
        self._wa_noiseprotocol.reset()
        
        # Cancelar stream para desbloquear handshake worker bloqueado
        if self._stream:
            logger.debug(f"[HANDSHAKE-DEBUG] Cancelando stream | account={account_id}")
            self._stream.cancel()
        
        # Limpar referência do worker (a thread vai terminar naturalmente após detectar cancelamento)
        if self._handshake_worker is not None:
            worker_thread_id = self._handshake_worker.ident if hasattr(self._handshake_worker, 'ident') else 'N/A'
            logger.debug(f"[HANDSHAKE-DEBUG] Handshake worker ativo, será finalizado | account={account_id} worker_thread_id={worker_thread_id}")
            # Não fazer join() aqui para não bloquear - a thread vai terminar após detectar cancelamento
            self._handshake_worker = None

    @EventCallback(YowAuthenticationProtocolLayer.EVENT_AUTH)
    def on_auth(self, event):        
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        logger.info(f"[HANDSHAKE-DEBUG] on_auth chamado | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())}")
        logger.debug("Received auth event")
        self._profile = self.getProp("profile")

        if self.getProp("botType")==YowBotType.TYPE_REG_COMPANION_SCANQR or self.getProp("botType")==YowBotType.TYPE_REG_COMPANION_LINKCODE:
                           
            keypair = self.getProp("reg_info")["keypair"]

            yowsupenv = self.getProp("env").deviceEnv

            '''
            if config.device_name is not None:
                yowsupenv._OS_NAME = config.os_name
                yowsupenv._OS_VERSION = config.os_version
                yowsupenv._MANUFACTURER = config.manufacturer
                yowsupenv._DEVICE_NAME = config.device_name
            else:
                #保存默认值
                config.os_name= yowsupenv.getOSName()
                config.os_version = yowsupenv.getOSVersion()
                config.manufacturer = yowsupenv.getManufacturer()
                config.device_name = yowsupenv.getDeviceName2()
                self._profile.write_config(config)
            '''

            passive = False

            mcc = "000"
            mnc = "000"
            
            #这个client_cofig 的结构是consonance里面的         
            client_config = ClientConfig(          
                username=None,
                pushname=None,                      
                passive=passive,
                useragent=UserAgentConfig(
                    platform=yowsupenv.getPlatform(),
                    app_version=yowsupenv.getVersion(),
                    mcc=mcc,
                    mnc=mnc,
                    os_version=yowsupenv.getOSVersion(),
                    manufacturer=yowsupenv.getManufacturer(),
                    device=yowsupenv.getDeviceName2(),
                    os_build_number=yowsupenv.getBuildVersion(),
                    phone_id=str(uuid.uuid4()),
                    locale_lang="en",
                    locale_country="US",
                    device_exp_id=base64.b64encode(WATools.generateDeviceId()).decode(),
                    device_type=0,          #PHONE
                    device_model_type=yowsupenv.getDeviceModelType()
                ),                
                short_connect=True
            )     

            regInfo = self.getProp("reg_info")
            regid  = regInfo["regid"]
            identity = regInfo["identity"]
            signedprekey = regInfo["signedprekey"]

            jid = self.getProp("jid")
            if jid is not None:
                r1,r2,deviceid = WATools.jidDecode(jid)

            self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, False)
            self.toLower(self.HEADER)            
            self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, True)                    
            
            if not self._in_handshake():
                self._handshake_attempt += 1
                attempt_id = self._handshake_attempt
                self._last_handshake_attempt = attempt_id
                logger.info(f"[handshake {attempt_id}] performing registration handshake | mcc={mcc} mnc={mnc} deviceid={deviceid if jid is not None else None}")
                self._handshake_worker = WANoiseProtocolHandshakeWorker(
                    self._wa_noiseprotocol, self._stream, client_config, keypair,rs = None,                    
                    finish_callback = self.on_handshake_finished,
                    mode = "reg",
                    identity = identity,regid = regid,signedprekey = signedprekey,
                    deviceid = deviceid if jid is not None else None,
                    attempt_id = attempt_id
                )
                logger.debug(f"[handshake {attempt_id}] starting handshake worker")
                self._stream.set_events_callback(self._handle_stream_event)
                self._handshake_worker.start()
            else:
                logger.warning("Registration handshake requested while another is in progress; skipping new attempt")
                        
        else :
            
            config = self._profile.config  # type: yowsup.config.v1.config.Config
            # event's keypair will override config's keypair
            local_static = config.client_static_keypair            
            username = int(self._profile.username)            
            device = config.device            
            
            if local_static is None:                
                logger.error("client_static_keypair is not defined in specified config, disconnecting")
                self.broadcastEvent(
                    YowLayerEvent(
                        YowNetworkLayer.EVENT_STATE_DISCONNECT,
                        reason="client_static_keypair is not defined in specified config"
                    )
                )
            else:

                
                if type(local_static) is bytes:
                    local_static = KeyPair.from_bytes(local_static)
                assert type(local_static) is KeyPair, type(local_static)
                passive =  event.getArg('passive')        
                yowsupenv = self.getProp("env").deviceEnv

                if config.fdid is None:
                    config.fdid = WATools.generatePhoneId(self.getProp("env"))
                    config.expid = WATools.generateDeviceId()
                    self._profile.write_config(config)                
                
                if config.device_name is not None:
                    yowsupenv.setOSName(config.os_name)
                    yowsupenv.setOSVersion(config.os_version)
                    yowsupenv.setManufacturer(config.manufacturer)
                    yowsupenv.setDeviceName(config.device_name)
                    yowsupenv.setDeviceModelType(config.device_model_type)
                else:
                    #保存默认值

                    config.os_name= yowsupenv.getOSName()
                    config.os_version = yowsupenv.getOSVersion()
                    config.manufacturer = yowsupenv.getManufacturer()
                    config.device_name = yowsupenv.getDeviceName2()
                    config.device_model_type = yowsupenv.getDeviceModelType()
                    
                    self._profile.write_config(config)


                self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, False)

                
                if config.edge_routing_info:                
                    self.toLower(self.EDGE_HEADER)
                    self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, True)
                    self.toLower(config.edge_routing_info)
                    self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, False)

                

                self.toLower(self.HEADER)
                self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, True)
                            
                remote_static = config.server_static_public
                self._rs = remote_static

                cc = Utils.getMobileCC(str(username))       
                lg,lc = Utils.getLGLC(cc)
                
                mcc =  "000"
                mnc = "000"
                
                client_config = ClientConfig(
                    username=username,
                    passive=passive,
                    useragent=UserAgentConfig(
                        platform=yowsupenv.getPlatform(),
                        app_version=yowsupenv.getVersion(),
                        mcc=mcc,
                        mnc=mnc,
                        os_version=yowsupenv.getOSVersion(),
                        manufacturer=yowsupenv.getManufacturer(),
                        device=yowsupenv.getDeviceName2(),
                        os_build_number=yowsupenv.getBuildVersion(),
                        phone_id=config.fdid or "",
                        locale_lang=lg,
                        locale_country=lc,
                        device_exp_id = base64.b64encode(config.expid).decode() if config.expid else "",                        
                        device_type=0,  #PHONE
                        device_model_type=yowsupenv.getDeviceModelType()
                    ),
                    pushname=config.pushname or self.DEFAULT_PUSHNAME,
                    short_connect=True                                      
                )

                if not self._in_handshake():
                    import threading
                    thread_id = threading.current_thread().ident
                    account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
                    self._handshake_attempt += 1
                    attempt_id = self._handshake_attempt
                    self._last_handshake_attempt = attempt_id
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] performing login handshake | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} username={username} passive={passive} deviceid={int(device) if device is not None else None} mcc={mcc} mnc={mnc} rs={'present' if remote_static else 'none'}")
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] client_config completo: platform={client_config.useragent.platform} app_version={client_config.useragent.app_version} os_version={client_config.useragent.os_version} manufacturer={client_config.useragent.manufacturer} device={client_config.useragent.device}")
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] local_static presente: {local_static is not None} remote_static presente: {remote_static is not None}")
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] stream object: {id(self._stream)} protocol state: {self._wa_noiseprotocol.state}")
                    self._handshake_worker = WANoiseProtocolHandshakeWorker(
                        self._wa_noiseprotocol, self._stream, client_config, local_static, remote_static,
                        self.on_handshake_finished,
                        deviceid = int(device) if device is not None else None,
                        attempt_id = attempt_id
                    )
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] starting handshake worker | worker_thread_id={self._handshake_worker.ident if hasattr(self._handshake_worker, 'ident') else 'N/A'}")
                    self._stream.set_events_callback(self._handle_stream_event)
                    self._handshake_worker.start()
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] handshake worker started | worker_thread_id={self._handshake_worker.ident}")
                else:
                    account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
                    logger.warning(f"[HANDSHAKE-DEBUG] Login handshake requested while another is in progress; skipping new attempt | account={account_id} current_state={self._wa_noiseprotocol.state} attempt_id={self._last_handshake_attempt}")

    def on_handshake_finished(self, e=None):
        # type: (Exception) -> None
        import threading
        import traceback
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        
        # Limpar referência do worker quando terminar
        self._handshake_worker = None
        
        if e is not None:
            error_msg = str(e)
            is_cancelled = "cancelled" in error_msg.lower() or "Stream cancelled" in error_msg
            
            if is_cancelled:
                # Handshake foi cancelado (provavelmente por desconexão) - não é um erro crítico
                logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] handshake cancelled | account={account_id} thread_id={thread_id} error={error_msg}")
            else:
                # Erro real durante handshake
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] handshake finished with error | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} error={e} error_type={type(e).__name__}")
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] error details: {str(e)}")
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] protocol state: {self._wa_noiseprotocol.state}")
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] stream state: {id(self._stream)}")
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] full traceback:\n{traceback.format_exc()}")
                self._maybe_break("NOISE_BREAK_ON_HANDSHAKE_ERROR")
                self.emitEvent(YowLayerEvent(self.EVENT_HANDSHAKE_FAILED, reason=e))
                data=WriteEncoder(TokenDictionary()).protocolTreeNodeToBytes(
                    ProtocolTreeNode("failure", {"reason": str(e)})
                )
                self.toUpper(data)            
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] An error occurred during handshake, try login again. | account={account_id}")
        else:
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] handshake finished successfully | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} state={self._wa_noiseprotocol.state}")
            
            # Fallback: Salvar server_static_public se disponível e ainda não foi salvo
            # Isso garante que a chave seja salva mesmo se _on_protocol_state_changed não for chamado
            if self._wa_noiseprotocol.rs is not None:
                # Verificar se já foi salvo (comparando com _rs local)
                needs_save = True
                if self._rs is not None and hasattr(self._rs, 'data') and hasattr(self._wa_noiseprotocol.rs, 'data'):
                    if self._rs.data == self._wa_noiseprotocol.rs.data:
                        needs_save = False
                        logger.debug(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] server_static_public já está salvo | account={account_id}")
                
                if needs_save:
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] Fallback: Salvando server_static_public em on_handshake_finished | account={account_id} state={self._wa_noiseprotocol.state}")
                    self._update_server_static_public(self._wa_noiseprotocol.rs)

    def _in_handshake(self):
        """
        :return:
        :rtype: bool
        """
        return self._wa_noiseprotocol.state == WANoiseProtocol.STATE_HANDSHAKE

        
    def _on_protocol_state_changed(self, state):
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] protocol state changed | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} old_state={getattr(self._wa_noiseprotocol, 'state', 'N/A')} new_state={state}")
        
        if state == WANoiseProtocol.STATE_TRANSPORT:
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] entering TRANSPORT state | account={account_id}")
            
            # Atualiza server_static_public se mudou (inclui nova chave estática recebida durante fallback XX)
            # Este é o caminho PRINCIPAL para salvar a chave estática
            if self._wa_noiseprotocol.rs is not None:
                new_rs_hex = self._wa_noiseprotocol.rs.data.hex()[:32] if hasattr(self._wa_noiseprotocol.rs, 'data') and self._wa_noiseprotocol.rs.data else "N/A"
                logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] [PRINCIPAL] Nova chave estática remota disponível, salvando no profile via _on_protocol_state_changed | account={account_id} rs_preview={new_rs_hex}...")
                self._update_server_static_public(self._wa_noiseprotocol.rs)
            else:
                logger.warning(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] Entrando em TRANSPORT mas rs é None | account={account_id}")
            
            self._flush_incoming_buffer()
            
        if state == WANoiseProtocol.STATE_ERROR and self._last_segment_preview:
            logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] protocol entered ERROR | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} last incoming segment {self._last_segment_preview}")
            self._maybe_break("NOISE_BREAK_ON_STATE_ERROR")
        logger.debug(f"[handshake {self._last_handshake_attempt}] protocol state changed to {state}")


    def _update_server_static_public(self, new_rs):
        """
        Atualiza a chave pública estática do servidor (server_static_public) no config
        e persiste no banco de dados.
        
        Este método é chamado quando o servidor do WhatsApp envia uma nova chave estática
        durante o handshake (por exemplo, quando ocorre NewRemoteStaticException e fallback
        para handshake XX).
        
        Args:
            new_rs: Nova chave pública estática do servidor (PublicKey)
        
        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário
        """
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        
        if new_rs is None:
            logger.warning(f"[HANDSHAKE-DEBUG] Tentativa de atualizar server_static_public com None | account={account_id}")
            return False
        
        # Verifica se realmente mudou
        # Compara os dados das chaves (bytes)
        old_rs_data = self._rs.data if self._rs is not None and hasattr(self._rs, 'data') else None
        new_rs_data = new_rs.data if hasattr(new_rs, 'data') else None
        
        if old_rs_data is not None and new_rs_data is not None and old_rs_data == new_rs_data:
            logger.debug(f"[HANDSHAKE-DEBUG] server_static_public não mudou, ignorando atualização | account={account_id}")
            return True
        
        old_rs_str = f"{old_rs_data.hex()[:16]}..." if old_rs_data else "None"
        new_rs_str = f"{new_rs_data.hex()[:16]}..." if new_rs_data else "None"
        
        logger.info(
            f"[HANDSHAKE-DEBUG] Atualizando server_static_public | "
            f"account={account_id} thread_id={thread_id} "
            f"old_rs={old_rs_str} new_rs={new_rs_str}"
        )
        
        try:
            if self._profile is None:
                logger.error(f"[HANDSHAKE-DEBUG] Profile não disponível para atualizar server_static_public | account={account_id}")
                return False
            
            config = self._profile.config
            config.server_static_public = new_rs
            self._profile.write_config(config)
            
            # Atualiza a referência local
            self._rs = new_rs
            
            # Log detalhado da nova chave salva
            saved_rs_hex = new_rs_data.hex() if new_rs_data else "N/A"
            logger.info(
                f"[HANDSHAKE-DEBUG] server_static_public atualizado com sucesso | "
                f"account={account_id} thread_id={thread_id} "
                f"new_rs_full_hex={saved_rs_hex[:64]}... (total {len(saved_rs_hex)//2} bytes)"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"[HANDSHAKE-DEBUG] Erro ao atualizar server_static_public | "
                f"account={account_id} thread_id={thread_id} error={e}",
                exc_info=True
            )
            return False

            
    def _handle_stream_event(self, event):
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event | account={account_id} thread_id={thread_id} event={event} attempt_id={self._last_handshake_attempt}")
        
        if event == BlockingQueueSegmentedStream.EVENT_WRITE:
            segment = self._stream.get_write_segment()
            logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event WRITE | account={account_id} thread_id={thread_id} segment_len={len(segment) if segment else 0} attempt_id={self._last_handshake_attempt}")
            logger.debug(f"[handshake {self._last_handshake_attempt}] stream event WRITE")
            self.toLower(segment)
        elif event == BlockingQueueSegmentedStream.EVENT_READ:
            logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event READ | account={account_id} thread_id={thread_id} aguardando segment da queue attempt_id={self._last_handshake_attempt}")
            logger.debug(f"[handshake {self._last_handshake_attempt}] stream event READ")
            segment = self._incoming_segments_queue.get(block=True)
            logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event READ | account={account_id} thread_id={thread_id} segment recebido, len={len(segment) if segment else 0} attempt_id={self._last_handshake_attempt}")
            self._stream.put_read_segment(segment)
        else:
            logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event OTHER | account={account_id} thread_id={thread_id} event={event} attempt_id={self._last_handshake_attempt}")
            logger.debug(f"[handshake {self._last_handshake_attempt}] stream event other={event}")

    def send(self, data):
        """
        :param data:
        :type data: bytearray | bytes
        :return:
        :rtype:
        """
        data = bytes(data) if type(data) is not bytes else data
        # Passa recovery_callback para o protocol.send()
        self._wa_noiseprotocol.send(data, recovery_callback=self._maybe_retry_handshake)

    def _flush_incoming_buffer(self):
        self._flush_lock.acquire()
        try:
            # Apenas processa mensagens quando o protocolo já está em TRANSPORT.
            if self._wa_noiseprotocol.state != WANoiseProtocol.STATE_TRANSPORT:
                return

            while self._incoming_segments_queue.qsize():
                self.toUpper(self._wa_noiseprotocol.receive())
        finally:
            self._flush_lock.release()

    def receive(self, data):
        """
        :param data:
        :type data: bytes
        :return:
        :rtype:
        """                    
        self._incoming_segments_queue.put(data)
        self._debug_segment_preview(data)
        # Só drena para cima quando já estamos em estado TRANSPORT; evita
        # chamar receive() do protocolo ainda em INIT/HANDSHAKE.
        if self._wa_noiseprotocol.state == WANoiseProtocol.STATE_TRANSPORT:
            self._flush_incoming_buffer()

    def _debug_segment_preview(self, data):
        """
        Guarda uma prévia do último segmento recebido para analisar falhas
        de handshake sem logar todo o payload.
        """
        try:
            preview = data[:64].hex()
            self._last_segment_preview = f"len={len(data)} hex64={preview}"
            logger.debug(f"[handshake {self._last_handshake_attempt}] incoming segment preview {self._last_segment_preview}")
        except Exception as e:
            logger.debug(f"[handshake {self._last_handshake_attempt}] could not preview segment: {e}")

    def _maybe_retry_handshake(self, reason=None):
        """
        Tenta recuperar de um estado congelado reiniciando o handshake.
        
        Args:
            reason: Razão pela qual a recuperação foi acionada
        """
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        
        # Não tenta recuperar se já há um handshake em progresso
        if self._in_handshake() or self._handshake_worker is not None:
            logger.debug(
                f"[HANDSHAKE-DEBUG] _maybe_retry_handshake ignorado: "
                f"handshake já em progresso | account={account_id} "
                f"state={self._wa_noiseprotocol.state} worker={self._handshake_worker is not None}"
            )
            return
        
        current_state = self._wa_noiseprotocol.state
        
        # Só tenta recuperar se estiver em ERROR ou HANDSHAKE preso
        if current_state not in (WANoiseProtocol.STATE_ERROR, WANoiseProtocol.STATE_HANDSHAKE):
            logger.debug(
                f"[HANDSHAKE-DEBUG] _maybe_retry_handshake ignorado: "
                f"estado não requer recuperação | account={account_id} state={current_state}"
            )
            return
        
        logger.warning(
            f"[HANDSHAKE-DEBUG] Tentando recuperar de estado congelado | "
            f"account={account_id} thread_id={thread_id} state={current_state} reason={reason}"
        )
        
        # Reseta o protocolo
        self._wa_noiseprotocol.reset()
        
        # Tenta reiniciar o handshake se houver profile disponível
        if self._profile is None:
            logger.warning(
                f"[HANDSHAKE-DEBUG] Não é possível recuperar: profile não disponível | "
                f"account={account_id}"
            )
            return
        
        # Emite evento de autenticação para tentar novo handshake
        # Isso será tratado pelo on_auth() que iniciará um novo handshake
        try:
            logger.info(
                f"[HANDSHAKE-DEBUG] Emitindo evento AUTH para reiniciar handshake | "
                f"account={account_id}"
            )
            # Emite evento de autenticação para forçar novo handshake
            self.broadcastEvent(
                YowLayerEvent(
                    YowAuthenticationProtocolLayer.EVENT_AUTH,
                    passive=False
                )
            )
        except Exception as e:
            logger.error(
                f"[HANDSHAKE-DEBUG] Erro ao tentar recuperar handshake | "
                f"account={account_id} error={e}",
                exc_info=True
            )

    def _maybe_break(self, env_var):
        if env_var in settings.debug_break_flags:
            import pdb; pdb.set_trace()


