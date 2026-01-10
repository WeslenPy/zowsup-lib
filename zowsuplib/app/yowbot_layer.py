import sys

# coding=UTF-8
import random
from typing import Optional
from zowsuplib.yowsup.common import YowConstants
from zowsuplib.yowsup.layers import EventCallback, YowLayerEvent
from zowsuplib.yowsup.layers.noise.layer import YowNoiseLayer


#import group iq
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_subject import SubjectGroupsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_create import CreateGroupsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_info import InfoGroupsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_leave import LeaveGroupsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_list import ListGroupsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants import ParticipantsGroupsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_add import AddParticipantsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_promote import PromoteParticipantsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_demote import DemoteParticipantsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_remove import RemoveParticipantsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_add_success import SuccessAddParticipantsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_add_failure import FailureAddParticipantsIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_groups.protocolentities.iq_groups_participants_remove_success import SuccessRemoveParticipantsIqProtocolEntity


# Constante para detecção de erros de handshake
HANDSHAKE_FAILED_EVENT = YowNoiseLayer.EVENT_HANDSHAKE_FAILED
from zowsuplib.yowsup.layers.axolotl.protocolentities.iq_keys_get_result import ResultGetKeysIqProtocolEntity
from zowsuplib.yowsup.layers.interface  import YowInterfaceLayer, ProtocolEntityCallback
from zowsuplib.yowsup.layers.network.layer import YowNetworkLayer
from zowsuplib.yowsup.layers.protocol_messages.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_messages.protocolentities.attributes import *
from zowsuplib.yowsup.layers.protocol_chatstate.protocolentities import *
from zowsuplib.yowsup.layers.protocol_notifications.protocolentities import *
from zowsuplib.yowsup.layers.protocol_presence.protocolentities.presence import PresenceProtocolEntity
from zowsuplib.yowsup.layers.protocol_profiles.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_contacts.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_iq.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_ib.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_media.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_groups.protocolentities  import * 
from zowsuplib.yowsup.layers.protocol_privacy.protocolentities  import *
from zowsuplib.yowsup.layers.protocol_historysync.protocolentities.history_sync import HistorySync
from zowsuplib.yowsup.layers.protocol_historysync.protocolentities.attributes import *
from zowsuplib.yowsup.layers.axolotl.protocolentities.iq_key_get import GetKeysIqProtocolEntity
from zowsuplib.yowsup.layers.protocol_appstate.protocolentities.patch_builder import PatchBuilder
from zowsuplib.yowsup.layers.protocol_appstate.protocolentities.attributes import *
from zowsuplib.yowsup.layers.protocol_appstate.protocolentities.mutation_keys import MutationKeys
from zowsuplib.yowsup.layers.protocol_appstate.protocolentities.hash_state import HashState
from Crypto.Random import get_random_bytes
from zowsuplib.yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
from zowsuplib.yowsup.layers.protocol_presence.protocolentities import *
from zowsuplib.yowsup.layers.protocol_ib.protocolentities import *
from zowsuplib.yowsup.config.v1.config import Config
from zowsuplib.common.utils import Utils
from zowsuplib.yowsup.common.tools import WATools
from zowsuplib.yowsup.layers.protocol_media.mediacipher import MediaCipher
from zowsuplib.yowsup.common.tools import Jid
import requests,logging,io,os,time,mimetypes,base64,random,threading,qrcode
from zowsuplib.yowsup.common.optionalmodules import PILOptionalModule
from threading import Thread
from zowsuplib.proto import wsend_pb2,wa_struct_pb2
from zowsuplib.yowsup.profile.profile import YowProfile
from pathlib import Path
from .yowbot_values import YowBotType
from zowsuplib.axolotl.ecc.curve import Curve
from zowsuplib.axolotl.ecc.djbec import *
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from zowsuplib.yowsup.layers.protocol_presence.protocolentities.presence_subscribe import SubscribePresenceProtocolEntity

import uuid,traceback
from zowsuplib.app.param_not_enough_exception import ParamsNotEnoughException

from loguru import logger

class YowQrCodeThread(Thread):
    def __init__(self, layer, interval):
        assert type(layer) is SendLayer, "layer must be a SenderLayer, got %s instead." % type(layer)
        
        self._layer = layer
        self._interval = interval
        self._stop = False
        self.__logger = logger
        super(YowQrCodeThread, self).__init__()
        self.daemon = True
        self.name = "YowQrCode-%s" % self.name
    
    def run(self):
        while not self._stop:
            refs = self._layer.getProp("refs")
            if len(refs)>0:
                ref = refs.pop(0)
                regInfo = self._layer.getProp("reg_info")
                keypair = regInfo["keypair"]
                identity = regInfo["identity"]                
                advSecretKey = random.randbytes(32)
                print(f"{str(ref,'utf8')},{str(base64.b64encode(keypair.public.data),'utf8')},{str(base64.b64encode(identity.publicKey.serialize()[1:]),'utf8')},{str(base64.b64encode(advSecretKey),'utf8')}")
                qr = qrcode.QRCode()
                qr.border =1
                qr.add_data(f"{str(ref,'utf8')},{str(base64.b64encode(keypair.public.data),'utf8')},{str(base64.b64encode(identity.publicKey.serialize()[1:]),'utf8')},{str(base64.b64encode(advSecretKey),'utf8')}")
                qr.make()
                qr.print_ascii(out=None,tty=False,invert=False)                                                
                self._layer.setProp("refs",refs)
            else:
                self._stop = True                                                   
                self._layer.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
            for i in range(0, self._interval):                
                time.sleep(1)                
                if self._stop:
                    self.__logger.debug(f"{self.name} - QrThread stopped")
                    return

    def stop(self):
        self._stop = True        

