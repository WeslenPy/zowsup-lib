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
    
    def __init__(self):
        handleMap = {
            "iq": (self.recvIq, self.sendIq)
        }
        self._pingThread = None
        self._pingQueue = {}
        self._pingQueueLock = Lock()
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
            else:
                #不知道是啥，打印出来                     
                self.__logger.info(node)
                                
    def gotPong(self, pingId):
        self._pingQueueLock.acquire()
        if pingId in self._pingQueue:
            self._pingQueue = {}
        self._pingQueueLock.release()

    def waitPong(self, id):
        self._pingQueueLock.acquire()
        self._pingQueue[id] = None
        pingQueueSize = len(self._pingQueue)
        self._pingQueueLock.release()
        self.__logger.debug(f"ping queue size: {pingQueueSize}")
        if pingQueueSize >= 3:
            self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT, reason = "Ping Timeout"))

    @EventCallback(YowAuthenticationProtocolLayer.EVENT_AUTHED)
    def onAuthed(self, event):        
        interval = self.getProp(self.__class__.PROP_PING_INTERVAL, 50)
        if not self._pingThread and interval > 0:
            self._pingQueue = {}
            self._pingThread = YowPingThread(self, interval)
            self.__logger.debug("starting ping thread.")
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
    def __init__(self, layer, interval):
        assert type(layer) is YowIqProtocolLayer, "layer must be a YowIqProtocolLayer, got %s instead." % type(layer)
        self._layer = layer
        self._interval = interval
        self._stop = False
        self.__logger = logging.getLogger(__name__)
        super(YowPingThread, self).__init__()
        self.daemon = True
        self.name = "YowPing%s" % self.name

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
