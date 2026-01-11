import time
import logging
from threading import Thread, Lock
from ...layers import YowProtocolLayer, YowLayerEvent, EventCallback
from ...common import YowConstants
from ...layers.axolotl.protocolentities.iq_keys_get_result import ResultGetKeysIqProtocolEntity
from ...layers.axolotl.protocolentities.iq_key_count_result import ResultKeyCountIqProtocolEntity 

from ...layers.protocol_profiles.protocolentities import *
from ...layers.protocol_groups.protocolentities import *
from ...layers.protocol_contacts.protocolentities import *
from ...layers.network import YowNetworkLayer
from ...layers.auth import YowAuthenticationProtocolLayer
from .protocolentities import *

from ...layers.protocol_media.protocolentities  import *
from ...layers.protocol_media.protocolentities.iq_requestmediaconn_result import ResultRequestMediaConnIqProtocolEntity
from loguru import logger

class YowIqProtocolLayer(YowProtocolLayer):
    
    PROP_PING_INTERVAL               = "org.openwhatsapp.yowsup.prop.pinginterval"
    PROP_PING_TIMEOUT                = "org.openwhatsapp.yowsup.prop.pingtimeout"
    
    def __init__(self):
        handleMap = {
            "iq": (self.recvIq, self.sendIq)
        }
        self._pingThread = None
        self._pingQueue = {}
        self._pingQueueLock = Lock()
        self._pingSysvarCtx = None
        self._pingAccountId = None
        self.__logger = logger
        super(YowIqProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Iq Layer"

    def onPong(self, protocolTreeNode, pingEntity):
        self.gotPong(pingEntity.getId())
        #self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(protocolTreeNode))

    def sendIq(self, entity):
        if entity.getXmlns() == "w:p":
            self._sendIq(entity, self.onPong)
        elif entity.getXmlns() in ("w:sync:app:state","privacy","urn:xmpp:whatsapp:push", "w", "w:b","urn:xmpp:whatsapp:account", "encrypt","w:biz","w:mex","urn:xmpp:whatsapp:dirty","md","w:account_defence") or entity.getXmlns() is None :                
            node =     entity.toProtocolTreeNode()    
            self.toLower(node)

    def recvIq(self, node):                    
        if node["xmlns"] == "urn:xmpp:ping":
            entity = PongResultIqProtocolEntity(YowConstants.DOMAIN, node["id"])
            self.toLower(entity.toProtocolTreeNode())


        if node["xmlns"] == "md" :
            if node.getChild("pair-device") is not None:
                #僚机配对，直接回复一个            
                #丢到应用层处理            
                self.toUpper(MultiDevicePairIqProtocolEntity.fromProtocolTreeNode(node))
                self.onAuthed(None)  #这里主要启动ping线程     
            if node.getChild("pair-success"):
                self.toUpper(MultiDevicePairSuccessIqProtocolEntity.fromProtocolTreeNode(node))

        if node["type"] == "error":
            self.toUpper(ErrorIqProtocolEntity.fromProtocolTreeNode(node))
                        

        if node["type"] == "result":
            # Processa pongs de ping (xmlns="w:p" e sem filhos)
            if node.getAttributeValue("xmlns") == "w:p" and not node.hasChildren():
                ping_id = node.getAttributeValue("id")
                if ping_id:
                    self.gotPong(ping_id)
                    self.__logger.debug(f"Pong processado para ping {ping_id}")
                return
            
            if not node.hasChildren():                
                self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("verified_name") is not None:                
                self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(node))                   
            elif node.getChild("media_conn") is not None:
                self.toUpper(ResultRequestMediaConnIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("cat") is not None:                
                self.toUpper(PushGetPnResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("list") is not None:
                self.toUpper(ResultGetKeysIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("usync") is not None:
                pass  #usync 相关的消息在protocol_contacts里面处理  
            elif node.getChild("companion-props") is not None:
                #配对返回僚机的jid，要处理                
                self.toUpper(MultiDevicePairDeviceResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("groups") is not None or node.getChild("group") is not None or node["from"].endswith("g.us"):
                pass  #group 相关的消息在protocol_groups里面处理
            elif node.getChild("account") is not None:                
                self.toUpper(AccountInfoResultIqProtocolEntity.fromProtocolTreeNode(node))    
            elif node.getChild("email") is not None:
                self.toUpper(EmailResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("verify_email") is not None:
                self.toUpper(VerifyEmailResultIqProtocolEntity.fromProtocolTreeNode(node))  
            elif node.getChild("device_logout") is not None:                
                self.toUpper(DeviceLogoutResultIqProtocolEntity.fromProtocolTreeNode(node))                 
            elif node.getChild("count") is not None:
                self.toUpper(ResultKeyCountIqProtocolEntity.fromProtocolTreeNode(node))      
            elif node.getChild("picture"):
                pic=node.getChild("picture")
                if pic.getAttributeValue("type"):
                    self.toUpper(ResultGetPictureIqProtocolEntity.fromProtocolTreeNode(node))
                else:                                  
                    self.toUpper(ResultSetPictureIqProtocolEntity.fromProtocolTreeNode(node))                
            elif node.getChild("result") is not None:
                self.toUpper(WmexResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("sync") is not None:
                # AppState Sync result
                from zowsuplib.yowsup.layers.protocol_iq.protocolentities.iq_app_sync_state_result import AppSyncStateResultIqProtocolEntity
                self.toUpper(AppSyncStateResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("status") is not None:
                # Status responses são processados pelo YowProfilesProtocolLayer
                # Passa o node para cima sem processar
                self.toUpper(node)
            else:
                #不知道是啥，打印出来                     
                self.__logger.info(node)
                                
    def gotPong(self, pingId):
        self._pingQueueLock.acquire()
        try:
            if pingId in self._pingQueue:
                del self._pingQueue[pingId]
                self.__logger.debug(f"Pong recebido para ping {pingId}, removido da fila. Fila restante: {len(self._pingQueue)}")
            else:
                self.__logger.warning(f"Pong recebido para ping {pingId} que não está na fila")
        finally:
            self._pingQueueLock.release()

    def waitPong(self, id):
        self._pingQueueLock.acquire()
        try:
            # Armazena timestamp do ping para detectar timeouts
            self._pingQueue[id] = time.time()
            pingQueueSize = len(self._pingQueue)
            
            # Verifica se há pings antigos não respondidos (mais de 60 segundos)
            current_time = time.time()
            old_pings = [pid for pid, timestamp in self._pingQueue.items() 
                        if timestamp and (current_time - timestamp) > 60]
            
            if old_pings:
                self.__logger.warning(f"Removendo {len(old_pings)} pings antigos não respondidos: {old_pings}")
                for pid in old_pings:
                    del self._pingQueue[pid]
                pingQueueSize = len(self._pingQueue)
            
            self.__logger.debug(f"ping queue size: {pingQueueSize} (ping {id} adicionado)")
            
            # Apenas desconecta se há 3 ou mais pings pendentes E pelo menos um está antigo
            if pingQueueSize >= 3 and old_pings:
                # Marca prop de timeout para camadas superiores reagirem
                try:
                    self.getStack().setProp(self.__class__.PROP_PING_TIMEOUT, True)
                except Exception:
                    pass
                self.__logger.warning(f"Ping timeout: {pingQueueSize} pings pendentes, {len(old_pings)} antigos. Desconectando stack")
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT, reason = "Ping Timeout"))
        finally:
            self._pingQueueLock.release()

    @EventCallback(YowAuthenticationProtocolLayer.EVENT_AUTHED)
    def onAuthed(self, event):        
        interval = self.getProp(self.__class__.PROP_PING_INTERVAL, 50)
        if interval <= 0:
            return
        # Sempre recria a thread de ping para garantir isolamento por conta/stack
        # e evitar reuso entre contas durante reconexões.
        self.stop_thread()
        self._pingQueue = {}
        # Tenta identificar a conta a partir das props do stack
        account_id = (
            self.getStack().getProp("botId")
            or self.getStack().getProp("jid")
            or "unknown"
        )
        self._pingAccountId = account_id
        self._pingThread = YowPingThread(
            self,
            interval,
            account_id=account_id,
            sysvar_context=None,
        )
        self.__logger.debug(f"starting ping thread for {account_id} (interval={interval}s).")
        self._pingThread.start()
    
    
    def stop_thread(self):
        if self._pingThread:
            self.__logger.debug("stopping ping thread")
            if self._pingThread:
                self._pingThread.stop()
                self._pingThread = None
            self._pingQueue = {}
            
        
    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECT)
    def onDisconnect(self, event):                
        self.stop_thread()
    
    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onDisconnected(self, event):                
        self.stop_thread()
            
class YowPingThread(Thread):
    def __init__(self, layer, interval, *, account_id="unknown", sysvar_context=None):
        assert type(layer) is YowIqProtocolLayer, "layer must be a YowIqProtocolLayer, got %s instead." % type(layer)
        self._layer = layer
        self._interval = interval
        self._stop = False
        self._account_id = account_id
        self.__logger = logger
        super(YowPingThread, self).__init__()
        self.daemon = True
        # Nome da thread deixa claro qual conta está sendo monitorada
        self.name = f"YowPing-{account_id}"

    def run(self):
        while not self._stop:
            for i in range(0, self._interval):                
                time.sleep(1)                
                if self._stop:
                    self.__logger.debug(f"{self.name} - ping thread stopped")
                    return
            ping = PingIqProtocolEntity()
            self._layer.waitPong(ping.getId())
            if not self._stop:
                self._layer.sendIq(ping)

    def stop(self):
        self._stop = True