class SendLayer(YowInterfaceLayer):

    PROP_MESSAGES = "org.openwhatsapp.yowsup.prop.sendclient.queue"
    PROP_WAAPI  = "org.openwhatsapp.yowsup.prop.sendclient.waapi"  

    def __init__(self,bot):
        super(SendLayer, self).__init__()
        self.ackQueue = []        
        self.isConnected = False  
        self.bot = bot      
        self.detect40x = False     
        self.detect503 = False     
        self.userQuit = False
        self.mode = None        
        logger = logging.getLogger(self.bot.botId if self.bot.botId is not None else "unknown")
        self.msgMap = {}    
        self.loginEvent = threading.Event()        
        self.cmdEventMap = {} 
        self.lastOnlineTimeStamp = None
        self.pingCount = 0             
        self.ctxMap = {}
        self._qrThread=None
        self.pairingStatus = None
        self.message_callback = None  # Callback customizado para mensagens
        self.handshake_failed_callback = None  # Callback para erros de handshake
        
        # Sistema anti-banimento: controle de envio
        self._last_sync_time = {}  # {jid: timestamp} para controle de sincronização
        self._invalid_numbers = set()  # Números inválidos conhecidos (evita tentar novamente)
        self._handshake_error_detected = False  # Flag para detectar erros de handshake
        self._message_notifications_enabled = True  # Controle de callbacks de mensagem
        self._login_failed = False  # Flag para diferenciar falha de login x sucesso
        self._login_in_progress = False  # Flag para indicar que login está em andamento
        self._pending_notifications_count = 0  # Contador de notificações pendentes durante login
        
        # Sistema de filtragem de notificações
        self._notification_filter_enabled = True  # Ativa/desativa filtragem
        self._important_notification_types = self._get_default_important_notifications()
        self._ignored_notification_types = self._get_default_ignored_notifications()
        self._login_timeout = 20  # Timeout padrão para login (segundos)
        self._max_login_timeout = 120  # Timeout máximo para login com notificações pendentes
        # Threads auxiliares: usar timers para reagendar ações sem bloquear a thread do stack
        self._timers: list[threading.Timer] = []
        # Controle de reconexão com backoff
        self._reconnect_attempts = 0
        self._reconnect_timer: Optional[threading.Timer] = None
        # Marca se ocorreu stream:error conflict
        self._last_stream_conflict = False
        # Armazena último erro IQ (ex: 463 account_reachout_restricted)
        self._last_iq_error: Optional[str] = None

    def _cancel_reconnect_timer(self):
        if self._reconnect_timer and self._reconnect_timer.is_alive():
            try:
                self._reconnect_timer.cancel()
            except Exception:
                pass
        self._reconnect_timer = None

    def _can_reconnect(self) -> bool:
        """
        Valida se a conta deve tentar reconectar.
        Hoje: bloqueia se a conta está marcada com restrição no banco.
        """
        if self.bot.botId is None:
            return True
        try:
            from zowsuplib.app.db import SessionLocal
            from zowsuplib.app import models
            db = SessionLocal()
            try:
                has_restriction = (
                    db.query(models.Account.has_restriction)
                    .filter_by(phone=self.bot.botId)
                    .scalar()
                )
                if has_restriction:
                    logger.warning(f"{self.bot.botId} está com restrição; não será reconectada automaticamente")
                    return False
            finally:
                db.close()
        except Exception as exc:
            logger.error(f"Erro ao validar restrição antes de reconectar {self.bot.botId}: {exc}")
        return True

    def _schedule_event(self, delay: float, fn) -> None:
        """Agenda uma função sem bloquear a thread atual."""
        timer = threading.Timer(delay, fn)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)
                
    def quit(self):
        self.userQuit = True
        self.onDisconnected(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))   

    def setCmdEvent(self,iqid,event):
        self.cmdEventMap[iqid] = {"event":event,"result":"None"}

    def getCmdResult(self,iqid,timeout):        
        if iqid in self.cmdEventMap:
            obj =self.cmdEventMap[iqid]
            if obj["event"].wait(timeout):
                del self.cmdEventMap[iqid]
                if "error" not in obj :
                    return "",obj["result"],False
                else:
                    if obj["error"]=="redirect":
                        return obj["error"],obj["result"],False
                    else:
                        return obj["error"],"",False
            else:
                self.cmdEventMap[iqid]
                #timeout
                return None,None,True                
        else:
            return "404",None,False
        
    def setMsgMap(self,taskId,targets,msgId):
        if taskId is not None:
            array = targets.split(",")
            for target in array:
                self.msgMap[taskId+"-"+target] = msgId

    def getMsgIdFromMsgMap(self,taskId,target):
        if taskId is None:
            return None        
        if (taskId+"-"+target) in self.msgMap:
            return  self.msgMap[taskId+"-"+target]
        return None

    def genProfile(self,device_identity):
        regInfo = self.getProp("reg_info")
        regid = regInfo["regid"]
        keypair = regInfo["keypair"]
        jid = self.getProp("jid")
        phone,a,deviceid = WATools.jidDecode(jid)
        identity = regInfo["identity"]
        cc = Utils.getMobileCC(phone)        
        mccmnc = {
            "mcc":"000",
            "mnc":"000"
        }                    
        config = Config(        
            cc=cc,
            mcc=mccmnc["mcc"],
            mnc=mccmnc["mnc"],
            phone=phone,
            device=int(deviceid),           
            client_static_keypair=keypair,
            device_identity=str(base64.b64encode(device_identity.SerializeToString()),'UTF-8')
        )
        # Usa apenas o identificador lógico de perfil (phone_deviceid), sem ACCOUNT_PATH
        profile_name = f"{phone}_{deviceid}"
        profile = YowProfile(profile_name, config)
        profile.write_config(config)
        db = profile.axolotl_manager

        q = "UPDATE identities SET registration_id=? , public_key=? , private_key=?,device_id=? WHERE recipient_id=-1"
        c = db._store.identityKeyStore.dbConn.cursor()
        pubKey = identity.publicKey.serialize()
        privKey = identity.privateKey.serialize()
        c.execute(q, (regid,                            
                    pubKey,
                    privKey,
                    deviceid))
        signedprekey = regInfo["signedprekey"]
        db._store.storeSignedPreKey(signedprekey.getId(), signedprekey)
        db._store.removeAllPreKeys()
        db._store.identityKeyStore.dbConn.commit()        

    @ProtocolEntityCallback("chatstate")
    def onTyping(self, event):
        logger.info("Typing")
        logger.info(f"Typing: {event}")

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onDisconnected(self, yowLayerEvent):             
        logger.info("Disconnect")       
        error = self.getStack().getProp("exception")                
        # Cancela timers de reconexão pendentes
        for t in self._timers:
            try:
                t.cancel()
            except Exception:
                pass
        self._timers.clear()
        self._cancel_reconnect_timer()
        # Se foi timeout de ping, limpa a prop para próxima tentativa
        try:
            if self.getStack().getProp("org.openwhatsapp.yowsup.prop.pingtimeout"):
                logger.warning(f"{self.bot.botId} desconectou por ping timeout; agendando reconexão imediata")
                self.getStack().setProp("org.openwhatsapp.yowsup.prop.pingtimeout", False)
        except Exception:
            pass
        if self.getProp("jid") is not None:           
            if self._qrThread:
                self._qrThread.stop()
            waNum,a,deviceid = WATools.jidDecode(self.getProp("jid"))
            logger.info(f"Companion device register success({waNum}_{deviceid})")        
            self.setProp("jid",None)
            # Reaponta o stack para o perfil lógico (sem ACCOUNT_PATH) sem bloquear a thread
            self._schedule_event(
                1,
                lambda: (
                    self.getStack().setProfile(f"{waNum}_{deviceid}"),
                    self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)),
                ),
            )
            return        
        if self.getProp("refs") is not None and len(self.getProp("refs"))==0:            
            self._schedule_event(
                1,
                lambda: self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)),
            )
            return
        
        if self.isConnected:     
            self.eventCallback(wsend_pb2.BotEvent.Event.LOGOUT)
            # Atualiza status da conta no banco de dados - marca como não logada
            if self.bot.botId is not None:
                from zowsuplib.app.db import update_account_status
                update_account_status(self.bot.botId, is_logged_in=False)

        self.isConnected = False       
            
        if (not self.detect40x) and (not self.userQuit):     
            self.bot.wa_old = None               
            self.loginEvent.clear()
            self._handshake_error_detected = False
            self._login_failed = False
            if not self._can_reconnect():
                logger.info(f"{self.bot.botId} reconexão abortada pela validação de restrição/estado")
                return
            # backoff exponencial com teto de 60s + jitter leve
            self._reconnect_attempts += 1
            base_delay = 1
            delay = min(base_delay * (2 ** (self._reconnect_attempts - 1)), 60)
            delay += random.uniform(0, 0.5)
            logger.info(
                f"{self.bot.botId} agendando reconexão em {delay:.1f}s (tentativa {self._reconnect_attempts})"
            )
            self._cancel_reconnect_timer()
            self._reconnect_timer = threading.Timer(
                delay,
                lambda: self.getStack().broadcastEvent(
                    YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)
                ),
            )
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()

        else:                                                      
            self.eventCallback(wsend_pb2.BotEvent.Event.QUIT)                
    
    @EventCallback(HANDSHAKE_FAILED_EVENT)
    def onHandshakeFailed(self, event):
        """
        Detecta erros de handshake e marca para rotação de ambiente.
        """
        import threading
        import traceback
        thread_id = threading.current_thread().ident
        reason = getattr(event, 'reason', None) or str(event)
        account_id = self.bot.botId if self.bot.botId else 'unknown'
        logger.error(f"[HANDSHAKE-DEBUG] onHandshakeFailed chamado | account={account_id} thread_id={thread_id} reason={reason} event={event}")
        logger.error(f"[HANDSHAKE-DEBUG] onHandshakeFailed stack trace:\n{traceback.format_stack()}")
        logger.error(f"[{account_id}] Erro de handshake detectado: {reason}")
        self._handshake_error_detected = True
        
        # Chama callback customizado se configurado
        if self.handshake_failed_callback:
            try:
                logger.info(f"[HANDSHAKE-DEBUG] onHandshakeFailed chamando callback | account={account_id}")
                self.handshake_failed_callback(reason=reason, bot_id=self.bot.botId)
                logger.info(f"[HANDSHAKE-DEBUG] onHandshakeFailed callback retornou | account={account_id}")
            except Exception as e:
                logger.error(f"[HANDSHAKE-DEBUG] onHandshakeFailed erro ao chamar callback | account={account_id} error={e}")
                logger.error(f"Erro ao chamar callback de handshake failed: {e}")
        
        # Marca que houve erro de handshake (pode ser usado para rotação de ambiente)
        logger.warning(f"[HANDSHAKE-DEBUG] [{account_id}] Handshake falhou. Considere tentar outro tipo de ambiente. | thread_id={thread_id}")    

    
    @ProtocolEntityCallback("notification")
    def onNotification(self,entity):        
        # Durante o login, incrementa contador de notificações pendentes
        if self._login_in_progress:
            self._pending_notifications_count += 1
            # Se há muitas notificações pendentes, loga para debug
            if self._pending_notifications_count % 10 == 0:
                logger.debug(f"[{self.bot.botId}] {self._pending_notifications_count} notificações pendentes durante login")

        if not self._message_notifications_enabled:
            logger.debug("Notificação de mensagem ignorada (desativada)")
            return

        # Sistema de filtragem de notificações
        if not self._is_notification_important(entity):
            entity_type = type(entity).__name__
            logger.debug(f"[{self.bot.botId}] Notificação ignorada pelo filtro: {entity_type}")
            return

        if isinstance(entity,MexUpdateNotificationProtocolEntity):            
            # Durante login, processa notificações mex de forma mais rápida (sem logging detalhado)
            if self._login_in_progress:
                logger.debug(f"Notification: MexUpdate durante login (ignorando detalhes)")
            else:
                logger.info(f"Notification: Received a MexUpdate Notification: {entity.jsonObj}")            
            return
        
        if isinstance(entity,AccountSyncNotificationProtocolEntity):
            # Durante login, adia processamento pesado de AccountSync
            if self._login_in_progress:
                logger.debug("Notification: AccountSync durante login (processamento adiado)")
                # Agenda processamento para depois do login usando Timer (orientado a eventos)
                # Não usa sleep - aguarda o evento de login completar
                def process_account_sync_after_login():
                    # Aguarda login completar verificando o flag (orientado a eventos)
                    max_wait = 10  # Máximo 10 segundos esperando login
                    waited = 0
                    while waited < max_wait and self._login_in_progress:
                        time.sleep(0.5)  # Polling leve (500ms)
                        waited += 0.5
                    if self.isConnected:
                        self._process_account_sync_notification(entity)
                
                timer = threading.Timer(2.0, process_account_sync_after_login)
                timer.daemon = True
                timer.start()
                return
            
            logger.info("Notification: Received a AccountSync Notification")            
            companionJid = self.getStack().getProp("pair-companion-jid")
            if companionJid is None :
                return
            
            # Processa AccountSync normalmente (código original)
            entity = GetKeysIqProtocolEntity([companionJid],_id=self.bot.idType)        
            def on_get_encrypt_success(entity, original_iq_entity):

                entity = ProtocolMessageProtocolEntity(protocol_attr=ProtocolAttributes(                    
                    type = ProtocolAttributes.TYPE_INITIAL_SECURITY_NOTIFICATION_SETTING_SYNC,
                    initial_security_notification_setting_sync=  InitialSecurityNotificationSettingSyncAttribute(
                        security_notification_enabled=True
                    )
                ),message_meta_attributes=MessageMetaAttributes(
                    recipient=companionJid,
                    category="peer"
                ))

                self.toLower(entity)                
                sync_keys = self.generateAppStateSyncKeys(10)

                self.db._store.addAppStateKeys(sync_keys)

                entity = ProtocolMessageProtocolEntity(protocol_attr=ProtocolAttributes(                    
                    type  = ProtocolAttributes.TYPE_APP_STATE_SYNC_KEY_SHARE,
                    app_state_sync_key_share= AppStateSyncKeyShareAttribute(
                        keys = sync_keys
                    )

                ),message_meta_attributes=MessageMetaAttributes(
                    recipient=companionJid,
                    category="peer"
                ))        
                
                self.toLower(entity)
                time.sleep(1)           

                def on_get_conn_success(conn_entity, original_iq_entity):   

                    hs = HistorySync(conn_entity,companionJid)

                    et = hs.createNonBlockingDataMessage()
                    self.toLower(et)
                    et = hs.createInitialStatusV3Message()
                    self.toLower(et)
                    et = hs.createPushNameMessage()
                    self.toLower(et)
                    et = hs.createInitialBootstrapMessage(conversations=[ConversationAttribute(id="TEST")])
                    self.toLower(et)
                    et = hs.createRecentMessage()
                    self.toLower(et)
                    
                    et = TrustContactIqProtocolEntity(Jid.normalize(self.bot.botId),int(time.time()))
                    self.toLower(et)

                    #######################APP STATE SYNC START###############################

                    #  critical_block critical_unblock_low
                
                    key = self.db._store.getOneAppStateKey()  
                    mutationKeys = MutationKeys.createFromKey(key.key_data.key_data)

                    localeSetting = SyncActionDataAttribute.createFromSyncActionValue(SyncActionValueAttribute(
                                localeSetting=SyncActionLocaleSettingAttribute(locale="zh_CN")
                            ))     
                    pushNameSetting = SyncActionDataAttribute.createFromSyncActionValue(SyncActionValueAttribute(
                                pushNameSetting=SyncActionPushnameSettingAttribute(name="enx test")                            
                            ))    

                    state = HashState("critical_block",0)                        
                    state,syncdPatch1 = PatchBuilder(state,mutationKeys,key).addMutation(localeSetting).addMutation(pushNameSetting).finish()                                                            
     
                    name1 = SyncActionDataAttribute.createFromSyncActionValue(SyncActionValueAttribute(
                                contactAction=SyncActionContactActionAttribute(fullName="test user",firstName="test",lidJid="8618502060000@s.whatsapp.net")                           
                            ).setArgs(["8618502060000@s.whatsapp.net"]))     
         

                    state2 = HashState("critical_unblock_low",0)
                    state2,syncdPatch2  = PatchBuilder(state2,mutationKeys,key).addMutation(name1).finish()

                                      
                    entity = AppSyncStateIqProtocolEntity(
                        patches= {
                            "critical_unblock_low":syncdPatch2.encode(),
                            "critical_block":syncdPatch1.encode()
                        }                    
                    )

                    self.toLower(entity)

                def on_get_conn_error(entity, original_iq_entity):  
                    print("get conn error")

                conniq = RequestMediaConnIqProtocolEntity()
                self._sendIq(conniq,on_get_conn_success,on_get_conn_error)

            def on_get_encrypt_error(entity, original_iq_entity):
                print("error get encrypt")

            self._sendIq(entity, on_get_encrypt_success, on_get_encrypt_error)
            return
    
    def _process_account_sync_notification(self, entity):
        """Processa notificação AccountSync de forma isolada (usado quando adiado durante login)."""
        # Durante login, simplesmente ignora AccountSync (será processado depois naturalmente)
        logger.debug("AccountSync adiado durante login será processado após login completar")
        # Não faz nada - a notificação será processada naturalmente quando chegar novamente

        if isinstance(entity, LinkCodeCompanionRegNotificationProtocolEntity):
            logger.info(f"Notification: Received a LinkCodeCompanionReg, stage={entity.stage}")

            if entity.stage == "primary_hello":                
                linkCode = self.bot.pairLinkCode
                #这个时候是配对请求，直接回复一个hello就行了
                #丢到应用层处理            
                primaryEphemeralPub = Utils.link_code_decrypt(linkCode,entity.linkCodePairingWrappedPrimaryEphemeralPub)                                
                shareEphemeralSecret = Curve.calculateAgreement(DjbECPublicKey(primaryEphemeralPub),DjbECPrivateKey(self.getProp("reg_info")["keypair"].private.data))                                
                linkCodePairingEphemeralRootSecret = get_random_bytes(32)
                encryptPayload  = self.getProp("reg_info")["identity"].publicKey.serialize()[1:]+entity.primaryIdentityPublic+linkCodePairingEphemeralRootSecret
                companionFinishKdfSalt = get_random_bytes(32)
                linkCodePairingKeyBundleEncryptionKey = Utils.extract_and_expand(shareEphemeralSecret,"link_code_pairing_key_bundle_encryption_key".encode(),32,companionFinishKdfSalt)                
                companionFinishIV  = get_random_bytes(12)
                cipher = AESGCM(linkCodePairingKeyBundleEncryptionKey)
                encrypted  = cipher.encrypt(companionFinishIV,encryptPayload, b'')                
                encryptedPayload = companionFinishKdfSalt + companionFinishIV + encrypted
                identitySharedKey = Curve.calculateAgreement(DjbECPublicKey(entity.primaryIdentityPublic),DjbECPrivateKey(self.getProp("reg_info")["identity"].privateKey.serialize()))
                linkingSecretKeyMaterial = shareEphemeralSecret+identitySharedKey+linkCodePairingEphemeralRootSecret
                advSecretPublicKey = Utils.extract_and_expand(linkingSecretKeyMaterial,"adv_secret".encode(),32)                  
                entity = MultiDevicePairCompanionFinishIqProtocolEntity(self.bot.pairPhoneNumber+"@s.whatsapp.net",encryptedPayload, self.getProp("reg_info")["identity"].publicKey.serialize()[1:],entity.linkCodePairingRef)
                self.toLower(entity)

                return 
                                                
            if entity.stage == "companion_hello":              
                logger.info("ENTERING WAITING CODE STATUS")
                self.pairingStatus = "WAIT_PAIRINGCODE"
                self.companionHelloEntity = entity  
                                                  
            if entity.stage == "companion_finish":
                if self.getProp("keypair") is None:
                    return 

                ref = entity.linkCodePairingRef
                primaryEphemerKeyPair = self.getProp("keypair")
                companionEphemerPub = self.getProp("companionEphemerPub")
                companionIdentityPublic = entity.companionIdentityPublic
                companionServerAuthKeyPub = self.getProp("companionAuthKeyPub")
                companionFinishKdfSalt = entity.linkCodePairingWrappedKeyBundle[:32]
                companionFinishIV = entity.linkCodePairingWrappedKeyBundle[32:44]
                linkCodePairingEncryptedKeyBundle = entity.linkCodePairingWrappedKeyBundle[44:]
                shareEphemeralSecret = Curve.calculateAgreement(DjbECPublicKey(companionEphemerPub),DjbECPrivateKey(self.getProp("keypair").private.data))
                linkCodePairingKeyBundleEncryptionKey = Utils.extract_and_expand(shareEphemeralSecret,"link_code_pairing_key_bundle_encryption_key".encode(),32,companionFinishKdfSalt)
                cipher = AESGCM(linkCodePairingKeyBundleEncryptionKey)
                linkCodePairingKeyBundle  = cipher.decrypt(companionFinishIV,linkCodePairingEncryptedKeyBundle, b'')                     
                identitySharedKey = Curve.calculateAgreement(DjbECPublicKey(companionIdentityPublic),DjbECPrivateKey(self.db.identity.privateKey.serialize()))
                linkCodePairingEphemeralRootSecret = linkCodePairingKeyBundle[-32:]
                linkingSecretKeyMaterial = shareEphemeralSecret+identitySharedKey+linkCodePairingEphemeralRootSecret
                advSecretPublicKey = Utils.extract_and_expand(linkingSecretKeyMaterial,"adv_secret".encode(),32)                  
                self.resetSync([],{})
                time.sleep(1)                
                profile = self.getProp("profile")
                ref,pubKey,deviceIdentity,keyIndexList = Utils.generateMultiDeviceParams(ref,companionServerAuthKeyPub,companionIdentityPublic,advSecretPublicKey,profile)                                                
                entity = MultiDevicePairDeviceIqProtocolEntity(ref=ref,pubKey=pubKey,deviceIdentity=deviceIdentity,keyIndexList=keyIndexList)                

                def on_pair_device_success(entity, original_iq_entity):                    
                    companionJid = entity.deviceJid
                    deviceIdx =  int(companionJid.split("@")[0].split(":")[1])
                    profile.config.add_device_to_list(deviceIdx)
                    profile.write_config(profile.config)
                    self.getStack().setProp("pair-companion-jid",companionJid)
                    
                def on_pair_device_error(entity, original_iq):         
                    logger.error("pair device error")               
                    self.quit()            

                self._sendIq(entity, on_pair_device_success, on_pair_device_error)                

        if isinstance(entity,WaOldCodeNotificationProtocolEntity):
            logger.info(f"Notification: Received a wa_old registration code: {entity.code} in {entity.timestamp}")                  
            return 
                    
        if isinstance(entity,CreateGroupsNotificationProtocolEntity):
            logger.info(f"Notification: Group {entity.groupId} created")
            return 
        
        if isinstance(entity,AddGroupsNotificationProtocolEntity):
            n = wsend_pb2.Notification()
            n.id = entity.getId()                               
            n.type = wsend_pb2.Notification.Type.Value("GROUP")
            n.sender = entity.getGroupId()
            n.target = self.bot.botId
            n.group_notification.action = wsend_pb2.Notification.GroupNotification.Action.Value("ADD")
            n.group_notification.reason = "invite"            
            n.group_notification.jids.extend(entity.getParticipants())                   
            logger.info(f"Notification: Group {n.sender} add participant {entity.getParticipants()[0]}")
            return
        
        if isinstance(entity,RemoveGroupsNotificationProtocolEntity):
            n = wsend_pb2.Notification()
            n.id = entity.getId()       
            n.sender = entity.getGroupId()
            n.target = self.bot.botId                                    
            n.type = wsend_pb2.Notification.Type.Value("GROUP")
            n.group_notification.action = wsend_pb2.Notification.GroupNotification.Action.Value("REMOVE")                  
            n.group_notification.jids.extend(entity.getParticipants())                 
            logger.info(f"Notification: Group {n.sender} remove participant {entity.getParticipants()[0]}")       
            return    
        
        if isinstance(entity,SetPictureNotificationProtocolEntity):
            if entity.setJid is not None:
                self.eventCallback(wsend_pb2.BotEvent.Event.CONTACT_UPDATE,contactUpdate={"target":entity.setJid.split("@")[0],"key":"AVATAR","value":entity.setId})
            return 
        
        if isinstance(entity,BusinessNameUpdateNotificationProtocolEntity):
            if entity.name is not None:
                self.eventCallback(wsend_pb2.BotEvent.Event.CONTACT_UPDATE,contactUpdate={"target":entity.jid.split("@")[0],"key":"NAME","value":entity.name})
            return 
        
        if isinstance(entity,BusinessRemoveNotificationProtocolEntity):
            if entity.jid is not None:
                self.eventCallback(wsend_pb2.BotEvent.Event.CONTACT_UPDATE,contactUpdate={"target":entity.jid.split("@")[0],"key":"REMOVE","value":"True"})
            return         
        
        if isinstance(entity,DisapperingModeNotificationProtocolEntity):
            self.eventCallback(wsend_pb2.BotEvent.Event.CONTACT_UPDATE,contactUpdate={"target":entity._from.split("@")[0],"key":"DISAPPEARING_MODE_DURATION","value":entity.duration})

                                
    def setCmdRedirect(self,cmdId,cmdName,cmdParams,options,context):        
        if cmdId in self.cmdEventMap: 
            obj = self.cmdEventMap[cmdId]
            obj["error"] = "redirect"
            obj["result"] = {
                "cmdName":cmdName,
                "cmdParams":cmdParams,
                "options":options,
                "context":context
            }
            obj["event"].set()

    def setCmdResult(self,cmdId,result):
        self.bot.setCmdResult(cmdId,result)

    def setCmdError(self,cmdId,error):        
        self.bot.setCmdError(cmdId,error)

    @ProtocolEntityCallback("presence")            
    def onPresence(self,entity):
        if isinstance(entity,PresenceProtocolEntity):
            self.setCmdResult(entity.getId(),{
                "type":entity.getType(),
                "last":entity.getLast()
            })
            return
                         
    @ProtocolEntityCallback("iq")
    def onIq(self, entity):          
        # processIqRegistry é chamado primeiro no receive() da YowInterfaceLayer
        # Se o callback foi chamado, não chegamos aqui
        # Se chegamos aqui, é porque não havia callback registrado ou processIqRegistry não encontrou o ID
                        
        if isinstance(entity,ResultIqProtocolEntity):
            iq_id = entity.getId()
            # Verifica se há callback registrado para este IQ (pode ter sido processado mas ainda estar no registry)
            if hasattr(self, 'iqRegistry') and iq_id in self.iqRegistry:
                # Se há callback registrado, não define resultado aqui
                # O callback será chamado pelo processIqRegistry
                logger.debug(f"IQ {iq_id} tem callback registrado, deixando processIqRegistry tratar")
                return
            # Define resultado genérico apenas para IQs sem callback específico
            logger.debug(f"IQ {iq_id} sem callback, definindo resultado genérico")
            self.setCmdResult(iq_id, {"status": "ok"})
            return 
        
        if isinstance(entity,ErrorIqProtocolEntity):
            # Captura erros IQ específicos
            error_code = str(entity.code) if hasattr(entity, "code") and entity.code else None
            error_text = str(entity.text) if hasattr(entity, "text") and entity.text else None
            
            # Detecta erro 463 (account_reachout_restricted)
            if error_code == "463" and error_text == "account_reachout_restricted":
                self._last_iq_error = f"iq_error_463_account_reachout_restricted"
                logger.warning(f"IQ Error 463: account_reachout_restricted detected")
            elif error_code:
                # Armazena erro IQ genérico
                self._last_iq_error = f"iq_error_{error_code}_{error_text or 'unknown'}"
                logger.debug(f"IQ Error detected: code={error_code}, text={error_text}")
            
            self.setCmdError(entity.getId(),entity.code)
            return 
                        
        if isinstance(entity,ResultGetKeysIqProtocolEntity):                  
            return
                 
        if isinstance(entity, MultiDevicePairIqProtocolEntity):                              

            if self.getProp("botType")==YowBotType.TYPE_REG_COMPANION_SCANQR:
                logger.info("QRCode Pairing")
                ack = IqProtocolEntity(to = YowConstants.WHATSAPP_SERVER,_type="result",_id=entity.getId())       
                self._sendIq(ack)     
                self.setProp("refs",entity.refs)
                #开始一个展示二维码的thread
                self._qrThread = YowQrCodeThread(self, 20)            
                self._qrThread.start()
                return 
            elif self.getProp("botType")==YowBotType.TYPE_REG_COMPANION_LINKCODE:
                logger.info("LinkCode Pairing")
                ack = IqProtocolEntity(to = YowConstants.WHATSAPP_SERVER,_type="result",_id=entity.getId())
                self._sendIq(ack)
                identity = self.getProp("reg_info")["identity"]                
                linkCodePairingWrappedCompanionEphemeralPub = Utils.link_code_encrypt(self.bot.pairLinkCode,self.getProp("reg_info")["keypair"].public.data)
                companionServerAuthKeyPub = self.getProp("reg_info")["keypair"].public.data
                jid = self.bot.pairPhoneNumber+"@s.whatsapp.net"                
                entity = MultiDevicePairCompanionHelloIqProtocolEntity(jid,shouldshowPushNotification="true",linkCodePairingWrappedCompanionEphemeralPub=linkCodePairingWrappedCompanionEphemeralPub,companionServerAuthKeyPub=companionServerAuthKeyPub)
                self.toLower(entity)
                
                return 

        if isinstance(entity, MultiDevicePairSuccessIqProtocolEntity):                               
            jid = entity.jid
            self.setProp("refs",None)          
            self.setProp("jid",jid)     
            self.setProp("botType",YowBotType.TYPE_RUN_AUTO)
            p1 = wa_struct_pb2.ADVSignedDeviceIdentityHMAC()
            p1.ParseFromString(entity.device_identity)        
            p2 = wa_struct_pb2.ADVSignedDeviceIdentity()
            p2.ParseFromString(p1.details)
            p3 = wa_struct_pb2.ADVDeviceIdentity()
            p3.ParseFromString(p2.details)        
            identity = self.getProp("reg_info")["identity"]
            buffer=b'\x06\x01'+p2.details+identity.publicKey.serialize()[1:]+p2.account_signature_key            
            devicesign = Curve.calculateSignature(identity.privateKey,buffer)
            p4 = wa_struct_pb2.ADVSignedDeviceIdentity()            
            p4.account_signature = p2.account_signature
            p4.details = p2.details
            p4.device_signature = devicesign
            signEntity = MultiDevicePairSignIqProtocolEntity(entity.getId(),p3.key_index,p4.SerializeToString())       
            self._sendIq(signEntity)                 
            self.genProfile(p4) 
            return 
    
        if isinstance(entity,ResultSetPictureIqProtocolEntity):             
            self.setCmdResult(entity.getId(),{"pictureId":entity.getPictureId()})
            return
        
        if isinstance(entity, EmailResultIqProtocolEntity):
            # EmailResultIqProtocolEntity já é tratado nos callbacks dos métodos específicos
            # Mas também pode ser recebido diretamente aqui, então tratamos
            result = {
                "email": entity.emailAddress,
                "verified": entity.verified,
                "confirmed": entity.confirmed,
                "do_verify": entity.doVerify
            }
            self.setCmdResult(entity.getId(), result)
            return
        
        if isinstance(entity, VerifyEmailResultIqProtocolEntity):
            # VerifyEmailResultIqProtocolEntity já é tratado nos callbacks dos métodos específicos
            result = {
                "status": "ok",
                "email": entity.emailAddress if hasattr(entity, 'emailAddress') else None
            }
            self.setCmdResult(entity.getId(), result)
            return 
                            
    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        logger.info("Login Fail")     

        logger.info(f"Login Fail: {entity}")
        reason = entity.reason if hasattr(entity, 'reason') else str(entity)
        
        # Verifica se é erro de handshake (pode aparecer como "handshake" ou outros códigos)
        is_handshake_error = (
            "handshake" in reason.lower() or 
            reason in ["handshake_failed", "HandshakeFailedException"] or
            (hasattr(entity, 'reason') and entity.reason and "handshake" in str(entity.reason).lower())
        )
        
        if is_handshake_error:
            logger.error(f"Erro de handshake detectado: {reason}")
            self._handshake_error_detected = True
            
            # Chama callback se configurado
            if self.handshake_failed_callback:
                try:
                    self.handshake_failed_callback(reason=reason, bot_id=self.bot.botId)
                except Exception as e:
                    logger.error(f"Erro ao chamar callback de handshake failed: {e}")
        
        if reason=="403" or reason=="401" or reason=="405" or reason=="404":
            self.eventCallback(wsend_pb2.BotEvent.Event.LOGIN_FAIL,eventDetail=reason)
            self.detect40x = True            

            # Atualiza status da conta no banco de dados - marca como não logada e com restrição
            if self.bot.botId is not None:
                from zowsuplib.app.db import update_account_status
                update_account_status(self.bot.botId, is_logged_in=False, has_restriction=True)

            if reason!="405" and self.bot.bot_type!=YowBotType.TYPE_RUN_TEMP:
                pass                

            # Se primeira tentativa retornar 403, sinaliza rotação (handled por camada superior)
            if reason == "403" and not self._handshake_error_detected:
                logger.info(f"403 no primeiro login: {reason}")
                # logger.info("403 no primeiro login: sinalizando rotação de handshake/profile")
                # self.setProp("refs", None)
                # self.setProp("jid", None)
                # self.setProp("reg_info", None)
                # self._handshake_error_detected = True
                # if self.handshake_failed_callback:
                #     try:
                #         self.handshake_failed_callback(reason="403_first_login", bot_id=self.bot.botId)
                #     except Exception as e:
                #         logger.error(f"Erro ao chamar callback de rotação após 403: {e}")

            self._login_failed = True
            self.isConnected = False
            self.loginEvent.set()

    def eventCallback(self,event,eventDetail=None,msgLog=None,contactUpdate=None):        
        if self.bot.callback is not None and self.bot.botId is not None:
            
            e = wsend_pb2.BotEvent()            
            e.bot_id = self.bot.botId
            e.event = event
            if eventDetail is not None:
                e.event_detail = eventDetail

            if msgLog is not None:                
                e.msg_log.msg_id = msgLog["msgId"]
                if "taskId" in msgLog and msgLog["taskId"] is not None:
                    e.msg_log.task_id = msgLog["taskId"] 
                if "sender" in msgLog and msgLog["sender"] is not None:
                    e.msg_log.sender = msgLog["sender"]
                if "status" in msgLog and msgLog["status"] is not None:
                    e.msg_log.status = msgLog["status"] 
                if "target" in msgLog and msgLog["target"] is not None:
                    e.msg_log.target = msgLog["target"] 
                if "errorCode" in msgLog and msgLog["errorCode"] is not None:
                    e.msg_log.error_code = msgLog["errorCode"]
                if "content" in msgLog and msgLog["content"] is not None:
                    e.msg_log.content = msgLog["content"]  

            if contactUpdate is not None:
                if "target" in contactUpdate and contactUpdate["target"] is not None:
                    e.contact_update.target = contactUpdate["target"]
                if "key" in contactUpdate and contactUpdate["key"] is not None:
                    e.contact_update.key = contactUpdate["key"]
                if "value" in contactUpdate and contactUpdate["value"] is not None:
                    e.contact_update.value = contactUpdate["value"]

            e.timestamp = int(time.time())
            self.bot.callback(event = e,logger =logger,caller=self.bot)


    def setMessageCallback(self, callback):
        """
        Define um callback customizado para mensagens recebidas.
        
        O callback será chamado com os seguintes argumentos:
        - message: objeto wsend_pb2.Message com os dados da mensagem
        - logger: logger para uso no callback
        - caller: referência ao bot
        
        Args:
            callback: Função ou método que será chamado quando uma mensagem for recebida.
                     Se None, remove o callback customizado.
        """
        self.message_callback = callback
        logger.info(f"Message callback {'configurado' if callback is not None else 'removido'} no SendLayer")

    def disableMessageNotifications(self):
        """Desativa a entrega de callbacks de mensagem (silencia notificações)."""
        self._message_notifications_enabled = False
        logger.info("Notificações de mensagem desativadas no SendLayer")

    def enableMessageNotifications(self):
        """Reativa a entrega de callbacks de mensagem."""
        self._message_notifications_enabled = True
        logger.info("Notificações de mensagem reativadas no SendLayer")
    
    def _get_default_important_notifications(self):
        """
        Retorna conjunto de tipos de notificações importantes por padrão.
        Essas notificações sempre serão processadas, mesmo com filtro ativo.
        """
        return {
            'AccountSyncNotificationProtocolEntity',
            'LinkCodeCompanionRegNotificationProtocolEntity',
            'CreateGroupsNotificationProtocolEntity',
            'AddGroupsNotificationProtocolEntity',
            'RemoveGroupsNotificationProtocolEntity',
            'SetPictureNotificationProtocolEntity',
            'DeletePictureNotificationProtocolEntity',
            'BusinessNameUpdateNotificationProtocolEntity',
            'BusinessRemoveNotificationProtocolEntity',
            'DisapperingModeNotificationProtocolEntity',
            'DeviceLogoutNotificationProtocolEntity',
            'StatusNotificationProtocolEntity',  # Status pode ser importante para alguns bots
        }
    
    def _get_default_ignored_notifications(self):
        """
        Retorna conjunto de tipos de notificações que podem ser ignoradas por padrão.
        Essas notificações serão descartadas se o filtro estiver ativo.
        """
        return {
            'MexUpdateNotificationProtocolEntity',  # Atualizações mex (geralmente não importantes)
            'WaOldCodeNotificationProtocolEntity',  # Código antigo de registro
        }
    
    def _is_notification_important(self, entity) -> bool:
        """
        Verifica se uma notificação é importante e deve ser processada.
        
        Args:
            entity: Entidade de notificação
            
        Returns:
            True se a notificação deve ser processada, False caso contrário
        """
        if not self._notification_filter_enabled:
            return True  # Se filtro desativado, processa tudo
        
        # Obtém o nome da classe da entidade
        entity_type = type(entity).__name__
        
        # Verifica se está na lista de importantes
        if entity_type in self._important_notification_types:
            return True
        
        # Verifica se está na lista de ignoradas
        if entity_type in self._ignored_notification_types:
            return False
        
        # Por padrão, se não está em nenhuma lista, processa (comportamento conservador)
        # Isso permite que novas notificações sejam processadas até serem explicitamente ignoradas
        return True
    
    def enable_notification_filter(self):
        """
        Ativa o sistema de filtragem de notificações.
        Apenas notificações importantes serão processadas.
        """
        self._notification_filter_enabled = True
        logger.info(f"[{self.bot.botId}] Filtro de notificações ativado")
    
    def disable_notification_filter(self):
        """
        Desativa o sistema de filtragem de notificações.
        Todas as notificações serão processadas.
        """
        self._notification_filter_enabled = False
        logger.info(f"[{self.bot.botId}] Filtro de notificações desativado")
    
    def add_important_notification_type(self, notification_type: str):
        """
        Adiciona um tipo de notificação à lista de importantes.
        
        Args:
            notification_type: Nome da classe da notificação (ex: 'MexUpdateNotificationProtocolEntity')
        """
        self._important_notification_types.add(notification_type)
        logger.debug(f"[{self.bot.botId}] Tipo de notificação adicionado como importante: {notification_type}")
    
    def remove_important_notification_type(self, notification_type: str):
        """
        Remove um tipo de notificação da lista de importantes.
        
        Args:
            notification_type: Nome da classe da notificação
        """
        self._important_notification_types.discard(notification_type)
        logger.debug(f"[{self.bot.botId}] Tipo de notificação removido de importantes: {notification_type}")
    
    def add_ignored_notification_type(self, notification_type: str):
        """
        Adiciona um tipo de notificação à lista de ignoradas.
        
        Args:
            notification_type: Nome da classe da notificação
        """
        self._ignored_notification_types.add(notification_type)
        logger.debug(f"[{self.bot.botId}] Tipo de notificação adicionado como ignorado: {notification_type}")
    
    def remove_ignored_notification_type(self, notification_type: str):
        """
        Remove um tipo de notificação da lista de ignoradas.
        
        Args:
            notification_type: Nome da classe da notificação
        """
        self._ignored_notification_types.discard(notification_type)
        logger.debug(f"[{self.bot.botId}] Tipo de notificação removido de ignorados: {notification_type}")
    
    def get_notification_filter_status(self) -> dict:
        """
        Retorna status atual do filtro de notificações.
        
        Returns:
            Dict com informações sobre o filtro
        """
        return {
            'enabled': self._notification_filter_enabled,
            'important_types': sorted(self._important_notification_types),
            'ignored_types': sorted(self._ignored_notification_types),
        }
    
    def messageCallback(self,msg):
        #if msg.HasField("participant"):
            #group msg, ignore it
        #    return
        if not self._message_notifications_enabled:
            logger.debug("Notificação de mensagem ignorada (desativada)")
            return
        # Primeiro chama o callback customizado do SendLayer (se configurado)
        if self.message_callback is not None:
            msg.bot_id = self.bot.botId
            logger.debug(f"messageCallback chamado - callback customizado: {self.message_callback}, msg type: {msg.type if hasattr(msg, 'type') else 'unknown'}")
            try:
                self.message_callback(message=msg, logger=logger, caller=self.bot)
            except Exception as e:
                logger.error(f"Erro ao chamar callback customizado de mensagem: {e}", exc_info=True)
        
        # Depois chama o callback padrão do bot (se configurado)
        if self.bot.callback is not None:
            msg.bot_id = self.bot.botId
            logger.debug(f"messageCallback chamado - callback do bot: {self.bot.callback}, msg type: {msg.type if hasattr(msg, 'type') else 'unknown'}")
            try:
                self.bot.callback(message=msg,logger=logger,caller=self.bot)
            except Exception as e:
                logger.error(f"Erro ao chamar callback do bot: {e}", exc_info=True)

    @ProtocolEntityCallback("success")
    def onSuccess(self, successProtocolEntity):                  
        logger.info("Login OK")     
                            
        self.isConnected = True
        self._login_failed = False
        
        # Limpa flag de login em progresso antes de setar evento
        # (permite que notificações pendentes sejam processadas normalmente após login)
        notifications_during_login = self._pending_notifications_count
        self._login_in_progress = False
        
        # Seta evento de login (isso acorda waitLogin)
        self.loginEvent.set()
        
        if notifications_during_login > 0:
            logger.info(f"[{self.bot.botId}] Login concluído com {notifications_during_login} notificações processadas durante login")
        self._reconnect_attempts = 0
        self._cancel_reconnect_timer()
        entity = AvailablePresenceProtocolEntity()
        self.toLower(entity)                
   
        self.eventCallback(wsend_pb2.BotEvent.Event.LOGIN_SUCCESS)
        
        self.lastOnlineTimeStamp = int(time.time()) 

        # Atualiza status da conta no banco de dados
        if self.bot.botId is not None:
            from zowsuplib.app.db import update_account_status
            update_account_status(self.bot.botId, is_logged_in=True, has_restriction=False)

        self.setProp(PROP_IDENTITY_AUTOTRUST, True)
        

    @ProtocolEntityCallback("stream:error")
    def onStreamError(self, entity):
        logger.info("Stream Error")      
        print(entity)        

        if entity.code is not None :
            if entity.code=="503":
                self.detect503 = True      
                self.bot._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))                
        # Detecta conflito (sessão substituída)
        try:
            # Verifica se é um erro de tipo "conflict" usando getErrorType()
            if hasattr(entity, "getErrorType"):
                error_type = entity.getErrorType()
                if error_type == "conflict":
                    self._last_stream_conflict = True
                    logger.warning("Stream error: conflict detected (session replaced)")
            
            # Verifica atributos diretos
            if hasattr(entity, "reason") and entity.reason == "conflict":
                self._last_stream_conflict = True
            if hasattr(entity, "type") and entity.type == "replaced":
                self._last_stream_conflict = True
            # Alguns parsers deixam em atributos dict-like:
            if hasattr(entity, "type") and getattr(entity, "type", None) == "conflict":
                self._last_stream_conflict = True
            
            # Verifica nos dados do erro (para casos como <conflict type="replaced" />)
            if hasattr(entity, "getErrorData"):
                error_data = entity.getErrorData()
                if error_data and "conflict" in error_data:
                    self._last_stream_conflict = True
                    logger.warning("Stream error: conflict detected in error data")
        except Exception as e:
            logger.debug(f"Erro ao processar stream:error: {e}")
            pass
   
    @ProtocolEntityCallback("ack")
    def onAck(self, entity):               

        logger.info(f"onAck chamado: {entity}") 
        
        if entity.getId() in self.ackQueue:

            if entity._from is not None:
                num = entity._from[0:entity._from.rfind('@', 0)]                  

            if entity.getError() is None:
                    # Atualiza o status da mensagem para SENT no banco de dados
                    if self.bot.botId is not None:
                        from zowsuplib.app.db import register_sent_message
                        recipient_jid = Jid.normalize(entity._from) if entity._from else num
                        register_sent_message(
                            phone=self.bot.botId,
                            msg_id=entity.getId(),
                            recipient=recipient_jid,
                            status="SENT",
                        )
                    
                    self.eventCallback(wsend_pb2.BotEvent.Event.MSG_LOG,msgLog={
                            'msgId':entity.getId(),                                                 
                            'sender':self.bot.botId,
                            'target':num,
                            'status': wsend_pb2.MsgLogItem.Status.Value("SENT")
                    })
            else:
                    # Atualiza o status da mensagem para ERROR no banco de dados
                    if self.bot.botId is not None:
                        from zowsuplib.app.db import register_sent_message
                        recipient_jid = Jid.normalize(entity._from) if entity._from else num
                        register_sent_message(
                            phone=self.bot.botId,
                            msg_id=entity.getId(),
                            recipient=recipient_jid,
                            status="ERROR",
                            error_code=entity.getError(),
                        )
                
                    self.eventCallback(wsend_pb2.BotEvent.Event.MSG_LOG,msgLog={
                            'msgId':entity.getId(),                            
                            'sender':self.bot.botId,
                            'target':num,
                            'errorCode': entity.getError(),
                            'status': wsend_pb2.MsgLogItem.Status.Value("ERROR")
                    })                                    
            
                                
            self.ackQueue.pop(self.ackQueue.index(entity.getId()))   


               
    def download(self,params):
                    
        enc_data = requests.get(url=params["url"]).content

        if enc_data is None:            
            logger.error("Download failed")        
            return None
        
        filename = params["filename"]
        ext = None

        if params["type"]=="IMAGE":
            media_info = MediaCipher.INFO_IMAGE            
        elif params["type"]=="VIDEO":
            media_info = MediaCipher.INFO_VIDEO    
        elif params["type"]=="AUDIO":
            media_info = MediaCipher.INFO_AUDIO
        elif params["type"]=="DOCUMENT":
            media_info = MediaCipher.INFO_DOCUMENT
        elif params["type"]=="STICKER":
            media_info = MediaCipher.INFO_IMAGE
        else:
            logger.error("Unsupported type")
            return None  

        filedata = MediaCipher().decrypt(enc_data, params["media_key"], media_info)
        
        if filedata is None:
            logger.error("Decrypt failed")
            return None
        
        if params["mimetype"]=="application/was":
            ext = ".was"
        
        if ext is None:
            ext = mimetypes.guess_extension(params["mimetype"].split(";")[0])
                            
        try:
            download_dir = getattr(self.bot, "app_config", None).download_path if getattr(self.bot, "app_config", None) else Path("/data/download/")
            full_path = Path(download_dir) / f"{filename}{ext}"
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(filedata)
        except Exception as e:
            logger.error(e)
            return None
        
        return str(full_path)
    
    def parseMediaCommonAttributes(self,msg,media_specific_attributes):        
        if media_specific_attributes is not None:
            msg.url = media_specific_attributes.url
            msg.direct_path = media_specific_attributes.direct_path
            msg.file_enc_sha256 = media_specific_attributes.file_enc_sha256
            msg.media_key_timestamp = media_specific_attributes.media_key_timestamp
            msg.file_sha256 = media_specific_attributes.file_sha256
            msg.file_length = media_specific_attributes.file_length
            msg.mimetype = media_specific_attributes.mimetype
            msg.media_key = media_specific_attributes.media_key
    
    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):            
        logger.debug(f"[SendLayer] onMessage chamado - type: {messageProtocolEntity.getType()}, from: {messageProtocolEntity.getFrom(False) if hasattr(messageProtocolEntity, 'getFrom') else 'unknown'}")
           
        if messageProtocolEntity.getType() == 'text' :

            type = "text"
            if isinstance(messageProtocolEntity, TextMessageProtocolEntity):                                                            
                text = messageProtocolEntity.getBody()     
            if isinstance(messageProtocolEntity, ExtendedTextMessageProtocolEntity):                                           
                text = messageProtocolEntity.text          
                if messageProtocolEntity.context_info is not None and messageProtocolEntity.context_info.external_ad_reply is not None:
                    type="ad"

            msg = wsend_pb2.Message()                         
            msg.msg_id = messageProtocolEntity.getId()                            
            msg.target = messageProtocolEntity.getTo(False) if messageProtocolEntity.fromme else self.bot.botId
            msg.sender = messageProtocolEntity.getFromPn(False) or messageProtocolEntity.getFrom(False)
            msg.notify = messageProtocolEntity.getNotify()
            msg.timestamp = int(time.time())
            if messageProtocolEntity.getParticipant(False) :
                msg.participant = messageProtocolEntity.getParticipant(False) 

            if type=="text":
                msg.type = wsend_pb2.Message.Type.Value("TEXT")  
                msg.text_message.text = text                   

            if type=="ad":
                msg.type = wsend_pb2.Message.Type.Value("AD")
                msg.ad_message.text = text
                msg.ad_message.title = messageProtocolEntity.context_info.external_ad_reply.title
                msg.ad_message.thumbnail = messageProtocolEntity.context_info.external_ad_reply.thumbnail
                msg.ad_message.url = messageProtocolEntity.context_info.external_ad_reply.source_url
                msg.ad_message.larger_thumbnail = messageProtocolEntity.context_info.external_ad_reply.render_larger_thumbnail
            
            self.messageCallback(msg)
                
        elif messageProtocolEntity.getType() == 'media':  

            msg = wsend_pb2.Message()                                
            msg.msg_id = messageProtocolEntity.getId()                
            msg.target = messageProtocolEntity.getTo(False) if messageProtocolEntity.fromme else self.bot.botId
            msg.sender = messageProtocolEntity.getFrom(False)
            msg.notify = messageProtocolEntity.getNotify()
            if messageProtocolEntity.getParticipant(False) :
                msg.participant = messageProtocolEntity.getParticipant(False) 

            msg.timestamp = int(time.time())
            if isinstance(messageProtocolEntity,ExtendedTextMediaMessageProtocolEntity):        
       
                type="url"
                if messageProtocolEntity.media_specific_attributes.context_info is not None and messageProtocolEntity.media_specific_attributes.context_info.external_ad_reply is not None:
                    type="ad"

                msg = wsend_pb2.Message()                         
                msg.msg_id = messageProtocolEntity.getId()                            
                msg.target = messageProtocolEntity.getTo(False) if messageProtocolEntity.fromme else self.bot.botId
                msg.sender = messageProtocolEntity.getFrom(False)
                msg.notify = messageProtocolEntity.getNotify()
                msg.timestamp = int(time.time())
                if messageProtocolEntity.getParticipant(False) :
                    msg.participant = messageProtocolEntity.getParticipant(False) 

                if type=="ad":
                    msg.type = wsend_pb2.Message.Type.Value("AD")
                    msg.ad_message.text = messageProtocolEntity.text
                    msg.ad_message.title = messageProtocolEntity.media_specific_attributes.context_info.external_ad_reply.title
                    msg.ad_message.thumbnail = messageProtocolEntity.media_specific_attributes.context_info.external_ad_reply.thumbnail
                    msg.ad_message.url = messageProtocolEntity.media_specific_attributes.context_info.external_ad_reply.source_url
                    msg.ad_message.larger_thumbnail = messageProtocolEntity.media_specific_attributes.context_info.external_ad_reply.render_larger_thumbnail
                else :
                    msg.type = wsend_pb2.Message.Type.Value("URL")                
                    msg.url_message.text = messageProtocolEntity.text   
                    msg.url_message.url  = messageProtocolEntity.matched_text
                          
                self.messageCallback(msg)                
                
                                                   
            elif isinstance(messageProtocolEntity,ImageDownloadableMediaMessageProtocolEntity):
                text = "[image]"                      
                msg.type = wsend_pb2.Message.Type.Value("IMAGE") 
                self.parseMediaCommonAttributes(msg.image_message,messageProtocolEntity.downloadablemedia_specific_attributes)                                
                if  messageProtocolEntity.caption:
                    msg.image_message.caption = messageProtocolEntity.caption                                 
                if  messageProtocolEntity.jpeg_thumbnail:
                    msg.image_message.jpeg_thumbnail = messageProtocolEntity.jpeg_thumbnail
                msg.image_message.height = messageProtocolEntity.height
                msg.image_message.width  = messageProtocolEntity.width                                
                                                    
                self.messageCallback(msg)                             

            elif isinstance(messageProtocolEntity,VideoDownloadableMediaMessageProtocolEntity):
                text = "[video]"      
                msg.type = wsend_pb2.Message.Type.Value("VIDEO") 
                self.parseMediaCommonAttributes(msg.video_message,messageProtocolEntity.downloadablemedia_specific_attributes)                               
                if  messageProtocolEntity.caption:
                    msg.video_message.caption = messageProtocolEntity.caption 
                msg.video_message.height = messageProtocolEntity.height
                msg.video_message.width  = messageProtocolEntity.width
                msg.video_message.seconds= messageProtocolEntity.seconds
                msg.video_message.gif_playback = messageProtocolEntity.gif_playback
                msg.video_message.jpeg_thumbnail = messageProtocolEntity.jpeg_thumbnail
                self.messageCallback(msg)   

            elif isinstance(messageProtocolEntity,AudioDownloadableMediaMessageProtocolEntity):
                text = "[audio]"      
                msg.type = wsend_pb2.Message.Type.Value("AUDIO") 
                self.parseMediaCommonAttributes(msg.audio_message,messageProtocolEntity.downloadablemedia_specific_attributes)
                msg.audio_message.seconds= messageProtocolEntity.seconds
                msg.audio_message.ptt = messageProtocolEntity.ptt  

                logger.debug(f"[AudioDownloadableMediaMessageProtocolEntity] msg: {msg}")                                                       
                self.messageCallback(msg)     

            elif isinstance(messageProtocolEntity,DocumentDownloadableMediaMessageProtocolEntity):
                text = "[document]"
                msg.type = wsend_pb2.Message.Type.Value("DOCUMENT")        
                self.parseMediaCommonAttributes(msg.document_message,messageProtocolEntity.downloadablemedia_specific_attributes)                
                if  messageProtocolEntity.caption:
                    msg.document_message.caption = messageProtocolEntity.caption                 
                if messageProtocolEntity.title:
                    msg.document_message.title = messageProtocolEntity.title
                if messageProtocolEntity.page_count:
                    msg.document_message.page_count= messageProtocolEntity.page_count
                    msg.document_message.file_name = messageProtocolEntity.file_name

                self.messageCallback(msg)   

            elif  isinstance(messageProtocolEntity,StickerDownloadableMediaMessageProtocolEntity):
                text = "[sticker]"
                msg.type = wsend_pb2.Message.Type.Value("STICKER")     
                self.parseMediaCommonAttributes(msg.sticker_message,messageProtocolEntity.downloadablemedia_specific_attributes)                
                msg.sticker_message.height = messageProtocolEntity.height
                msg.sticker_message.width  = messageProtocolEntity.width                    
                msg.sticker_message.is_animated = messageProtocolEntity.is_animated                    
                msg.sticker_message.sticker_sent_ts = messageProtocolEntity.sticker_sent_ts
                msg.sticker_message.is_avatar = messageProtocolEntity.is_avatar
                msg.sticker_message.is_ai_sticker = messageProtocolEntity.is_ai_sticker
                msg.sticker_message.is_lottie = messageProtocolEntity.is_lottie
                self.messageCallback(msg)   
            else:          
                text = "[media]" 
                msg.type = wsend_pb2.Message.Type.Value("OTHER") 
                self.messageCallback(msg)
                                      
        self.toLower(messageProtocolEntity.ack())
        self.toLower(messageProtocolEntity.ack(True))
                                  
    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):

        if entity.getParticipant() is not None:
            _from = entity.getFrom(False)+"::"+entity.getParticipant(False)
        else:
            _from = entity.getFrom(False)
            
        #群发模式，有待跟踪的消息id                          
        if entity.getType() == "read":
            self.eventCallback(wsend_pb2.BotEvent.Event.MSG_LOG,msgLog={
                'msgId':entity.getId(),
                'sender':self.bot.botId,
                'target':_from,
                'status': wsend_pb2.MsgLogItem.Status.Value("READ")                

            })                                             
        else:
            self.eventCallback(wsend_pb2.BotEvent.Event.MSG_LOG,msgLog={
                'msgId':entity.getId(),                
                'sender':self.bot.botId,
                'target':_from,                          
                'status': wsend_pb2.MsgLogItem.Status.Value("RECEIVED")
            }) 

        self.toLower(entity.ack())        

    # Mantido atributo booleano self.isConnected para status de conexão.
    # Método removido para evitar recursão e confusão com o atributo.
                      
    def waitLogin(self):
        #等待bot连接就绪,
        #超时返回false，正常登录返回true
        logged = self.loginEvent.wait(20)
        return logged and (not self._login_failed) and self.isConnected
    
    def multiSend(self,cmdParams,options):
        tos, *other = cmdParams
        toArr = tos.split(",")
        if len(toArr)==0:
            logger.info("No target to send")
            return False

        repeat = int(Utils.getOption(options,"repeat",1))
        execCount = 0
        for i in range(0,repeat):
            for to in toArr:            
                params = [to]
                params.extend(cmdParams[1:])
                self.sendMsg(params,options)
                execCount+= 1
                time.sleep(1)
                            
        return "JUSTWAIT"
    
    def _check_account_restriction(self):
        """
        Verifica se a conta tem restrições antes de enviar mensagem.
        
        Returns:
            True se a conta está restrita, False caso contrário
        """
        if self.bot.botId is None:
            return False
        
        try:
            from zowsuplib.app.db import SessionLocal
            from zowsuplib.app import models
            
            db = SessionLocal()
            try:
                has_restriction = (
                    db.query(models.Account.has_restriction)
                    .filter_by(phone=self.bot.botId)
                    .scalar()
                )
                if has_restriction:
                    logger.warning(f"Conta {self.bot.botId} está com restrição, não é possível enviar mensagens")
                    return True
                return False
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Erro ao verificar restrições da conta: {e}")
            return False
    
    def _is_number_invalid(self, phone_number):
        """
        Verifica se um número está na lista de números inválidos.
        
        Args:
            phone_number: Número de telefone
        
        Returns:
            True se o número é inválido, False caso contrário
        """
        # Remove @s.whatsapp.net se presente
        phone = phone_number.split('@')[0] if '@' in phone_number else phone_number
        return phone in self._invalid_numbers
    
    def _mark_number_invalid(self, phone_number):
        """
        Marca um número como inválido.
        
        Args:
            phone_number: Número de telefone
        """
        phone = phone_number.split('@')[0] if '@' in phone_number else phone_number
        self._invalid_numbers.add(phone)
        logger.warning(f"Número {phone} marcado como inválido")
    
    def _validate_contact_sync_result(self, sync_result, requested_jid):
        """
        Valida o resultado da sincronização de contato.
        
        Args:
            sync_result: Resultado da sincronização (ResultSyncIqProtocolEntity)
            requested_jid: JID que foi solicitado para sincronizar
        
        Returns:
            Tuple (is_valid, jid_found, phone_number)
            - is_valid: True se o número é válido no WhatsApp
            - jid_found: JID encontrado (pode ser diferente do solicitado)
            - phone_number: Número de telefone extraído
        """
        if not sync_result or not hasattr(sync_result, 'inNumbers'):
            return False, None, None
        
        # Extrai o número do JID solicitado
        phone = requested_jid.split('@')[0] if '@' in requested_jid else requested_jid
        
        # Verifica se está na lista de números inválidos (prioridade)
        invalid_users = getattr(sync_result, 'invalidUsers', [])
        if phone in invalid_users:
            logger.warning(f"Número {phone} está na lista de inválidos do WhatsApp")
            return False, None, phone
        
        # Verifica se está em inNumbers (números válidos que têm você nos contatos)
        if phone in sync_result.inNumbers:
            jid_found = sync_result.inNumbers[phone]
            logger.info(f"Número {phone} válido (inNumbers), JID: {jid_found}")
            return True, jid_found, phone
        
        # Verifica se está em outNumbers (números válidos que você tem nos contatos)
        if phone in sync_result.outNumbers:
            jid_found = sync_result.outNumbers[phone]
            logger.info(f"Número {phone} válido (outNumbers), JID: {jid_found}")
            return True, jid_found, phone
        
        # Se não está em nenhum, pode ser inválido
        logger.warning(f"Número {phone} não encontrado em inNumbers nem outNumbers - pode ser inválido")
        return False, None, phone
    
    def _human_like_delay(self, base_delay=2.0, variation=1.0):
        """
        Gera um delay que simula comportamento humano (variável e natural).
        
        Args:
            base_delay: Delay base em segundos
            variation: Variação máxima em segundos
        
        Returns:
            Delay aleatório entre base_delay e base_delay + variation
        """
        delay = base_delay + random.uniform(0, variation)
        return delay
    
    def assureContactsAndSend(self,cmdParams,options,send_func,redo_func):        
        """
        Garante que o contato está sincronizado antes de enviar mensagem.
        Implementa estratégia anti-banimento com validações robustas.
        
        Args:
            cmdParams: Parâmetros do comando [to, message, ...]
            options: Opções do comando
            send_func: Função para enviar mensagem
            redo_func: Função para reenviar após sincronização
        
        Returns:
            False se contato já existe, None se está sincronizando
        """
        if not cmdParams or len(cmdParams) < 1:
            logger.error("assureContactsAndSend: parâmetros insuficientes")
            return False
        
        to = cmdParams[0]
        if not to:
            logger.error("assureContactsAndSend: 'to' vazio")
            return False

        try:
            # 1. Verifica se a conta está restrita
            if self._check_account_restriction():
                logger.error(f"Não é possível enviar: conta {self.bot.botId} está com restrição")
                raise RuntimeError(f"Conta {self.bot.botId} está com restrição")
            
            isCompanion = "_" in self.bot.botId if self.bot.botId else False
            jid = Jid.normalize(to)
            
            if not jid:
                logger.error(f"assureContactsAndSend: falha ao normalizar JID: {to}")
                raise ValueError(f"JID inválido: {to}")
            
            # 3. Verifica se o número está na lista de inválidos
            phone = jid.split('@')[0] if '@' in jid else jid
            if self._is_number_invalid(phone):
                logger.warning(f"Número {phone} está na lista de inválidos, não tentando enviar")
                raise ValueError(f"Número {phone} é inválido no WhatsApp")

            isNewContact = self.db._store.isNewContact(jid)
            if isNewContact and not isCompanion:
                logger.info(f"Contato {jid} é novo, sincronizando e validando antes de enviar...")
                
                # 4. Verifica se já sincronizou recentemente (evita sincronizações muito frequentes)
                last_sync = self._last_sync_time.get(jid, 0)
                current_time = time.time()
                min_sync_interval = 30  # Mínimo 30 segundos entre sincronizações do mesmo número
                
                if last_sync > 0 and (current_time - last_sync) < min_sync_interval:
                    wait_time = min_sync_interval - (current_time - last_sync)
                    logger.info(f"Aguardando {wait_time:.1f}s antes de sincronizar novamente {jid}")
                    time.sleep(wait_time)
                
                self.db._store.addContact(jid)
                entity = GetSyncIqProtocolEntity([phone], mode="delta")

                logger.debug(f"GetSyncIqProtocolEntity: {entity}")
                
                # Usa uma lista para armazenar o JID atualizado (permite modificação dentro da closure)
                jid_container = [jid]
                
                def on_success(entity, original_iq_entity):
                    # Valida o resultado da sincronização usando o JID original
                    is_valid, jid_found, phone_num = self._validate_contact_sync_result(entity, jid_container[0])
                    
                    if not is_valid:
                        logger.error(f"Número {phone_num} não é válido no WhatsApp (não encontrado na sincronização)")
                        self._mark_number_invalid(phone_num)
                        # Remove o contato que foi adicionado antes da sincronização se for inválido
                        try:
                            if hasattr(self.db._store, 'removeContact'):
                                self.db._store.removeContact(jid_container[0])
                                logger.debug(f"Contato inválido {jid_container[0]} removido do banco")
                        except Exception as e:
                            logger.warning(f"Erro ao remover contato inválido: {e}")
                        # Não tenta enviar para número inválido
                        return
                    
                    # Atualiza o JID se encontrou um diferente
                    current_jid = jid_container[0]
                    original_jid = current_jid
                    
                    if jid_found and jid_found != current_jid:
                        logger.info(f"JID atualizado: {current_jid} -> {jid_found}")
                        jid_container[0] = jid_found
                        # Atualiza cmdParams com o JID correto
                        cmdParams[0] = jid_found.split('@')[0] if '@' in jid_found else jid_found
                        current_jid = jid_found
                        
                        # Se o JID mudou, remove o antigo e adiciona o novo
                        try:
                            if hasattr(self.db._store, 'removeContact'):
                                self.db._store.removeContact(original_jid)
                                logger.debug(f"Contato antigo {original_jid} removido do banco")
                        except Exception as e:
                            logger.warning(f"Erro ao remover contato antigo: {e}")
                    
                    # O contato já foi salvo pelo syncContacts, mas garante que está com o JID correto
                    # (syncContacts salva todos os contatos válidos automaticamente)
                    logger.info(f"Contato {current_jid} sincronizado e validado com sucesso (já salvo pelo syncContacts)")
                    
                    # Aguarda delay human-like antes de confiar
                    trust_delay = self._human_like_delay(base_delay=2.0, variation=1.5)
                    logger.debug(f"Aguardando {trust_delay:.1f}s antes de confiar no contato...")
                    time.sleep(trust_delay)
                    
                    # Confia no contato
                    trust_entity = TrustContactIqProtocolEntity(current_jid, int(time.time()))
                    self.toLower(trust_entity)
                    
                    # Aguarda mais um pouco antes de enviar (comportamento humano)
                    send_delay = self._human_like_delay(base_delay=3.0, variation=2.0)
                    logger.debug(f"Aguardando {send_delay:.1f}s antes de enviar mensagem...")
                    time.sleep(send_delay)
                    
                    # Atualiza timestamp da última sincronização
                    self._last_sync_time[current_jid] = time.time()
                    
                    # Reenvia a mensagem
                    redo_func(cmdParams, options)
                
                def on_error(entity, original_iq):
                    logger.error(f"Erro ao sincronizar contato {jid_container[0]}")
                    # Marca como inválido se erro persistente
                    error_code = getattr(entity, 'code', None)
                    if error_code in ['404', '406']:  # Códigos comuns para número inválido
                        logger.warning(f"Erro {error_code} ao sincronizar {phone}, marcando como inválido")
                        self._mark_number_invalid(phone)
                    # Não tenta enviar para número que falhou na sincronização

                self._last_sync_time[jid] = time.time()
                self._sendIq(entity, on_success, on_error)
                return None  # Indica que está em processo de sincronização
            else:
                logger.debug(f"Contato {jid} já existe nos contatos")
                send_func(cmdParams, options)
                return False
                
        except (ValueError, RuntimeError) as e:
            logger.error(f"Erro em assureContactsAndSend: {e}")
            raise  # Re-lança exceções críticas
        except Exception as e:
            logger.error(f"Erro inesperado em assureContactsAndSend: {e}", exc_info=True)
            # Em caso de erro inesperado, não tenta enviar (mais seguro)
            return False    
        
    def sendMsgDirect(self,cmdParams,options):
        """
        Envia mensagem de texto de forma robusta e consistente.
        
        Args:
            cmdParams: Lista com [to, message, ...]
            options: Dict com opções adicionais
        
        Returns:
            message_id da mensagem enviada
        
        Raises:
            ValueError: Se parâmetros inválidos
            RuntimeError: Se não estiver conectado ou erro ao enviar
        """
        # Validação de parâmetros
        if not cmdParams or len(cmdParams) < 2:
            raise ValueError("sendMsgDirect requer pelo menos 2 parâmetros: [to, message]")
        
        to = cmdParams[0]
        message = cmdParams[1]
        
        # Validação de entrada
        if not to or not isinstance(to, str):
            raise ValueError(f"Parâmetro 'to' inválido: {to}")
        
        if not message or not isinstance(message, str):
            raise ValueError(f"Parâmetro 'message' inválido: {message}")
        
        # Validação de tamanho da mensagem (WhatsApp limita a ~4096 caracteres)
        MAX_MESSAGE_LENGTH = 4096
        if len(message) > MAX_MESSAGE_LENGTH:
            logger.warning(f"Mensagem muito longa ({len(message)} chars), truncando para {MAX_MESSAGE_LENGTH}")
            message = message[:MAX_MESSAGE_LENGTH]
        
        # Verifica se está conectado
        if not self.isConnected:
            error_msg = f"Não é possível enviar mensagem: conta não está conectada (botId={self.bot.botId})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Verifica se a conta está restrita (anti-banimento)
        if self._check_account_restriction():
            error_msg = f"Conta {self.bot.botId} está com restrição, não é possível enviar mensagens"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            # Normaliza o JID do destinatário
            normalized_to = Jid.normalize(to)
            if not normalized_to:
                raise ValueError(f"Falha ao normalizar JID: {to}")
            
            # Verifica se o número está na lista de inválidos
            phone = normalized_to.split('@')[0] if '@' in normalized_to else normalized_to
            if self._is_number_invalid(phone):
                error_msg = f"Número {phone} é inválido no WhatsApp (marcado como inválido anteriormente)"
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            logger.debug(f"Enviando mensagem para {normalized_to} (original: {to})")
            
            # Prepara context_info
            context_info = self._prepare_context_info(options)
            
            # Cria atributos da mensagem baseado nas opções
            attr = self._create_text_attributes(message, context_info, options)
            
            # Cria entidade da mensagem
            messageEntity = ExtendedTextMessageProtocolEntity(
                attr, 
                MessageMetaAttributes(
                    id=self.bot.idType,
                    recipient=normalized_to,
                    timestamp=int(time.time())
                )            
            )
            
            msg_id = messageEntity.getId()
            logger.info(f"Preparando envio de mensagem (ID={msg_id}) para {normalized_to}")
            
            # Adiciona à fila de ACK
            self.ackQueue.append(msg_id)
            
            # Envia mensagem baseado no tipo
            if "broadcast" in options:
                self._send_broadcast_message(messageEntity, options)
            else:
                self._send_regular_message(messageEntity, normalized_to, to, options)
            
            # Registra no banco de dados
            self._register_sent_message(msg_id, normalized_to, "TEXT", "EXECUTED")
            
            # Notifica evento
            self._notify_message_sent(msg_id, normalized_to, to)
            
            # Se waitMsgId está configurado, sinaliza o evento
            if "waitMsgId" in options and "ctxId" in options:
                ctx_id = options["ctxId"]
                if ctx_id in self.ctxMap:
                    self.ctxMap[ctx_id]["msgId"] = msg_id
                    self.ctxMap[ctx_id]["event"].set()
            
            logger.info(f"Mensagem enviada com sucesso (ID={msg_id}) para {normalized_to}")
            return msg_id
            
        except Exception as e:
            logger.exception(e)
            error_msg = f"Erro ao enviar mensagem para {to}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Tenta registrar erro no banco de dados
            try:
                normalized_to = Jid.normalize(to) if to else None
                if normalized_to and self.bot.botId:
                    from zowsuplib.app.db import register_sent_message
                    register_sent_message(
                        phone=self.bot.botId,
                        msg_id=None,
                        recipient=normalized_to,
                        message_type="TEXT",
                        status="ERROR",
                        error_code=str(e)
                    )
            except:
                pass
            
            raise RuntimeError(error_msg) from e
    
    def _prepare_context_info(self, options):
        """Prepara ContextInfoAttributes baseado nas opções."""
        context_info = ContextInfoAttributes()

        # Configura reply/quote se fornecido
        if "reply" in options or "reply_to" in options:
            reply_to = options.get("reply") or options.get("reply_to")
            if isinstance(reply_to, str):
                # Se for apenas uma string, assume que é o message_id
                context_info.stanza_id = reply_to
            elif isinstance(reply_to, dict):
                # Se for um dict, pode ter message_id, participant, etc.
                context_info.stanza_id = reply_to.get("message_id") or reply_to.get("id")
                context_info.participant = reply_to.get("participant")
                context_info.remote_jid = reply_to.get("remote_jid")
        
        # Configura disappearing mode
        if "disappearing" in options:
            try:
                disappearing_days = int(options["disappearing"])
                context_info.expiration = disappearing_days * 86400
                context_info.ephemeral_setting_timestamp = int(time.time())
                context_info.disappearing_mode = DisappearingModeAttributes(
                    initiator=DisappearingModeAttributes.INITIATOR_CHANGED_IN_CHAT,
                    trigger=DisappearingModeAttributes.TRIGGER_CHAT_SETTING,
                    initiatedByMe=True
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Valor inválido para 'disappearing': {options.get('disappearing')}, usando padrão")
                context_info.expiration = 0
        else:
            context_info.expiration = 0
            context_info.ephemeral_setting_timestamp = int(time.time())
            context_info.disappearing_mode = DisappearingModeAttributes(
                initiator=DisappearingModeAttributes.INITIATOR_CHANGED_IN_CHAT,
                trigger=DisappearingModeAttributes.TRIGGER_UNKNOWN,
                initiatedByMe=None
            )

        # Configura source tracking
        if "source" in options:
            if options["source"] == "random":
                srcs = ["contact_card", "contact_search", "global_search_new_chat", "phone_number_hyperlink"]
                source = random.choice(srcs)
            else:
                source = options["source"]

            context_info.entry_point_conversion_app = "whatsapp"
            context_info.entry_point_conversion_source = source
            context_info.entry_point_conversion_delay_seconds = random.randint(5, 13)

        return context_info
    
    def _create_text_attributes(self, message, context_info, options):
        """Cria ExtendedTextAttributes baseado nas opções."""
        if "url" in options:
            url = options["url"]                    
            urlTitle = options.get("urltitle")
            urlDesc = options.get("urldesc")
            
            return ExtendedTextAttributes(
                text=message,
                matched_text=url,
                description=urlDesc,
                title=urlTitle,
                context_info=context_info
            )     
        elif "bjid" in options:
            context_info.forwarding_score = 2
            context_info.is_forwarded = True
            context_info.business_message_forward_info = BusinessMessageForwardInfoAttributes(
                        business_owner_jid=Jid.normalize(options["bjid"])
                    )              
            
            return ExtendedTextAttributes(
                text=message,
                preview_type=0,
                context_info=context_info,
                invite_link_group_type_v2=0
            )   
        else:
            # Suporta opções de status (text_color, background_color, font)
            # Compatível com o padrão whatsmeow para envio de status
            text_argb = options.get("text_color") or options.get("text_argb")
            background_argb = options.get("background_color") or options.get("background_argb")
            font = options.get("font")
            preview_type = options.get("preview_type", 0)
            invite_link_group_type_v2 = options.get("invite_link_group_type_v2", 0)
            
            return ExtendedTextAttributes(
                text=message,
                preview_type=preview_type,
                context_info=context_info,
                invite_link_group_type_v2=invite_link_group_type_v2,
                text_argb=text_argb,
                background_argb=background_argb,
                font=font
            )            

    def _send_broadcast_message(self, messageEntity, options):
        """Envia mensagem em modo broadcast."""
        if "bcid" not in options or "phash" not in options:
            raise ValueError("Opções 'bcid' e 'phash' são obrigatórias para broadcast")
        
        logger.info(f"Enviando mensagem broadcast (ID={messageEntity.getId()})")
        messageEntity.to = options["bcid"]
        messageEntity.phash = options["phash"]
        self.toLower(messageEntity)
    
    def _send_regular_message(self, messageEntity, normalized_to, original_to, options):
        """Envia mensagem regular (não broadcast) com delays human-like."""
        logger.info(f"Enviando mensagem regular (ID={messageEntity.getId()}) para {normalized_to}")
        
        # Envia indicador de digitação antes da mensagem (apenas para contatos individuais)
        target = Jid.normalize(original_to.split(",")[0])
        is_group = target.endswith("@g.us")
        
        try:
            if is_group:
                # Grupo: inclui o próprio JID como participante
                typing_entity = OutgoingChatstateProtocolEntity(
                    ChatstateProtocolEntity.STATE_TYPING,
                    target,
                    Jid.normalize(self.bot.botId)
                )
            else:
                # Contato individual
                typing_entity = OutgoingChatstateProtocolEntity(
                    ChatstateProtocolEntity.STATE_TYPING,
                    target
                )
            
            self.toLower(typing_entity)
            
            # Aguarda delay human-like antes de enviar (simula digitação natural)
            # Para grupos, delay menor; para contatos individuais, delay maior
            typing_delay = options.get("typing_delay", self._human_like_delay(base_delay=.5, variation=1))
            
            if typing_delay > 0:
                max_delay = 0.5 if is_group else 1.0  # Limite máximo por tipo
                actual_delay = min(typing_delay, max_delay)
                logger.debug(f"Aguardando {actual_delay:.1f}s (typing delay) antes de enviar...")
                # time.sleep(actual_delay)
            
        except Exception as e:
            logger.warning(f"Erro ao enviar indicador de digitação: {e}, continuando...")
        
        # Envia a mensagem
        self.toLower(messageEntity)
            
    def _register_sent_message(self, msg_id, recipient_jid, message_type, status, error_code=None):
        """Registra mensagem enviada no banco de dados."""
        if self.bot.botId is None:
            return
        
        try:
            from zowsuplib.app.db import register_sent_message
            register_sent_message(
                phone=self.bot.botId,
                msg_id=msg_id,
                recipient=recipient_jid,
                message_type=message_type,
                status=status,
                error_code=error_code
            )
        except Exception as e:
            logger.warning(f"Erro ao registrar mensagem no banco de dados: {e}")
    
    def _notify_message_sent(self, msg_id, normalized_to, original_to):
        """Notifica evento de mensagem enviada."""
        try:
            # Extrai o número do JID para o target
            self.eventCallback(wsend_pb2.BotEvent.Event.MSG_LOG, msgLog={
                'msgId': msg_id,
                'sender': self.bot.botId,
                'target':  original_to[0:Jid.normalize(original_to).rfind("@",0)],
                'status': wsend_pb2.MsgLogItem.Status.Value("EXECUTED")                
                })      

        except Exception as e:
            logger.warning(f"Erro ao notificar evento de mensagem: {e}")        
    
    def getContextValue(self,ctxId,key):
        if ctxId not in self.ctxMap:
            return None        
        if key not in self.ctxMap[ctxId]:
            return None        
        return self.ctxMap[ctxId][key]
    
    def sendMsg(self,cmdParams,options):        

        if "broadcast" in options:
            bcid,phash = self.db._store.addBroadcast(jids = cmdParams[0],senderJid=self.bot.botId)
            options["bcid"] = bcid
            options["phash"] = phash            

        if "waitMsgId" not in options:
            self.assureContactsAndSend(cmdParams,options,send_func=self.sendMsgDirect,redo_func=self.sendMsg)            
            return "JUSTWAIT"
        else:
            ctxId = str(uuid.uuid4())            
            self.ctxMap[ctxId] = {"event":threading.Event()}
            options["ctxId"] = ctxId                                    
            self.assureContactsAndSend(cmdParams,options,send_func=self.sendMsgDirect,redo_func=self.sendMsg)            
            #等待消息ID的返回
            ret = self.ctxMap[ctxId]["event"].wait(int(options["waitMsgId"]))
            if not ret:
                return "TIMEOUT"
            else:
                msgId = self.getContextValue(ctxId,"msgId")
                del self.ctxMap[ctxId]
                return msgId

    def sendMessageReaction(self, cmdParams, options):
        """
        Envia uma reação (emoji) para uma mensagem de forma robusta e consistente.
        
        Args:
            cmdParams: Lista com [to, message_id, emoji] ou [to, message_id, emoji, participant]
            options: Dict com opções adicionais
        
        Returns:
            message_id da reação enviada
        
        Raises:
            ValueError: Se parâmetros inválidos
            RuntimeError: Se não estiver conectado ou erro ao enviar
        """
        # Validação de parâmetros
        if not cmdParams or len(cmdParams) < 3:
            raise ValueError("sendMessageReaction requer pelo menos 3 parâmetros: [to, message_id, emoji]")
        
        to = cmdParams[0]
        message_id = cmdParams[1]
        emoji = cmdParams[2]
        participant = cmdParams[3] if len(cmdParams) > 3 else None



        logger.info(f"sendMessageReaction: {cmdParams}, {options}")
        
        # Validação de entrada
        if not to or not isinstance(to, str):
            raise ValueError(f"Parâmetro 'to' inválido: {to}")
        
        if not message_id or not isinstance(message_id, str):
            raise ValueError(f"Parâmetro 'message_id' inválido: {message_id}")
        
        if not emoji or not isinstance(emoji, str):
            raise ValueError(f"Parâmetro 'emoji' inválido: {emoji}")
        
        # Verifica se está conectado
        if not self.isConnected:
            error_msg = f"Não é possível enviar reação: conta não está conectada (botId={self.bot.botId})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Verifica se a conta está restrita (anti-banimento)
        if self._check_account_restriction():
            error_msg = f"Conta {self.bot.botId} está com restrição, não é possível enviar reações"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            # Normaliza o JID do destinatário
            normalized_to = Jid.normalize(to)
            if not normalized_to:
                raise ValueError(f"Falha ao normalizar JID: {to}")
            
            # Normaliza o participant se fornecido
            normalized_participant = None
            if participant:
                normalized_participant = Jid.normalize(participant)
                if not normalized_participant:
                    logger.warning(f"Participant inválido: {participant}, ignorando")
            
            # Verifica se é grupo e ajusta participant
            is_group = normalized_to.endswith("@g.us")
            if is_group and normalized_participant:
                # Para grupos, o participant deve ser incluído
                participant_for_meta = normalized_participant
            else:
                participant_for_meta = None
            
            logger.debug(f"Enviando reação {emoji} para mensagem {message_id} em {normalized_to}")
            
            # Cria ReactionAttributes (inclui participant no key para grupos)
            reaction_attr = ReactionAttributes(
                msgid=message_id,
                remote_jid=normalized_to,
                from_me=False,
                text=emoji,
                sender_timestamp_ms=int(time.time() * 1000),
                participant=participant_for_meta
            )
            
            # Meta da mensagem (inclui participant para grupos)
            meta_attrs = MessageMetaAttributes(
                id=self.bot.idType,
                recipient=normalized_to,
                participant=participant_for_meta,
                timestamp=int(time.time()),
            )
            
            # Cria a entidade de reação
            reaction_entity = ReactionMessageProtocolEntity(
                reaction_attr,
                message_meta_attributes=meta_attrs
            )
            
            msg_id = reaction_entity.getId()
            logger.info(f"Preparando envio de reação (ID={msg_id}) para mensagem {message_id} em {normalized_to}")
            
            # Adiciona à fila de ACK
            self.ackQueue.append(msg_id)
            
            # Envia através do stack (ProtocolTreeNode)
            reaction_node = reaction_entity.toProtocolTreeNode()
            self.toLower(reaction_node)
            
            # Registra e notifica
            self._register_sent_message(msg_id, normalized_to, "REACTION", "EXECUTED")
            self._notify_message_sent(msg_id, normalized_to, to)
            
            # Se waitMsgId está configurado, sinaliza o evento
            if "waitMsgId" in options and "ctxId" in options:
                ctx_id = options["ctxId"]
                if ctx_id in self.ctxMap:
                    self.ctxMap[ctx_id]["msgId"] = msg_id
                    self.ctxMap[ctx_id]["event"].set()
            
            logger.info(f"Reação enviada com sucesso (ID={msg_id}) para mensagem {message_id} em {normalized_to}")
            return msg_id
            
        except Exception as e:
            error_msg = f"Erro ao enviar reação para {to}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Tenta registrar erro no banco de dados
            try:
                normalized_to = Jid.normalize(to) if to else None
                if normalized_to and self.bot.botId:
                    from zowsuplib.app.db import register_sent_message
                    register_sent_message(
                        phone=self.bot.botId,
                        msg_id=None,
                        recipient=normalized_to,
                        message_type="REACTION",
                        status="ERROR",
                        error_code=str(e)
                    )
            except:
                pass
            
            raise RuntimeError(error_msg) from e
    
    def sendReaction(self, cmdParams, options):
        """
        Envia uma reação (emoji) para uma mensagem.
        Wrapper que lida com waitMsgId e chama sendMessageReaction.
        
        Args:
            cmdParams: Lista com [to, message_id, emoji] ou [to, message_id, emoji, participant]
            options: Dict com opções adicionais (pode conter "waitMsgId" e "ctxId")
        
        Returns:
            "JUSTWAIT" se waitMsgId não estiver configurado
            message_id se waitMsgId estiver configurado e sucesso
            "TIMEOUT" se waitMsgId estiver configurado mas timeout
        """
        if "waitMsgId" not in options:
            # Envia sem aguardar ID
            self.sendMessageReaction(cmdParams, options)
            return "JUSTWAIT"
        else:
            # Configura contexto para aguardar ID
            ctxId = str(uuid.uuid4())
            self.ctxMap[ctxId] = {"event": threading.Event()}
            options["ctxId"] = ctxId
            
            # Envia a reação
            self.sendMessageReaction(cmdParams, options)
            
            # Aguarda o ID da mensagem
            ret = self.ctxMap[ctxId]["event"].wait(int(options["waitMsgId"]))
            if not ret:
                # Timeout
                del self.ctxMap[ctxId]
                return "TIMEOUT"
            else:
                # Sucesso - obtém o ID
                msgId = self.getContextValue(ctxId, "msgId")
                del self.ctxMap[ctxId]
                return msgId
    
    def sendTextReplyDirect(self, cmdParams, options):
        """
        Envia mensagem de texto marcando outra como resposta (reply/quote) de forma robusta e consistente.
        
        Args:
            cmdParams: Lista com [to, text, reply_to_message_id] ou [to, text, reply_to_message_id, reply_to_participant]
            options: Dict com opções adicionais (pode conter "quoted_text", etc.)
        
        Returns:
            message_id da mensagem enviada
        
        Raises:
            ValueError: Se parâmetros inválidos
            RuntimeError: Se não estiver conectado ou erro ao enviar
        """
        # Validação de parâmetros
        if not cmdParams or len(cmdParams) < 3:
            raise ValueError("sendTextReplyDirect requer pelo menos 3 parâmetros: [to, text, reply_to_message_id]")
        
        to = cmdParams[0]
        text = cmdParams[1]
        reply_to_message_id = cmdParams[2]
        reply_to_participant = cmdParams[3] if len(cmdParams) > 3 else None
        
        # Validação de entrada
        if not to or not isinstance(to, str):
            raise ValueError(f"Parâmetro 'to' inválido: {to}")
        
        if not text or not isinstance(text, str):
            raise ValueError(f"Parâmetro 'text' inválido: {text}")
        
        if not reply_to_message_id or not isinstance(reply_to_message_id, str):
            raise ValueError(f"Parâmetro 'reply_to_message_id' inválido: {reply_to_message_id}")
        
        # Validação de tamanho da mensagem
        MAX_MESSAGE_LENGTH = 4096
        if len(text) > MAX_MESSAGE_LENGTH:
            logger.warning(f"Mensagem muito longa ({len(text)} chars), truncando para {MAX_MESSAGE_LENGTH}")
            text = text[:MAX_MESSAGE_LENGTH]
        
        # Verifica se está conectado
        if not self.isConnected:
            error_msg = f"Não é possível enviar mensagem de reply: conta não está conectada (botId={self.bot.botId})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Verifica se a conta está restrita (anti-banimento)
        if self._check_account_restriction():
            error_msg = f"Conta {self.bot.botId} está com restrição, não é possível enviar mensagens"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            # Normaliza o JID do destinatário
            normalized_to = Jid.normalize(to)
            if not normalized_to:
                raise ValueError(f"Falha ao normalizar JID: {to}")
            
            # Normaliza o participant se fornecido
            normalized_participant = None
            if reply_to_participant:
                normalized_participant = Jid.normalize(reply_to_participant)
                if not normalized_participant:
                    logger.warning(f"Participant inválido: {reply_to_participant}, ignorando")
            
            # Verifica se o número está na lista de inválidos
            phone = normalized_to.split('@')[0] if '@' in normalized_to else normalized_to
            if self._is_number_invalid(phone):
                error_msg = f"Número {phone} é inválido no WhatsApp (marcado como inválido anteriormente)"
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            logger.debug(f"Enviando mensagem de reply para {normalized_to} (original: {to}) respondendo {reply_to_message_id}")
            
            # Verifica se é grupo
            is_group = normalized_to.endswith("@g.us")
            
            # Prepara context_info com informações do reply
            context_info = ContextInfoAttributes()
            context_info.stanza_id = reply_to_message_id
            context_info.participant = normalized_participant if normalized_participant and is_group else None
            context_info.remote_jid = None  # None indica que é do mesmo chat

            # Se quoted_text foi fornecido, cria um quoted_message simples para enriquecer a reply
            quoted_text = options.get("quoted_text")
            if quoted_text:
                try:
                    quoted_entity = TextMessageProtocolEntity(
                        body=quoted_text,
                        messageMetaAttributes=MessageMetaAttributes(
                            id=reply_to_message_id,
                            recipient=normalized_to,
                            participant=normalized_participant if normalized_participant and is_group else None,
                            fromMe=False
                        )
                    )
                    context_info.quoted_message = quoted_entity
                except Exception as e:
                    logger.warning(f"Não foi possível construir quoted_message: {e}, continuando sem quoted_text")
            
            # Cria ExtendedTextAttributes com context_info
            extended_text_attrs = ExtendedTextAttributes(
                text=text,
                preview_type=0,
                context_info=context_info,
                invite_link_group_type_v2=0
            )
            
            # Cria entidade da mensagem
            messageEntity = ExtendedTextMessageProtocolEntity(
                extended_text_attrs,
                MessageMetaAttributes(
                    id=self.bot.idType,
                    recipient=normalized_to,
                    timestamp=int(time.time())
                )
            )
            
            msg_id = messageEntity.getId()
            logger.info(f"Preparando envio de mensagem de reply (ID={msg_id}) para {normalized_to} respondendo {reply_to_message_id}")
            
            # Adiciona à fila de ACK
            self.ackQueue.append(msg_id)
            
            # Envia mensagem (usa o mesmo padrão de sendMsgDirect)
            if "broadcast" in options:
                self._send_broadcast_message(messageEntity, options)
            else:
                self._send_regular_message(messageEntity, normalized_to, to, options)
            
            # Registra no banco de dados
            self._register_sent_message(msg_id, normalized_to, "TEXT", "EXECUTED")
            
            # Notifica evento
            self._notify_message_sent(msg_id, normalized_to, to)
            
            # Se waitMsgId está configurado, sinaliza o evento
            if "waitMsgId" in options and "ctxId" in options:
                ctx_id = options["ctxId"]
                if ctx_id in self.ctxMap:
                    self.ctxMap[ctx_id]["msgId"] = msg_id
                    self.ctxMap[ctx_id]["event"].set()
            
            logger.info(f"Mensagem de reply enviada com sucesso (ID={msg_id}) para {normalized_to}")
            return msg_id
            
        except Exception as e:
            error_msg = f"Erro ao enviar mensagem de reply para {to}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Tenta registrar erro no banco de dados
            try:
                normalized_to = Jid.normalize(to) if to else None
                if normalized_to and self.bot.botId:
                    from zowsuplib.app.db import register_sent_message
                    register_sent_message(
                        phone=self.bot.botId,
                        msg_id=None,
                        recipient=normalized_to,
                        message_type="TEXT",
                        status="ERROR",
                        error_code=str(e)
                    )
            except:
                pass
            
            raise RuntimeError(error_msg) from e
    
    def sendTextReply(self, cmdParams, options):
        """
        Envia uma mensagem de texto marcando outra como resposta (reply/quote).
        Wrapper que lida com waitMsgId e chama sendTextReplyDirect.
        
        Args:
            cmdParams: Lista com [to, text, reply_to_message_id] ou [to, text, reply_to_message_id, reply_to_participant]
            options: Dict com opções adicionais (pode conter "waitMsgId", "ctxId", "quoted_text", etc.)
        
        Returns:
            "JUSTWAIT" se waitMsgId não estiver configurado
            message_id se waitMsgId estiver configurado e sucesso
            "TIMEOUT" se waitMsgId estiver configurado mas timeout
        """
        if "waitMsgId" not in options:
            # Envia sem aguardar ID, aplicando fluxo de sincronização/anti-ban
            self.assureContactsAndSend(
                cmdParams,
                options,
                send_func=self.sendTextReplyDirect,
                redo_func=self.sendTextReply
            )
            return "JUSTWAIT"
        else:
            # Configura contexto para aguardar ID
            ctxId = str(uuid.uuid4())
            self.ctxMap[ctxId] = {"event": threading.Event()}
            options["ctxId"] = ctxId
            
            # Envia a mensagem de reply com sincronização/anti-ban
            self.assureContactsAndSend(
                cmdParams,
                options,
                send_func=self.sendTextReplyDirect,
                redo_func=self.sendTextReply
            )
            
            # Aguarda o ID da mensagem
            ret = self.ctxMap[ctxId]["event"].wait(int(options["waitMsgId"]))
            if not ret:
                # Timeout
                del self.ctxMap[ctxId]
                return "TIMEOUT"
            else:
                # Sucesso - obtém o ID
                msgId = self.getContextValue(ctxId, "msgId")
                del self.ctxMap[ctxId]
                return msgId

    def sendMediaMsg(self,cmdParams,options):
    
        if "waitMsgId" not in options:
            self.assureContactsAndSend(cmdParams,options,send_func=self.sendMediaMsgDirect,redo_func=self.sendMediaMsg)            
            return "JUSTWAIT"             
        else:
            ctxId = str(uuid.uuid4())            
            self.ctxMap[ctxId] = {"event":threading.Event()}
            options["ctxId"] = ctxId                        
            self.assureContactsAndSend(cmdParams,options,send_func=self.sendMediaMsgDirect,redo_func=self.sendMediaMsg)                        
                 
            ret = self.ctxMap[ctxId]["event"].wait(int(options["waitMsgId"]))            
            if not ret:                
                return "TIMEOUT"
            else:                
                msgId = self.getContextValue(ctxId,"msgId")
                del self.ctxMap[ctxId]
                return msgId
            
    def sendMediaMsgDirect(self,cmdParams,options):
        def onRequestMediaConnResult(cmdParams, resultRequestMediaConnIqProtocolEntity, requestMediaConnIqProtocolEntity):
            to, mediaType, filePath,*other = cmdParams    
            caption = options["caption"] if "caption" in options else None
            fileName = options["fileName"] if "fileName" in options else None

            entity = None  # Inicializa entity como None

            try:
                if mediaType=="image":
                    if filePath.startswith("http://") or filePath.startswith("https://"):
                        attr_media = ImageAttributes.from_url(filePath,mediaType,resultRequestMediaConnIqProtocolEntity)
                    else:
                        # Verifica se o arquivo existe antes de tentar usar
                        if not os.path.exists(filePath):
                            error_msg = f"Arquivo de imagem não encontrado: {filePath}"
                            logger.error(error_msg)
                            raise FileNotFoundError(error_msg)
                        attr_media = ImageAttributes.from_filepath(filePath,mediaType,resultRequestMediaConnIqProtocolEntity)
                    attr_media.caption = caption
                    
                    entity = ImageDownloadableMediaMessageProtocolEntity(
                        image_attrs=attr_media,
                        message_meta_attrs=MessageMetaAttributes(id=self.bot.idType,recipient=Jid.normalize(to))
                    )            

                if mediaType=="video":            
                    if filePath.startswith("http://") or filePath.startswith("https://"):
                        attr_media = VideoAttributes.from_url(filePath,mediaType,resultRequestMediaConnIqProtocolEntity)
                    else:
                        # Verifica se o arquivo existe antes de tentar usar
                        if not os.path.exists(filePath):
                            error_msg = f"Arquivo de vídeo não encontrado: {filePath}"
                            logger.error(error_msg)
                            raise FileNotFoundError(error_msg)
                        attr_media = VideoAttributes.from_filepath(filePath,mediaType,resultRequestMediaConnIqProtocolEntity)
                    attr_media.caption = caption            
                    entity = VideoDownloadableMediaMessageProtocolEntity(
                        video_attrs=attr_media,
                        message_meta_attrs=MessageMetaAttributes(id=self.bot.idType,recipient= Jid.normalize(to))
                    )                         

                if mediaType=="audio":      
                    # Extrai opções PTT e waveform das options
                    ptt = options.get("ptt", False) if isinstance(options, dict) else False
                    waveform = options.get("waveform") if isinstance(options, dict) else None
                    
                    if filePath.startswith("http://") or filePath.startswith("https://"):
                        attr_media = AudioAttributes.from_url(
                            filePath,
                            mediaType,
                            resultRequestMediaConnIqProtocolEntity,
                            ptt=ptt,
                            waveform=waveform
                        )          
                    else:
                        # Verifica se o arquivo existe antes de tentar usar
                        if not os.path.exists(filePath):
                            error_msg = f"Arquivo de áudio não encontrado: {filePath}"
                            logger.error(error_msg)
                            raise FileNotFoundError(error_msg)
                        attr_media = AudioAttributes.from_filepath(
                            filePath,
                            mediaType,
                            resultRequestMediaConnIqProtocolEntity,
                            ptt=ptt,
                            waveform=waveform
                        )          
                    entity = AudioDownloadableMediaMessageProtocolEntity(
                        audio_attrs=attr_media,
                        message_meta_attrs=MessageMetaAttributes(id=self.bot.idType,recipient= Jid.normalize(to))
                    )                         
                    
                if mediaType=="document":        
                    if filePath.startswith("http://") or filePath.startswith("https://"):
                        attr_media = DocumentAttributes.from_url(filePath,fileName,mediaType,resultRequestMediaConnIqProtocolEntity)  
                    else:
                        # Verifica se o arquivo existe antes de tentar usar
                        if not os.path.exists(filePath):
                            error_msg = f"Arquivo de documento não encontrado: {filePath}"
                            logger.error(error_msg)
                            raise FileNotFoundError(error_msg)
                        attr_media = DocumentAttributes.from_filepath(filePath,fileName,mediaType,resultRequestMediaConnIqProtocolEntity)          
                    entity = DocumentDownloadableMediaMessageProtocolEntity(
                        document_attrs=attr_media,
                        message_meta_attrs=MessageMetaAttributes(id=self.bot.idType,recipient= Jid.normalize(to))
                    )

                if mediaType=="sticker":
                    # Opções para sticker (is_animated, is_avatar, etc.)
                    is_animated = options.get("is_animated", False) if "is_animated" in options else False
                    is_avatar = options.get("is_avatar", False) if "is_avatar" in options else False
                    is_ai_sticker = options.get("is_ai_sticker", False) if "is_ai_sticker" in options else False
                    is_lottie = options.get("is_lottie", False) if "is_lottie" in options else False
                    
                    if filePath.startswith("http://") or filePath.startswith("https://"):
                        attr_media = StickerAttributes.from_url(
                            filePath, "sticker", resultRequestMediaConnIqProtocolEntity,
                            is_animated=is_animated, is_avatar=is_avatar,
                            is_ai_sticker=is_ai_sticker, is_lottie=is_lottie
                        )
                    else:
                        attr_media = StickerAttributes.from_filepath(
                            filePath, "sticker", resultRequestMediaConnIqProtocolEntity,
                            is_animated=is_animated, is_avatar=is_avatar,
                            is_ai_sticker=is_ai_sticker, is_lottie=is_lottie
                        )
                    entity = StickerDownloadableMediaMessageProtocolEntity(
                        sticker_attrs=attr_media,
                        message_meta_attrs=MessageMetaAttributes(id=self.bot.idType,recipient= Jid.normalize(to))
                    )

                # Verifica se entity foi definido
                if entity is None:
                    logger.error(f"Tipo de mídia '{mediaType}' não suportado ou entity não foi criado")
                    return None

                logger.info(f"Send Media {mediaType} Msg (ID={entity.getId()})")                

                self.ackQueue.append(entity.getId())

                self.toLower(entity) 

                # Registra a mensagem de mídia enviada no banco de dados
                if self.bot.botId is not None:
                    from zowsuplib.app.db import register_sent_message
                    recipient_jid = Jid.normalize(to)
                    register_sent_message(
                        phone=self.bot.botId,
                        msg_id=entity.getId(),
                        recipient=recipient_jid,
                        message_type=mediaType.upper(),
                        status="EXECUTED",
                    )

                self.eventCallback(wsend_pb2.BotEvent.Event.MSG_LOG,msgLog={
                    'msgId':entity.getId(),                    
                    'sender':self.bot.botId,
                    "target":to[0:Jid.normalize(to).rfind("@",0)],
                    'status': wsend_pb2.MsgLogItem.Status.Value("EXECUTED")                
                })  

                if "waitMsgId" in options and "ctxId" in options:
                    ctx_id = options["ctxId"]
                    if ctx_id in self.ctxMap:
                        self.ctxMap[ctx_id]["msgId"] = entity.getId()
                        self.ctxMap[ctx_id]["event"].set()
                    else:
                        logger.warning(f"ctxId {ctx_id} não encontrado em ctxMap ao processar resultado de mídia. Pode ter sido removido prematuramente.")            

                return entity.getId()                   
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem de mídia: {e}", exc_info=True)
                # Se há waitMsgId e ctxId, sinaliza erro no ctxMap
                if "waitMsgId" in options and "ctxId" in options:
                    ctx_id = options.get("ctxId")
                    if ctx_id and ctx_id in self.ctxMap:
                        self.ctxMap[ctx_id]["error"] = {
                            "code": -1,
                            "msg": str(e)
                        }
                        self.ctxMap[ctx_id]["event"].set()
                return None
                
        def onRequestMediaConnError(cmdParams, errorRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity):
            logger.error("Request upload for file failed")
            # Se há waitMsgId, sinaliza erro no ctxMap
            if "waitMsgId" in options and "ctxId" in options:
                ctx_id = options["ctxId"]
                if ctx_id in self.ctxMap:
                    self.ctxMap[ctx_id]["error"] = {
                        "code": errorRequestUploadIqProtocolEntity.code if hasattr(errorRequestUploadIqProtocolEntity, 'code') else "Unknown",
                        "msg": str(errorRequestUploadIqProtocolEntity)
                    }
                    self.ctxMap[ctx_id]["event"].set()
                else:
                    logger.warning(f"ctxId {ctx_id} não encontrado em ctxMap ao processar erro de mídia.")

        mediaType = cmdParams[1]
        if not mediaType in ["image","video","audio","document","sticker"]:
            logger.info(f"sendmedia type {mediaType} is not supported now")

        entity = RequestMediaConnIqProtocolEntity()
        successFn = lambda successEntity, originalEntity: onRequestMediaConnResult( cmdParams, successEntity, originalEntity)
        errorFn = lambda errorEntity, originalEntity: onRequestMediaConnError(cmdParams, errorEntity, originalEntity)
        self._sendIq(entity, successFn, errorFn)

    def sendStatus(self, cmdParams, options):
        """
        Envia status de texto para status@broadcast.
        
        Args:
            cmdParams: [to, text] - to deve ser "status@broadcast"
            options: Opções adicionais (text_color, background_color, font, etc.)
        """
        # Garante que está enviando para status@broadcast
        if len(cmdParams) < 2:
            raise ValueError("sendStatus requer [to, text]")
        
        to = cmdParams[0]
        text = cmdParams[1]
        
        # Normaliza para status@broadcast se necessário
        if to != "status@broadcast" and not to.endswith("@broadcast"):
            logger.warning(f"sendStatus: destinatário '{to}' não é status@broadcast, ajustando")
            to = "status@broadcast"
        
        # Usa sendMsgDirect com as opções de status
        return self.sendMsgDirect([to, text], options)

    def sendStatusMedia(self, cmdParams, options):
        """
        Envia status de mídia (imagem/vídeo) para status@broadcast.
        
        Args:
            cmdParams: [to, mediaType, filePath] - to deve ser "status@broadcast"
            options: Opções adicionais (caption, etc.)
        """
        # Garante que está enviando para status@broadcast
        if len(cmdParams) < 3:
            raise ValueError("sendStatusMedia requer [to, mediaType, filePath]")
        
        to = cmdParams[0]
        mediaType = cmdParams[1]
        filePath = cmdParams[2]
        
        # Normaliza para status@broadcast se necessário
        if to != "status@broadcast" and not to.endswith("@broadcast"):
            logger.warning(f"sendStatusMedia: destinatário '{to}' não é status@broadcast, ajustando")
            to = "status@broadcast"
        
        # Usa sendMediaMsgDirect
        return self.sendMediaMsgDirect([to, mediaType, filePath], options)
        self._sendIq(entity, successFn, errorFn)

    def revokeMsg(self,cmdParams,options):
        attr = ProtocolAttributes(
            key=MessageKeyAttributes(
                id=cmdParams[1],
                from_me=True,
                remote_jid=Jid.normalize(cmdParams[0])                
            ),
            type=ProtocolAttributes.TYPE_REVOKE
        )
        messageEntity = ProtocolMessageProtocolEntity(attr,
            MessageMetaAttributes(id=self.bot.idType,recipient=Jid.normalize(cmdParams[0]),timestamp=int(time.time()),edit="7")            
        )
        self.toLower(messageEntity)
        return "JUSTWAIT"
    
    def editMsg(self,cmdParams,options):
        attr = ProtocolAttributes(
            key=MessageKeyAttributes(
                id=cmdParams[1],
                from_me=True,
                remote_jid=Jid.normalize(cmdParams[0])                
            ),
            type=ProtocolAttributes.TYPE_MESSAGE_EDIT,            
            edited_message=MessageAttributes(
                extended_text=ExtendedTextAttributes(
                    text = cmdParams[2],            
                    preview_type=0,
                    context_info=ContextInfoAttributes()
                )
            ),
            timestamp_ms=int(time.time()*1000)
        )        
        messageEntity = ProtocolMessageProtocolEntity(attr,
            MessageMetaAttributes(id=self.bot.idType,recipient=Jid.normalize(cmdParams[0]),timestamp=int(time.time()),edit="1")            
        )
        self.toLower(messageEntity)
        return "JUSTWAIT"

    def syncContacts(self,cmdParams,options):            
        if "mode" not in options:
            options["mode"] = "delta"                      
        if "cnt" not in options:
            options["cnt"] = "30"

        nums = cmdParams[0].split(',')        
      
        entity = GetSyncIqProtocolEntity(nums,mode = options["mode"])    

        def on_success(entity, original_iq_entity):  
            logger.info("syncContacts success with %d contacts" % len(entity.inNumbers))
            
            # Salva todos os contatos válidos no banco de dados
            saved_count = 0
            try:
                # Salva contatos de inNumbers (números que têm você nos contatos)
                for number, jid in entity.inNumbers.items():
                    try:
                        saved_jid = self.db._store.addContact(jid)
                        if saved_jid:
                            saved_count += 1
                            logger.debug(f"Contato {jid} (número {number}) salvo no banco via syncContacts")
                    except Exception as e:
                        logger.warning(f"Erro ao salvar contato {jid} (número {number}): {e}")
                
                # Salva contatos de outNumbers (números que você tem nos contatos)
                for number, jid in entity.outNumbers.items():
                    try:
                        # Verifica se já não foi salvo em inNumbers
                        if jid not in entity.inNumbers.values():
                            saved_jid = self.db._store.addContact(jid)
                            if saved_jid:
                                saved_count += 1
                                logger.debug(f"Contato {jid} (número {number}) salvo no banco via syncContacts")
                    except Exception as e:
                        logger.warning(f"Erro ao salvar contato {jid} (número {number}): {e}")
                
                if saved_count > 0:
                    logger.info(f"syncContacts: {saved_count} contatos salvos no banco de dados")
            except Exception as e:
                logger.error(f"Erro ao salvar contatos no banco durante syncContacts: {e}", exc_info=True)
                        
            self.setCmdResult(entity.getId(),{
                "count": len(entity.inNumbers),
                "valid": entity.inNumbers,
                "invalid": entity.outNumbers,
                "jids": list(entity.inNumbers.values()),
                "saved_count": saved_count
            })              

        def on_error(entity, original_iq):            
            logger.error("syncContacts error")
            
        self._sendIq(entity,on_success,on_error)
        return entity.getId()
 
    def getConfig(self,cmdParams,options)  :
        push = PushIqProtocolEntity()
        self.toLower(push)
        logger.info("push iq")
        props = PropsIqProtocolEntity()
        self.toLower(props)
        logger.info("props iq")

    def cleanDirty(self,cmdParams,options) :
        entity = CleanDirtyIqProtocolEntity(type=cmdParams[0])
        self.toLower(entity)

    def joinGroupWithCode(self,cmdParams,options):        

        def on_success(entity, original_iq_entity):                 
            logger.info("joinGroupWithCode success")    
            self.setCmdResult(entity.getId(),{"group_jid":entity.groupId})
                                                 
        def on_fail(entity, original_iq):          
            logger.error("joinGroupWithCode error")         


        entity = JoinWithCodeGroupsIqProtocolEntity(code=cmdParams[0])

        self._sendIq(entity,on_success,on_fail)
        return entity.getId()        


    def getAccountInfo(self, cmdParams, options):
        """Obtém informações da conta (creation, last_reg)"""
        def on_success(entity, original_iq_entity):
            logger.info("getAccountInfo success")
            from zowsuplib.yowsup.layers.protocol_iq.protocolentities.iq_account_info_result import AccountInfoResultIqProtocolEntity
            if isinstance(entity, AccountInfoResultIqProtocolEntity):
                result = {
                    "creation": entity.creation,
                    "last_reg": entity.lastReg
                }
            else:
                result = {"status": "ok"}
            self.setCmdResult(entity.getId(), result)
        
        def on_error(entity, original_iq):
            logger.error("getAccountInfo error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        from zowsuplib.yowsup.layers.protocol_iq.protocolentities.iq_account_info import AccountInfoIqProtocolEntity
        entity = AccountInfoIqProtocolEntity()
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def getAvatar(self,cmdParams,options):        
        if len(cmdParams)==0:
            target = self.bot.botId
        else:
            target = cmdParams[0]

        def on_success(entity, original_iq_entity):                   
            result = {
                "id":entity.getPictureId(),
                "type":entity.getPictureType(),
                "url":entity.getUrl()
            }                
            self.setCmdResult(entity.getId(),result)
            return     

        def on_error(entity, original_iq):                                                 
            self.setCmdError(entity.getId(),entity.code)
        
        entity = GetPictureIqProtocolEntity(jid=Jid.normalize(target),preview=False)        

        self._sendIq(entity,on_success,on_error)
        return entity.getId()
    
    def set2FA(self, cmdParams, options):
        """Define a autenticação de dois fatores (2FA)"""
        def on_success(entity, original_iq_entity):
            logger.info("set2FA success")
            self.setCmdResult(entity.getId(), {"status": "ok"})
        
        def on_error(entity, original_iq):
            logger.error("set2FA error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        if len(cmdParams) == 0:
            cmdParams = [self.bot.botId[-6:], self.bot.botId+"@163.com"]
        entity = Set2FAIqProtocolEntity(code=cmdParams[0], email=cmdParams[1])
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
                
    def setAvatar(self, cmdParams, options):
        """Define o avatar da conta a partir de URL ou arquivo local"""
        def on_success(entity, original_iq_entity):
            logger.info("setAvatar success")
            self.setCmdResult(entity.getId(), {"status": "ok"})
        
        def on_error(entity, original_iq):
            logger.error("setAvatar error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        if len(cmdParams) == 0:
            raise ParamsNotEnoughException()
        
        avatar_source = cmdParams[0]  # Pode ser URL ou caminho de arquivo
        
        with PILOptionalModule(failMessage="No PIL library installed, try install pillow") as imp:
            Image = imp("Image")
            
            # Se for URL, baixa; se for arquivo, abre diretamente
            if avatar_source.startswith(("http://", "https://")):
                image_data = requests.get(avatar_source).content
                src = Image.open(io.BytesIO(image_data)).convert("RGB")
            else:
                # Assume que é um caminho de arquivo local
                if not os.path.exists(avatar_source):
                    raise FileNotFoundError(f"Arquivo não encontrado: {avatar_source}")
                src = Image.open(avatar_source).convert("RGB")
            
            picture = io.BytesIO()
            preview = io.BytesIO()
            src.resize((640, 640)).save(picture, format="jpeg")
            src.resize((96, 96)).save(preview, format="jpeg")
            
            entity = SetPictureIqProtocolEntity("s.whatsapp.net", preview.getvalue(), picture.getvalue())
            self._sendIq(entity, on_success, on_error)
            return entity.getId()

    def subscribePresence(self, cmdParams,options):
        entity = SubscribePresenceProtocolEntity(jid = Jid.normalize(cmdParams[0]))
        self.toLower(entity)
        return entity.getId()

    def setName(self, cmdParams, options):
        """Define o nome da conta (pushname) usando AppState Sync (padrão whatsmeow)"""
        def on_success(entity, original_iq_entity):
            logger.info("setName (AppState Sync) success")
            # Atualiza o pushname no profile após sucesso
            profile = self.getStack().getProp("profile")
            if profile:
                profile.config.pushname = cmdParams[0]
                profile.write_config(profile.config)
            self.setCmdResult(entity.getId(), {"status": "ok", "name": cmdParams[0]})
        
        def on_error(entity, original_iq):
            logger.error("setName (AppState Sync) error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        try:
            # Obtém uma chave de AppState
            key = self.db._store.getOneAppStateKey()
            if not key:
                # Se não houver chaves, gera automaticamente
                logger.warning("No AppState keys found. Generating new keys...")
                sync_keys = self.generateAppStateSyncKeys(10)
                self.db._store.addAppStateKeys(sync_keys)
                key = self.db._store.getOneAppStateKey()
                if not key:
                    raise Exception("Failed to generate AppState keys")
            
            # Cria as mutation keys a partir da chave
            mutationKeys = MutationKeys.createFromKey(key.key_data.key_data)
            
            # Cria a mutation para pushname setting
            pushNameSetting = SyncActionDataAttribute.createFromSyncActionValue(
                SyncActionValueAttribute(
                    pushNameSetting=SyncActionPushnameSettingAttribute(name=cmdParams[0])
                )
            )
            
            # Cria o estado inicial (critical_block é onde ficam as configurações como pushname)
            # Nota: Em produção, deveria obter a versão atual do app state, mas por simplicidade
            # começamos com version 0. O WhatsApp aceitará e retornará a versão correta.
            state = HashState("critical_block", 0)
            
            # Constrói o patch com a mutation
            state, syncdPatch = PatchBuilder(state, mutationKeys, key).addMutation(pushNameSetting).finish()
            
            # Cria a entidade IQ para enviar o app state sync
            # O patch precisa ser codificado (encode() retorna o objeto protobuf)
            # O AppSyncStateIqProtocolEntity chama SerializeToString() internamente no protobuf
            patches = {"critical_block": syncdPatch.encode()}
            entity = AppSyncStateIqProtocolEntity(patches=patches)
            
            # Envia o IQ
            self._sendIq(entity, on_success, on_error)
            return entity.getId()
            
        except Exception as e:
            logger.error(f"Erro ao definir pushname via AppState Sync: {e}", exc_info=True)
            cmd_id = f"appstate-setname-error-{int(time.time() * 1000)}"
            self.setCmdError(cmd_id, str(e))
            return cmd_id

    def trustContact(self,cmdParams,options):
        def onSuccess(entity, originalIqEntity):
            self.setCmdResult(entity.getId(),{"status":"OK"})
            logger.info("trust contact  success")

        def onError(errorIqEntity, originalIqEntity):
            logger.info("trust contact error")
        
        entity = TrustContactIqProtocolEntity(Jid.normalize(cmdParams[0]),int(time.time()))
        self._sendIq(entity, onSuccess, onError)    
        return entity.getId() 
    
    def setBusinessName(self,cmdParams,options):     

        def on_success(entity, original_iq_entity):                                 
            self.setCmdResult(entity.getId(),{"status":"OK"})
                            
        def on_error(entity, original_iq):          
            logger.error("listGroup error")            

        entity = SetBusinessNameIqProtocolEntity(profile = self.getStack().getProp("profile"), name = cmdParams[0])
        self._sendIq(entity,on_success,on_error)
        return entity.getId()

    def setMode(self,mode):
        self.mode = mode

    def createGroup(self,params,options):        
        if len(params)!=2:
            self.setCmdResult()
        if params[1]=="":
            logger.info("create an empty group")
            pList = None
        else:
            pList = Jid.normalize(params[1]).split(",")
        entity = CreateGroupsIqProtocolEntity(params[0],participants=pList,creator=self.bot.botId)    

        def on_success(entity, original_iq_entity):        
            if isinstance(entity,SuccessCreateGroupsIqProtocolEntity):    
                logger.info("makegroup success")                
                self.setCmdResult(entity.getId(),{
                    "groupId":entity.groupId
                })
        def on_error(entity, original_iq):                        
            logger.error("makegroup error")       
         
        self._sendIq(entity,on_success,on_error)
        return entity.getId()

    def groupInfo(self,cmdParams,options):
        def on_success(entity, original_iq_entity):  
            logger.info("groupinfo success")            
            self.setCmdResult(entity.getId(),{
                "groupId": entity.groupId,
                "subject": entity.subject,
                "participants": entity.participants
            })                        

        def on_error(entity, original_iq):            
            logger.error("groupinfo error")
            self.setCmdError(entity.getId(),entity.code)

        entity = InfoGroupsIqProtocolEntity(group_jid = Jid.normalize(cmdParams[0]))
        self._sendIq(entity,on_success,on_error)
        return entity.getId()

    def getGroupInvite(self,cmdParams,options):

        def on_success(entity, original_iq_entity):            
            if isinstance(entity,SuccessGetInviteCodeGroupsIqProtocolEntity):    
                logger.info("getgroupinvite success")       
                self.setCmdResult(entity.getId(), {
                    "groupJid":entity.groupJid,
                    "inviteCode": entity.inviteCode
                })       

        def on_error(entity, original_iq):                        
            logger.info("getgroupinvite error")  

        to = cmdParams[0]        
        entity = GetInviteCodeGroupsIqProtocolEntity(group_jid=Jid.normalize(to))
        self._sendIq(entity, on_success, on_error)
        
        return entity.getId()
    
    def listGroups(self,cmdParams,options):
        
        def on_success(entity, original_iq_entity):
            if isinstance(entity, ListGroupsResultIqProtocolEntity):
                groups = []
                groups_admins = []
                for group in entity.getGroups():
                    groups.append({
                        "id": group.getId(),
                        "subject": group.getSubject(),
                        "creator": group.getCreator(),
                        "subjectOwner": group.getSubjectOwner(),
                        "subjectTime": group.getSubjectTime(),
                        "creationTime": group.getCreationTime(),
                        "participants": group.getParticipants(),
                    })
                    # getGroupAdmins retorna lista de objetos Group quando account_jid é fornecido
                    admin_groups = group.getGroupAdmins(account_jid=self.bot.botId)
                    # Converte objetos Group para dicionários
                    for admin_group in admin_groups:
                        groups_admins.append({
                            "group_id": admin_group.getId(),
                            "subject": admin_group.getSubject(),
                            "creator": admin_group.getCreator(),
                            "owner": admin_group.getOwner(),
                        })

                        
                    logger.info(f"Groups admins: {groups_admins}")


                logger.info(f"Groups admins out: {groups_admins}")

                self.setCmdResult(entity.getId(), {
                    "groups": groups,
                    "groups_admins": groups_admins,
                    "count": len(groups)
                })

        def on_error(entity, original_iq):
            self.setCmdError(entity.getId(), "Failed to get groups list")

        entity = ListGroupsIqProtocolEntity(participants=True)
        self._sendIq(entity, on_success, on_error)
        return entity.getId()

    def groupAdd(self,cmdParams,options):
        def on_success(entity, original_iq_entity):  
            logger.info("groupadd success")

            self.setCmdResult(entity.getId(),{
                "successCount": len(entity.successList),
                "successJids": entity.successList,
                "errorCount": len(entity.errorList),
                "errorJids": entity.errorList
            }) 

        def on_error(entity, original_iq):            
            logger.error("groupadd error")
            self.setCmdError(entity.getId(),entity.code)

        entity = AddParticipantsIqProtocolEntity(
            group_jid = Jid.normalize(cmdParams[0]),
            participantList=Jid.normalize(cmdParams[1]).split(",")
        )
        self._sendIq(entity,on_success,on_error)
        return entity.getId()
    
    def checkDevice(self,cmdParams,options):
        def on_success(entity, original_iq_entity):  
            logger.info("checkDevice success")            

        def on_error(entity, original_iq):            
            logger.error("checkDevice error")

        entity = DevicesGetSyncIqProtocolEntity([cmdParams[0]])
        self._sendIq(entity, on_success, on_error)   
        return entity.getId()



    def groupApprove(self,cmdParams,options):
        if len(cmdParams)>=3:
            action = cmdParams[2]
        else:
            action = 'approve'

        entity = ApproveParticipantsGroupsIqProtocolEntity(
            group_jid = Jid.normalize(cmdParams[0]),
            participantList=Jid.normalize(cmdParams[1]).split(","),
            action = action            
        )        
        self.toLower(entity)

    def setGroupIcon(self, cmdParams, options):
        """Define o ícone do grupo a partir de URL ou arquivo local"""
        def on_success(entity, original_iq_entity):
            logger.info("setGroupIcon success")
            self.setCmdResult(entity.getId(), {"status": "ok"})
        
        def on_error(entity, original_iq):
            logger.error("setGroupIcon error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        group_jid = Jid.normalize(cmdParams[0])
        icon_source = cmdParams[1]  # Pode ser URL ou caminho de arquivo
        
        with PILOptionalModule(failMessage="No PIL library installed, try install pillow") as imp:
            Image = imp("Image")
            
            # Se for URL, baixa; se for arquivo, abre diretamente
            if icon_source.startswith(("http://", "https://")):
                image_data = requests.get(icon_source).content
                src = Image.open(io.BytesIO(image_data)).convert("RGB")
            else:
                # Assume que é um caminho de arquivo local
                if not os.path.exists(icon_source):
                    raise FileNotFoundError(f"Arquivo não encontrado: {icon_source}")
                src = Image.open(icon_source).convert("RGB")
            
            picture = io.BytesIO()
            preview = io.BytesIO()
            src.resize((640, 640)).save(picture, format="jpeg")
            src.resize((96, 96)).save(preview, format="jpeg")
            
            entity = SetPictureIqProtocolEntity(
                "s.whatsapp.net", 
                preview.getvalue(), 
                picture.getvalue(),
                target=Jid.normalize(group_jid)
            )
            self._sendIq(entity, on_success, on_error)
            return entity.getId()        
            
    def leaveGroup(self,cmdParams,options):
        def on_success(entity, original_iq_entity):         
            logger.info("leavegroup success")  
            self.setCmdResult(entity.getId(),{"status":"ok"})                                                 
        def on_error(entity, original_iq):          
            logger.error("leavegroup error")              

        groupJid = cmdParams[0]        
        entity = LeaveGroupsIqProtocolEntity([Jid.normalize(groupJid)])
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def setGroupSubject(self, cmdParams, options):
        """Define o assunto/nome do grupo"""
        def on_success(entity, original_iq_entity):
            logger.info("setGroupSubject success")
            self.setCmdResult(entity.getId(), {"status": "ok", "subject": cmdParams[1]})
        
        def on_error(entity, original_iq):
            logger.error("setGroupSubject error")
            self.setCmdError(entity.getId(), entity.code)
        
        group_jid = Jid.normalize(cmdParams[0])
        subject = cmdParams[1]
        entity = SubjectGroupsIqProtocolEntity(group_jid, subject)
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def setGroupDescription(self, cmdParams, options):
        """Define a descrição do grupo (seguindo padrão whatsmeow)"""
        group_jid = Jid.normalize(cmdParams[0])
        description = cmdParams[1] if len(cmdParams) > 1 else ""
        
        # Obtém previous_id e new_id das opções ou gera/obtém automaticamente
        previous_id = options.get("previous_id") or options.get("prev_id")
        new_id = options.get("new_id")
        
        # Se previous_id não foi fornecido, tenta obter das informações do grupo
        if not previous_id:
            try:
                # Busca informações do grupo para obter o topic_id atual
                # Nota: Isso requer uma chamada síncrona, então vamos fazer de forma assíncrona
                # Por enquanto, deixamos None e o WhatsApp pode lidar com isso
                pass
            except Exception as e:
                logger.warning(f"Could not get previous topic ID: {e}")
        
        # Se new_id não foi fornecido, gera um novo ID de mensagem
        if not new_id:
            # Gera um ID no formato do WhatsApp (32 caracteres hexadecimais)
            import random
            import string
            new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
        
        def on_success(entity, original_iq_entity):
            logger.info("setGroupDescription success")
            self.setCmdResult(entity.getId(), {"status": "ok", "description": description})
        
        def on_error(entity, original_iq):
            logger.error("setGroupDescription error")
            self.setCmdError(entity.getId(), entity.code)
        
        entity = DescriptionGroupsIqProtocolEntity(
            group_jid, 
            description, 
            new_id=new_id, 
            previous_id=previous_id
        )
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def setGroupSettings(self, cmdParams, options):
        """Define configurações do grupo (locked/unlocked, announcement, etc.)"""
        def on_success(entity, original_iq_entity):
            logger.info("setGroupSettings success")
            self.setCmdResult(entity.getId(), {"status": "ok"})
        
        def on_error(entity, original_iq):
            logger.error("setGroupSettings error")
            self.setCmdError(entity.getId(), entity.code)
        
        group_jid = Jid.normalize(cmdParams[0])
        action = cmdParams[1]  # "locked", "unlocked", "announcement", "not_announcement", etc.
        value = cmdParams[2] if len(cmdParams) > 2 else None
        entity = SetGroupsIqProtocolEntity(group_jid, action, value)
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def groupRemove(self, cmdParams, options):
        """Remove participantes do grupo"""
        def on_success(entity, original_iq_entity):
            logger.info("groupRemove success")
            self.setCmdResult(entity.getId(), {
                "successCount": len(entity.successList) if hasattr(entity, 'successList') else 0,
                "successJids": entity.successList if hasattr(entity, 'successList') else [],
                "errorCount": len(entity.errorList) if hasattr(entity, 'errorList') else 0,
                "errorJids": entity.errorList if hasattr(entity, 'errorList') else []
            })
        
        def on_error(entity, original_iq):
            logger.error("groupRemove error")
            self.setCmdError(entity.getId(), entity.code)
        
        entity = RemoveParticipantsIqProtocolEntity(
            group_jid=Jid.normalize(cmdParams[0]),
            participantList=Jid.normalize(cmdParams[1]).split(",")
        )
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def groupPromote(self, cmdParams, options):
        """Promove participantes a administradores"""
        def on_success(entity, original_iq_entity):
            logger.info("groupPromote success")
            self.setCmdResult(entity.getId(), {"status": "ok"})
        
        def on_error(entity, original_iq):
            logger.error("groupPromote error")
            self.setCmdError(entity.getId(), entity.code)
        
        entity = PromoteParticipantsIqProtocolEntity(
            group_jid=Jid.normalize(cmdParams[0]),
            participantList=Jid.normalize(cmdParams[1]).split(",")
        )
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def groupDemote(self, cmdParams, options):
        """Remove privilégios de administrador de participantes"""
        def on_success(entity, original_iq_entity):
            logger.info("groupDemote success")
            self.setCmdResult(entity.getId(), {"status": "ok"})
        
        def on_error(entity, original_iq):
            logger.error("groupDemote error")
            self.setCmdError(entity.getId(), entity.code)
        
        entity = DemoteParticipantsIqProtocolEntity(
            group_jid=Jid.normalize(cmdParams[0]),
            participantList=Jid.normalize(cmdParams[1]).split(",")
        )
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def resetSync(self,params,options):        
        entity = AppSyncResetIqProtocolEntity()
        self.toLower(entity)

    def multiDeviceLink(self,cmdParams,options): 

        profile = self.getStack().getProp("profile")
        qr_str = cmdParams[0]
        ref,pubKey,deviceIdentity,keyIndexList = Utils.generateMultiDeviceParamsFromQrCode(qr_str,profile)

        entity = MultiDevicePairDeviceIqProtocolEntity(ref=ref,pubKey=pubKey,deviceIdentity=deviceIdentity,keyIndexList=keyIndexList)
        
        def on_pair_device_success(entity, original_iq_entity):                    
            companionJid = entity.deviceJid
            deviceIdx =  int(companionJid.split("@")[0].split(":")[1])
            profile.config.add_device_to_list(deviceIdx)
            profile.write_config(profile.config)

            self.getStack().setProp("pair-companion-jid",companionJid)
            
        def on_pair_device_error(entity, original_iq):         
            logger.error("pair device error")               
            self.quit()            

        self._sendIq(entity, on_pair_device_success, on_pair_device_error)


    def multiDeviceRemove(self,cmdParams,options):
        if len(cmdParams)==0 or cmdParams[0]=="all":
            entity = MultiDeviceRemoveCompanionDeviceIqProtocolEntity(jid=None)     #表示删除所有
        else:
            entity = MultiDeviceRemoveCompanionDeviceIqProtocolEntity(jid=Jid.normalize(cmdParams[0]))

        self.toLower(entity)
        return entity.getId()        
    
    def setEmail(self, cmdParams, options):
        """Define o email da conta"""
        def on_success(entity, original_iq_entity):
            logger.info("setEmail success")
            self.setCmdResult(entity.getId(), {"status": "ok", "email": cmdParams[0]})
        
        def on_error(entity, original_iq):
            logger.error("setEmail error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        entity = SetEmailIqProtocolEntity(email=cmdParams[0])
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def getEmail(self, cmdParams, options):
        """Obtém o email da conta"""
        def on_success(entity, original_iq_entity):
            logger.info("getEmail success")
            if isinstance(entity, EmailResultIqProtocolEntity):
                result = {
                    "email": entity.emailAddress,
                    "verified": entity.verified,
                    "confirmed": entity.confirmed,
                    "do_verify": entity.doVerify
                }
            else:
                result = {"status": "ok"}
            self.setCmdResult(entity.getId(), result)
        
        def on_error(entity, original_iq):
            logger.error("getEmail error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        entity = GetEmailIqProtocolEntity()
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def verifyEmail(self, cmdParams, options):
        """Solicita verificação do email"""
        def on_success(entity, original_iq_entity):
            logger.info("verifyEmail success")
            if isinstance(entity, VerifyEmailResultIqProtocolEntity):
                result = {
                    "status": "ok",
                    "email": entity.emailAddress if hasattr(entity, 'emailAddress') else None
                }
            else:
                result = {"status": "ok"}
            self.setCmdResult(entity.getId(), result)
        
        def on_error(entity, original_iq):
            logger.error("verifyEmail error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        entity = VerifyEmailIqProtocolEntity()
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def verifyEmailCode(self, cmdParams, options):
        """Verifica o código de verificação do email"""
        def on_success(entity, original_iq_entity):
            logger.info("verifyEmailCode success")
            self.setCmdResult(entity.getId(), {"status": "ok", "code": cmdParams[0]})
        
        def on_error(entity, original_iq):
            logger.error("verifyEmailCode error")
            self.setCmdError(entity.getId(), entity.code if hasattr(entity, 'code') else "Unknown error")
        
        entity = VerifyEmailCodeIqProtocolEntity(code=cmdParams[0])
        self._sendIq(entity, on_success, on_error)
        return entity.getId()
    
    def inputPairingCode(self,params,options):
        if self.pairingStatus!="WAIT_PAIRINGCODE":
            logger.error("NOT IN WAITING CODE STATUS")
            return 
        
        self.pairingCode = params[0]

        if self.pairingCode:
            linkCode = self.pairingCode
            primaryEphemerKeyPair = WATools.generateKeyPair()
            companionEphemerPub = Utils.link_code_decrypt(linkCode,self.companionHelloEntity.linkCodePairingWrappedCompanionEphemeralPub)
            self.setProp("companionEphemerPub",companionEphemerPub)
            self.setProp("companionAuthKeyPub",self.companionHelloEntity.companionServerAuthKeyPub)
            self.setProp("keypair",primaryEphemerKeyPair)                
            linkCodePairingWrappedPrimaryEphemeralPub = Utils.link_code_encrypt(linkCode,primaryEphemerKeyPair.public.data)                            
            #发送primary_hello回包
            entity = MultiDevicePairPrimaryHelloIqProtocolEntity(linkCodePairingWrappedPrimaryEphemeralPub = linkCodePairingWrappedPrimaryEphemeralPub,primaryIdentityPub=self.db.identity.publicKey.serialize()[1:],linkCodePairingRef=self.companionHelloEntity.linkCodePairingRef)
            self.toLower(entity)
            self.pairingStatus = "WAIT_PAIRINGFINISH"
            self.pairingCode=None
            return entity.getId()  

    
    def setDisappearing(self,cmdParams,options):
        if len(cmdParams)==1:
            disappearingTime = 86400
        else:
            disappearingTime = int(cmdParams[1]) * 86400

        attr = ProtocolAttributes(
            key=MessageKeyAttributes(
                id=None,
                from_me=True,
                remote_jid=Jid.normalize(cmdParams[0])                
            ),
            type=ProtocolAttributes.TYPE_EPHEMERAL_SETTING,
            ephemeral_expiration=disappearingTime,
            disappearing_mode=DisappearingModeAttributes(
                trigger=DisappearingModeAttributes.TRIGGER_CHAT_SETTING,
                initiatedByMe=True,
            ),
            timestamp_ms=int(time.time()*1000)
        )
        entity = ProtocolMessageProtocolEntity(protocol_attr=attr,
            message_meta_attributes=
            MessageMetaAttributes(id=self.bot.idType,recipient=Jid.normalize(cmdParams[0]),timestamp=int(time.time())))
        self.toLower(entity)
        return entity.getId()

    def generateAppStateSyncKeys(self,n):
        profile = self.getStack().getProp("profile")        
        keys = []
        for i in range(0,n):
            key = AppStateSyncKeyAttribute(
                key_id= AppStateSyncKeyIdAttribute(key_id=random.randint(10000,20000).to_bytes(6,'big')),
                key_data=AppStateSyncKeyDataAttribute(
                    key_data=Curve.generateKeyPair().publicKey.serialize()[1:],
                    fingerprint=AppStateSyncKeyFingerprintAttribute(
                       raw_id = random.randint(10000,2000000000),
                       current_index=i,
                       device_indexes=profile.config.device_list
                    ),
                    timestamp=int(time.time())
                )
            )
            keys.append(key)        
        return keys
              


    def integrityCheck(self,cmdParams,options):        

        def on_success(entity, original_iq_entity):   
            if isinstance(entity,WmexResultIqProtocolEntity):       
                self.setCmdResult(entity.getId(), entity.result_obj)

        def on_error(entity, original_iq):                        
            logger.info("integrityCheck error")        

        user_ids = cmdParams[0].split(",")        
        jids = []
        for id in user_ids:
            jids.append({"jid":Jid.normalize(id)})

        query=  {
            "variables":{         
                "input":{
                    "query_input":jids,
                    "telemetry":{
                        "context":"INTERACTIVE"
                    }                    
                }
            }
        }
        
        entity = WmexQueryIqProtocolEntity(query_name="BizIntegrityQuery",query_obj=query)            
        self._sendIq(entity, on_success, on_error)        

        return entity.getId()  