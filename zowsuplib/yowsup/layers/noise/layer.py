from zowsuplib.consonance.config.appversion import AppVersionConfig
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
import threading
from typing import Optional

from loguru import logger
import json
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
        self._instance_id = id(self)  # ID único da instância para debug de isolamento
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
        self._last_client_config = None  # Armazena ClientConfig para salvar após handshake

    def __str__(self):
        return "Noise Layer"

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def on_disconnected(self, event):
        import threading
        import json
        import time
        from loguru import logger
        
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        thread_id = threading.current_thread().ident
        stack_id = id(self.getStack())
        
        logger.info(f"[HANDSHAKE-DEBUG] on_disconnected chamado | account={account_id} thread_id={thread_id} stack_id={stack_id} instance={self._instance_id}")
        
        # Verifica se o evento é para esta conta específica
        # (evita processar eventos de outras contas em caso de múltiplas contas)
        event_account_id = event.getArg("account_id") if hasattr(event, 'getArg') else None
        if event_account_id and event_account_id != account_id:
            logger.warning(f"[HANDSHAKE-DEBUG] on_disconnected ignorado: evento para outra conta | this_account={account_id} event_account={event_account_id} instance={self._instance_id}")
            return
        
        # Resetar protocolo
        self._wa_noiseprotocol.reset()
        
        # Cancelar stream para desbloquear handshake worker bloqueado
        # Apenas se o stream ainda não foi cancelado
        if self._stream and not self._stream.is_cancelled():
            logger.debug(f"[HANDSHAKE-DEBUG] Cancelando stream | account={account_id} instance={self._instance_id}")
            self._stream.cancel()
        elif self._stream:
            logger.debug(f"[HANDSHAKE-DEBUG] Stream já estava cancelado | account={account_id} instance={self._instance_id}")
        
        # Limpar referência do worker (a thread vai terminar naturalmente após detectar cancelamento)
        if self._handshake_worker is not None:
            worker_thread_id = self._handshake_worker.ident if hasattr(self._handshake_worker, 'ident') else 'N/A'
            logger.debug(f"[HANDSHAKE-DEBUG] Handshake worker ativo, será finalizado | account={account_id} worker_thread_id={worker_thread_id} instance={self._instance_id}")
            # Não fazer join() aqui para não bloquear - a thread vai terminar após detectar cancelamento
            self._handshake_worker = None

    @EventCallback(YowAuthenticationProtocolLayer.EVENT_AUTH)
    def on_auth(self, event):        
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        stack_id = id(self.getStack())
        logger.info(f"[HANDSHAKE-DEBUG] on_auth chamado | account={account_id} thread_id={thread_id} stack_id={stack_id} instance={self._instance_id}")
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
                account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
                
                # Reseta o stream se estiver cancelado ou em estado inconsistente
                if self._stream:
                    if self._stream.is_cancelled():
                        logger.info(f"[HANDSHAKE-DEBUG] Stream estava cancelado, resetando antes de novo handshake (reg) | account={account_id} instance={self._instance_id}")
                        self._stream.reset()
                    # Limpa a queue de segmentos recebidos para evitar dados antigos
                    while not self._incoming_segments_queue.empty():
                        try:
                            self._incoming_segments_queue.get_nowait()
                        except:
                            break
                
                self._handshake_attempt += 1
                attempt_id = self._handshake_attempt
                self._last_handshake_attempt = attempt_id
                logger.info(f"[handshake {attempt_id}] performing registration handshake | account={account_id} instance={self._instance_id} mcc={mcc} mnc={mnc} deviceid={deviceid if jid is not None else None}")
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
                
                # Usa _build_client_config para tentar reutilizar ClientConfig salvo
                client_config = self._build_client_config(config, yowsupenv, username, passive, device)
                # Armazena ClientConfig para salvar após handshake bem-sucedido
                self._last_client_config = client_config

                if not self._in_handshake():
                    import threading
                    thread_id = threading.current_thread().ident
                    account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
                    stack_id = id(self.getStack())
                    
                    # Reseta o stream se estiver cancelado ou em estado inconsistente
                    # Isso garante que cada handshake comece com um stream limpo
                    if self._stream:
                        if self._stream.is_cancelled():
                            logger.info(f"[HANDSHAKE-DEBUG] Stream estava cancelado, resetando antes de novo handshake | account={account_id} instance={self._instance_id}")
                            self._stream.reset()
                        # Limpa a queue de segmentos recebidos para evitar dados antigos
                        while not self._incoming_segments_queue.empty():
                            try:
                                self._incoming_segments_queue.get_nowait()
                            except:
                                break
                    
                    self._handshake_attempt += 1
                    attempt_id = self._handshake_attempt
                    self._last_handshake_attempt = attempt_id
                    
                    
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] performing login handshake | account={account_id} thread_id={thread_id} stack_id={stack_id} instance={self._instance_id} username={username} passive={passive} deviceid={int(device) if device is not None else None} mcc={client_config.useragent.mcc} mnc={client_config.useragent.mnc} rs={'present' if remote_static else 'none'}")
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] client_config completo: platform={client_config.useragent.platform} app_version={client_config.useragent.app_version} os_version={client_config.useragent.os_version} manufacturer={client_config.useragent.manufacturer} device={client_config.useragent.device} instance={self._instance_id}")
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] local_static presente: {local_static is not None} remote_static presente: {remote_static is not None} instance={self._instance_id}")
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] stream object: {id(self._stream)} protocol state: {self._wa_noiseprotocol.state} instance={self._instance_id}")
                    self._handshake_worker = WANoiseProtocolHandshakeWorker(
                        self._wa_noiseprotocol, self._stream, client_config, local_static, remote_static,
                        self.on_handshake_finished,
                        deviceid = int(device) if device is not None else None,
                        attempt_id = attempt_id
                    )
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] starting handshake worker | worker_thread_id={self._handshake_worker.ident if hasattr(self._handshake_worker, 'ident') else 'N/A'}")
                    # logger.info(f"[HANDSHAKE-DEBUG] [handshake {attempt_id}] handshake worker started | worker_thread_id={self._handshake_worker.ident}")
                    self._stream.set_events_callback(self._handle_stream_event)
                    self._handshake_worker.start()
                    
                else:
                    account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
                    logger.warning(f"[HANDSHAKE-DEBUG] Login handshake requested while another is in progress; skipping new attempt | account={account_id} current_state={self._wa_noiseprotocol.state} attempt_id={self._last_handshake_attempt}")

    def on_handshake_finished(self, e=None):
        # type: (Exception) -> None
        import threading
        import traceback
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        
        # CANCELAR STREAM IMEDIATAMENTE quando há erro para desbloquear thread bloqueada
        if e is not None:
            # Cancela o stream para desbloquear qualquer thread bloqueada em read_segment()
            if self._stream and not self._stream.is_cancelled():
                logger.info(
                    f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] "
                    f"Cancelando stream devido a erro no handshake | account={account_id} thread_id={thread_id} instance={self._instance_id}"
                )
                self._stream.cancel()
        
        # Limpar referência do worker quando terminar
        worker_thread_id = None
        if self._handshake_worker is not None:
            worker_thread_id = self._handshake_worker.ident if hasattr(self._handshake_worker, 'ident') else None
            logger.debug(
                f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] "
                f"Limpando referência do worker | account={account_id} worker_thread_id={worker_thread_id} instance={self._instance_id}"
            )
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
            
            # Salva ClientConfig após handshake bem-sucedido (pode ter sido atualizado)
            if hasattr(self, '_last_client_config') and self._last_client_config is not None:
                try:
                    logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] Salvando ClientConfig após handshake bem-sucedido | account={account_id}")
                    self._save_client_config(self._last_client_config)
                except Exception as save_error:
                    logger.warning(f"[HANDSHAKE-DEBUG] [handshake {self._last_handshake_attempt}] Erro ao salvar ClientConfig após handshake: {save_error}")
            
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
        try: 
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
                f"account={account_id} thread_id={thread_id} error={e}"
            )
            return False

            
    def _handle_stream_event(self, event):
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        stack_id = id(self.getStack())
        
        # Verifica se o stream foi cancelado antes de processar
        if self._stream and self._stream.is_cancelled():
            logger.warning(f"[HANDSHAKE-DEBUG] Stream cancelado, ignorando evento | account={account_id} thread_id={thread_id} event={event} instance={self._instance_id} attempt_id={self._last_handshake_attempt}")
            return
        
        logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event | account={account_id} thread_id={thread_id} stack_id={stack_id} instance={self._instance_id} event={event} attempt_id={self._last_handshake_attempt}")
        
        if event == BlockingQueueSegmentedStream.EVENT_WRITE:
            try:
                segment = self._stream.get_write_segment()
                # Verifica novamente se foi cancelado durante a operação
                if self._stream and self._stream.is_cancelled():
                    logger.warning(f"[HANDSHAKE-DEBUG] Stream cancelado durante WRITE, ignorando segment | account={account_id} instance={self._instance_id}")
                    return
                logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event WRITE | account={account_id} thread_id={thread_id} segment_len={len(segment) if segment else 0} attempt_id={self._last_handshake_attempt} instance={self._instance_id}")
                logger.debug(f"[handshake {self._last_handshake_attempt}] stream event WRITE")
                self.toLower(segment)
            except Exception as e:
                if "cancelled" in str(e).lower() or "Stream cancelled" in str(e):
                    logger.warning(f"[HANDSHAKE-DEBUG] Stream cancelado durante get_write_segment | account={account_id} instance={self._instance_id} error={e}")
                else:
                    logger.error(f"[HANDSHAKE-DEBUG] Erro em _handle_stream_event WRITE | account={account_id} instance={self._instance_id} error={e}", exc_info=True)
        elif event == BlockingQueueSegmentedStream.EVENT_READ:
            logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event READ | account={account_id} thread_id={thread_id} aguardando segment da queue attempt_id={self._last_handshake_attempt} instance={self._instance_id}")
            logger.debug(f"[handshake {self._last_handshake_attempt}] stream event READ")
            try:
                segment = self._incoming_segments_queue.get(block=True)
                logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event READ | account={account_id} thread_id={thread_id} segment recebido, len={len(segment) if segment else 0} attempt_id={self._last_handshake_attempt} instance={self._instance_id}")
                # Verifica novamente se foi cancelado durante a espera
                if self._stream and not self._stream.is_cancelled():
                    self._stream.put_read_segment(segment)
                else:
                    logger.warning(f"[HANDSHAKE-DEBUG] Stream cancelado durante READ, ignorando segment | account={account_id} instance={self._instance_id}")
            except Exception as e:
                if "cancelled" in str(e).lower() or "Stream cancelled" in str(e):
                    logger.warning(f"[HANDSHAKE-DEBUG] Stream cancelado durante READ | account={account_id} instance={self._instance_id} error={e}")
                else:
                    logger.error(f"[HANDSHAKE-DEBUG] Erro em _handle_stream_event READ | account={account_id} instance={self._instance_id} error={e}", exc_info=True)
        else:
            logger.debug(f"[HANDSHAKE-DEBUG] _handle_stream_event OTHER | account={account_id} thread_id={thread_id} event={event} attempt_id={self._last_handshake_attempt} instance={self._instance_id}")
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

    def _save_client_config(self, client_config: ClientConfig) -> bool:
        """
        Salva o ClientConfig no profile para reutilização no próximo auth.
        
        Args:
            client_config: ClientConfig a ser salvo
            
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            if self._profile is None:
                logger.warning("[HANDSHAKE-DEBUG] Profile não disponível para salvar ClientConfig")
                return False
            
            account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
            profile_name = self._profile._profile_name
            
            # Serializa ClientConfig para dict
            config_dict = {
                "username": client_config.username,
                "passive": client_config.passive,
                "pushname": client_config.pushname,
                "short_connect": client_config.short_connect,
                "connect_reason": client_config.connect_reason,
                "useragent": {
                    "platform": client_config.useragent.platform,
                    "mcc": client_config.useragent.mcc,
                    "mnc": client_config.useragent.mnc,
                    "os_version": client_config.useragent.os_version,
                    "manufacturer": client_config.useragent.manufacturer,
                    "device": client_config.useragent.device,
                    "os_build_number": client_config.useragent.os_build_number,
                    "phone_id": client_config.useragent.phone_id,
                    "locale_lang": client_config.useragent.locale_lang,
                    "locale_country": client_config.useragent.locale_country,
                    "device_exp_id": client_config.useragent.device_exp_id,
                    "device_type": client_config.useragent.device_type,
                    "device_model_type": client_config.useragent.device_model_type,
                }
            }
            
            # Salva no ProfileConfig com nome personalizado
            from zowsuplib.yowsup.common.tools import StorageTools
            from zowsuplib.app.db import thread_local_session
            from zowsuplib.app import models
            
            phone = StorageTools._extract_phone_from_profile_name(profile_name)
            if not phone:
                logger.error(f"[HANDSHAKE-DEBUG] Não foi possível extrair phone de profile_name={profile_name}")
                return False
            
            # Salva o dict diretamente - SQLAlchemy JSON serializa automaticamente
            with thread_local_session() as db:
                account = db.query(models.Account).filter_by(phone=phone).one_or_none()
                if account is None:
                    account = models.Account(phone=phone)
                    db.add(account)
                    db.flush()
                
                # Usa a nova tabela ClientConfig (one-to-one com Account)
                client_config = db.query(models.ClientConfig).filter_by(account_id=account.id).one_or_none()
                
                if client_config is None:
                    client_config = models.ClientConfig(
                        account_id=account.id,
                        config_data=config_dict,
                    )
                    db.add(client_config)
                    logger.info(f"[HANDSHAKE-DEBUG] ClientConfig criado na nova tabela | account={account_id} phone={phone}")
                else:
                    client_config.config_data = config_dict
                    logger.info(f"[HANDSHAKE-DEBUG] ClientConfig atualizado na nova tabela | account={account_id} phone={phone}")
                
                # Commit automático via context manager
                return True
            
        except Exception as e:
            account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
            logger.error(f"[HANDSHAKE-DEBUG] Erro ao salvar ClientConfig | account={account_id} error={e}", exc_info=True)
            return False

    def _load_client_config(self) -> Optional[ClientConfig]:
        """
        Carrega o ClientConfig salvo do profile, se disponível.
        
        Returns:
            ClientConfig ou None se não estiver salvo ou houver erro
        """
        try:
            if self._profile is None:
                return None
            
            account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
            profile_name = self._profile._profile_name
            
            # Tenta carregar do ProfileConfig
            from zowsuplib.yowsup.common.tools import StorageTools
            from zowsuplib.app.db import thread_local_session
            from zowsuplib.app import models
            
            phone = StorageTools._extract_phone_from_profile_name(profile_name)
            if not phone:
                return None
            
            with thread_local_session() as db:
                account = db.query(models.Account).filter_by(phone=phone).one_or_none()
                if not account:
                    logger.debug(f"[HANDSHAKE-DEBUG] Account não encontrado | account={account_id} phone={phone}")
                    return None
                
                # Usa a nova tabela ClientConfig (one-to-one com Account)
                client_config_row = db.query(models.ClientConfig).filter_by(account_id=account.id).one_or_none()
                
                if client_config_row is None:
                    logger.debug(f"[HANDSHAKE-DEBUG] ClientConfig não encontrado na nova tabela | account={account_id} phone={phone}")
                    return None
                
                config_data = client_config_row.config_data
            
            # SQLAlchemy JSON retorna dict diretamente, mas pode haver dados antigos em bytes (compatibilidade)
            if isinstance(config_data, bytes):
                # Compatibilidade: dados antigos salvos como bytes
                config_data = config_data.decode('utf-8')
                config_dict = json.loads(config_data)
            elif isinstance(config_data, str):
                # Compatibilidade: dados antigos salvos como string JSON
                config_dict = json.loads(config_data)
            else:
                # Novo formato: já é um dict
                config_dict = config_data
            
            yowsupenv = self.getProp("env").deviceEnv
            # Reconstrói UserAgentConfig
            from zowsuplib.consonance.config.appversion import AppVersionConfig
            useragent_dict = config_dict.get("useragent", {})


            useragent = UserAgentConfig(
                platform=useragent_dict.get("platform"),
                app_version=yowsupenv.getVersion(),
                mcc=useragent_dict.get("mcc", "000"),
                mnc=useragent_dict.get("mnc", "000"),
                os_version=useragent_dict.get("os_version"),
                manufacturer=useragent_dict.get("manufacturer"),
                device=useragent_dict.get("device"),
                os_build_number=useragent_dict.get("os_build_number"),
                phone_id=useragent_dict.get("phone_id", ""),
                locale_lang=useragent_dict.get("locale_lang", "en"),
                locale_country=useragent_dict.get("locale_country", "US"),
                device_exp_id=useragent_dict.get("device_exp_id", ""),
                device_type=useragent_dict.get("device_type", 0),
                device_model_type=useragent_dict.get("device_model_type")
            )
            
            # Reconstrói ClientConfig
            client_config = ClientConfig(
                username=config_dict.get("username"),
                passive=config_dict.get("passive", False),
                useragent=useragent,
                pushname=config_dict.get("pushname"),
                short_connect=config_dict.get("short_connect", True),
                connect_reason=config_dict.get("connect_reason")
            )
            
            logger.info(f"[HANDSHAKE-DEBUG] ClientConfig carregado do profile | account={account_id}")
            return client_config
            
        except Exception as e:
            account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
            logger.warning(f"[HANDSHAKE-DEBUG] Erro ao carregar ClientConfig, criando novo | account={account_id} error={e}")
            return None

    def _build_client_config(self, config, yowsupenv, username, passive, device=None) -> ClientConfig:
        """
        Constrói ClientConfig, tentando carregar do profile primeiro.
        Se não estiver disponível, cria novo e salva.
        
        Args:
            config: Config do profile
            yowsupenv: DeviceEnv
            username: Número de telefone
            passive: Se é conexão passiva
            device: Device ID (opcional)
            
        Returns:
            ClientConfig
        """
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        
        # Tenta carregar ClientConfig salvo
        saved_client_config = self._load_client_config()
        
        if saved_client_config is not None:
            # Atualiza campos que podem ter mudado
            # username pode mudar, então sempre usa o atual
            # phone_id e device_exp_id podem mudar, então atualiza do config
            cc = Utils.getMobileCC(str(username))
            lg, lc = Utils.getLGLC(cc)
            
            # Cria novo UserAgentConfig com dados atualizados
            useragent = UserAgentConfig(
                platform=saved_client_config.useragent.platform,
                app_version=saved_client_config.useragent.app_version,
                mcc=saved_client_config.useragent.mcc,
                mnc=saved_client_config.useragent.mnc,
                os_version=saved_client_config.useragent.os_version,
                manufacturer=saved_client_config.useragent.manufacturer,
                device=saved_client_config.useragent.device,
                os_build_number=saved_client_config.useragent.os_build_number,
                phone_id=config.fdid or saved_client_config.useragent.phone_id or "",
                locale_lang=lg or saved_client_config.useragent.locale_lang,
                locale_country=lc or saved_client_config.useragent.locale_country,
                device_exp_id=base64.b64encode(config.expid).decode() if config.expid else saved_client_config.useragent.device_exp_id or "",
                device_type=saved_client_config.useragent.device_type,
                device_model_type=saved_client_config.useragent.device_model_type
            )
            
            # Cria ClientConfig atualizado
            client_config = ClientConfig(
                username=username,
                passive=passive,
                useragent=useragent,
                pushname=config.pushname or saved_client_config.pushname or self.DEFAULT_PUSHNAME,
                short_connect=saved_client_config.short_connect,
                connect_reason=saved_client_config.connect_reason
            )
            
            logger.info(f"[HANDSHAKE-DEBUG] ClientConfig reutilizado do profile (com atualizações) | account={account_id}")
            return client_config
        
        # Se não encontrou salvo, cria novo
        cc = Utils.getMobileCC(str(username))
        lg, lc = Utils.getLGLC(cc)
        
        mcc = "000"
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
                device_exp_id=base64.b64encode(config.expid).decode() if config.expid else "",
                device_type=0,  # PHONE
                device_model_type=yowsupenv.getDeviceModelType()
            ),
            pushname=config.pushname or self.DEFAULT_PUSHNAME,
            short_connect=True
        )
        
        # Salva para próxima vez
        self._save_client_config(client_config)
        
        logger.info(f"[HANDSHAKE-DEBUG] Novo ClientConfig criado e salvo | account={account_id}")
        return client_config


