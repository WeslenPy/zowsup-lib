from ...common import YowConstants
from ...layers import YowLayerEvent, YowProtocolLayer, EventCallback
from ...layers.network import YowNetworkLayer
from .protocolentities import *
from .layer_interface_authentication import YowAuthenticationProtocolLayerInterface
from .protocolentities import StreamErrorProtocolEntity
import logging

from loguru import logger


class YowAuthenticationProtocolLayer(YowProtocolLayer):
    EVENT_AUTHED  = "org.openwhatsapp.yowsup.event.auth.authed"
    EVENT_AUTH = "org.openwhatsapp.yowsup.event.auth"
    PROP_CREDENTIALS = "org.openwhatsapp.yowsup.prop.auth.credentials"
    PROP_PASSIVE = "org.openwhatsapp.yowsup.prop.auth.passive"    

    def __init__(self):
        handleMap = {
            "stream:features": (self.handleStreamFeatures, None),
            "failure": (self.handleFailure, None),
            "success": (self.handleSuccess, None),
            #"w:p": (self.handleSuccess, None),
            "stream:error": (self.handleStreamError, None),            
        }
        super(YowAuthenticationProtocolLayer, self).__init__(handleMap)
        self.interface = YowAuthenticationProtocolLayerInterface(self)

    def __str__(self):
        return "Authentication Layer"

    @EventCallback(YowNetworkLayer.EVENT_STATE_CONNECTED)
    def on_connected(self, event):
        import threading
        thread_id = threading.current_thread().ident
        try:
            stack = self.getStack()
            account_id = stack.getProp("botId") or stack.getProp("jid") or "unknown" if stack else "unknown"
        except:
            account_id = "unknown"
        
        passive = self.getProp(self.PROP_PASSIVE, False)
        logger.info(f"[LOGIN-DEBUG] YowAuthenticationProtocolLayer.on_connected() chamado | account={account_id} thread_id={thread_id} passive={passive}")
        logger.info(f"[LOGIN-DEBUG] Emitindo EVENT_AUTH para iniciar handshake | account={account_id} thread_id={thread_id}")
        self.broadcastEvent(
            YowLayerEvent(
                self.EVENT_AUTH,
                passive=passive
            )
        )
        logger.info(f"[LOGIN-DEBUG] EVENT_AUTH emitido com sucesso | account={account_id} thread_id={thread_id}")
        

    def setCredentials(self, credentials):
        logger.warning("setCredentials is deprecated and has no effect, user stack.setProfile instead")

    def getUsername(self, full = False):
        username = self.getProp("profile").username
        return username if not full else ("%s@%s" % (username, YowConstants.WHATSAPP_SERVER))

    def handleStreamFeatures(self, node):
        import threading
        thread_id = threading.current_thread().ident
        try:
            stack = self.getStack()
            account_id = stack.getProp("botId") or stack.getProp("jid") or "unknown" if stack else "unknown"
        except:
            account_id = "unknown"
        
        logger.info(f"[LOGIN-DEBUG] handleStreamFeatures() chamado - recebido stream:features após handshake | account={account_id} thread_id={thread_id}")
        nodeEntity = StreamFeaturesProtocolEntity.fromProtocolTreeNode(node)
        logger.info(f"[LOGIN-DEBUG] StreamFeatures parseado, enviando para camadas superiores | account={account_id} thread_id={thread_id}")
        self.toUpper(nodeEntity)

    def handleSuccess(self, node):
        import threading
        thread_id = threading.current_thread().ident
        try:
            stack = self.getStack()
            account_id = stack.getProp("botId") or stack.getProp("jid") or "unknown" if stack else "unknown"
        except:
            account_id = "unknown"
        
        passive = self.getProp(self.__class__.PROP_PASSIVE)
        logger.info(f"[LOGIN-DEBUG] handleSuccess() chamado - recebido mensagem 'success' do servidor | account={account_id} thread_id={thread_id} passive={passive}")
        logger.info(f"[LOGIN-DEBUG] Emitindo EVENT_AUTHED para indicar autenticação bem-sucedida | account={account_id} thread_id={thread_id}")
        successEvent = YowLayerEvent(self.__class__.EVENT_AUTHED, passive=passive)
        self.broadcastEvent(successEvent)
        logger.info(f"[LOGIN-DEBUG] EVENT_AUTHED emitido, parseando SuccessProtocolEntity | account={account_id} thread_id={thread_id}")
        nodeEntity = SuccessProtocolEntity.fromProtocolTreeNode(node)
        logger.info(f"[LOGIN-DEBUG] SuccessProtocolEntity parseado, enviando para camadas superiores | account={account_id} thread_id={thread_id}")
        self.toUpper(nodeEntity)
        logger.info(f"[LOGIN-DEBUG] handleSuccess() concluído - login autenticado com sucesso | account={account_id} thread_id={thread_id}")

    def handleFailure(self, node):
        import threading
        thread_id = threading.current_thread().ident
        try:
            stack = self.getStack()
            account_id = stack.getProp("botId") or stack.getProp("jid") or "unknown" if stack else "unknown"
        except:
            account_id = "unknown"
        
        logger.error(f"[LOGIN-DEBUG] handleFailure() chamado - recebido mensagem 'failure' do servidor | account={account_id} thread_id={thread_id}")
        nodeEntity = FailureProtocolEntity.fromProtocolTreeNode(node)
        logger.error(f"[LOGIN-DEBUG] FailureProtocolEntity parseado, enviando para camadas superiores | account={account_id} thread_id={thread_id}")
        self.toUpper(nodeEntity)
        logger.error(f"[LOGIN-DEBUG] Emitindo EVENT_STATE_DISCONNECT devido a falha de autenticação | account={account_id} thread_id={thread_id}")
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT, reason="Authentication Failure"))
        logger.error(f"[LOGIN-DEBUG] handleFailure() concluído - login falhou | account={account_id} thread_id={thread_id}")

    def handleStreamError(self, node):
        nodeEntity = StreamErrorProtocolEntity.fromProtocolTreeNode(node)

        code = node.getAttributeValue("code")
        if code=="515":
            self.toUpper(nodeEntity)
            return

        
        errorType = nodeEntity.getErrorType()

        if not errorType and nodeEntity.code is None:
            raise NotImplementedError("Unhandled stream:error node:\n%s" % node)
                

        self.toUpper(nodeEntity)


