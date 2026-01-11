from ...layers import YowLayer, YowLayerEvent, EventCallback
from ...layers.network.layer_interface import YowNetworkLayerInterface
from ...layers.network.dispatcher.dispatcher import ConnectionCallbacks
from ...layers.network.dispatcher.dispatcher import YowConnectionDispatcher
from ...layers.network.dispatcher.dispatcher_socket import SocketConnectionDispatcher
from ...layers.network.dispatcher.dispatcher_asyncore import AsyncoreConnectionDispatcher
import logging

from loguru import logger

class YowNetworkLayer(YowLayer, ConnectionCallbacks):
    """This layer wraps a connection dispatcher that provides connection and a communication channel
    to remote endpoints. Unless explicitly configured, applications should not make assumption about
    the dispatcher being used as the default dispatcher could be changed across versions"""
    EVENT_STATE_CONNECT         = "org.openwhatsapp.yowsup.event.network.connect"
    EVENT_STATE_DISCONNECT      = "org.openwhatsapp.yowsup.event.network.disconnect"
    EVENT_STATE_CONNECTED       = "org.openwhatsapp.yowsup.event.network.connected"
    EVENT_STATE_DISCONNECTED    = "org.openwhatsapp.yowsup.event.network.disconnected"

    PROP_ENDPOINT               = "org.openwhatsapp.yowsup.prop.endpoint"
    PROP_NET_READSIZE           = "org.openwhatsapp.yowsup.prop.net.readSize"
    PROP_DISPATCHER             = "org.openwhatsapp.yowsup.prop.net.dispatcher"

    STATE_DISCONNECTED          = 0
    STATE_CONNECTING            = 1
    STATE_CONNECTED             = 2
    STATE_DISCONNECTING         = 3

    DISPATCHER_SOCKET = 0
    DISPATCHER_ASYNCORE = 1
    DISPATCHER_DEFAULT = DISPATCHER_ASYNCORE

    def __init__(self):
        self.state = self.__class__.STATE_DISCONNECTED
        YowLayer.__init__(self)
        ConnectionCallbacks.__init__(self)
        self.interface = YowNetworkLayerInterface(self)
        self.connected = False
        self._dispatcher = None  # type: YowConnectionDispatcher
        self._disconnect_reason = None

    def __create_dispatcher(self, dispatcher_type):
        if dispatcher_type == self.DISPATCHER_ASYNCORE:
            logger.debug("Created asyncore dispatcher")
            return AsyncoreConnectionDispatcher(self)
        else:
            logger.debug("Created socket dispatcher")
            return SocketConnectionDispatcher(self)

    def onConnected(self):
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        endpoint = self.getProp(self.__class__.PROP_ENDPOINT)
        logger.info(f"[HANDSHAKE-DEBUG] onConnected | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} endpoint={endpoint}")
        logger.debug("Connected")
        self.state = self.__class__.STATE_CONNECTED
        self.connected = True
        logger.info(f"[HANDSHAKE-DEBUG] onConnected emitindo EVENT_STATE_CONNECTED | account={account_id} thread_id={thread_id}")
        self.emitEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECTED))

    def onDisconnected(self):
        import threading
        import inspect
        import os
        
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        stack_id = id(self.getStack())
        
        # Identifica quem chamou este método
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_info = "unknown"
        caller_file = "unknown"
        caller_line = 0
        
        if caller_frame:
            caller_file = caller_frame.f_code.co_filename
            caller_line = caller_frame.f_lineno
            caller_name = caller_frame.f_code.co_name
            
            # Extrai apenas o nome do arquivo (sem path completo)
            caller_file = os.path.basename(caller_file)
            caller_info = f"{caller_file}:{caller_line} ({caller_name})"
        
        # Tenta identificar o tipo de dispatcher
        dispatcher_type = "unknown"
        if self._dispatcher:
            dispatcher_type = type(self._dispatcher).__name__
        
        # Log detalhado com informações do caller
        logger.info(
            f"[NETWORK-DEBUG] onDisconnected chamado | "
            f"account={account_id} "
            f"thread_id={thread_id} "
            f"stack_id={stack_id} "
            f"caller={caller_info} "
            f"dispatcher={dispatcher_type} "
            f"previous_state={self.state} "
            f"reason={self._disconnect_reason or 'none'}"
        )
        
        if self.state != self.__class__.STATE_DISCONNECTED:
            self.state = self.__class__.STATE_DISCONNECTED
            self.connected = False
            logger.debug("Disconnected")
            self.emitEvent(
                YowLayerEvent(
                    self.__class__.EVENT_STATE_DISCONNECTED, reason=self._disconnect_reason or "", detached=True
                )
            )
        else:
            logger.debug(
                f"[NETWORK-DEBUG] onDisconnected ignorado (já estava desconectado) | "
                f"account={account_id} thread_id={thread_id}"
            )

    def onConnecting(self):
        pass

    def onConnectionError(self, error):
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        
        logger.info(
            f"[NETWORK-DEBUG] onConnectionError chamado | "
            f"account={account_id} thread_id={thread_id} error={error}"
        )
        self.onDisconnected()

    @EventCallback(EVENT_STATE_CONNECT)
    def onConnectLayerEvent(self, ev):
        if not self.connected:
            self.createConnection()
        else:
            logger.warning("Received connect event while already connected")
        return True

    @EventCallback(EVENT_STATE_DISCONNECT)
    def onDisconnectLayerEvent(self, ev):
        self.destroyConnection(ev.getArg("reason"))
        return True

    def createConnection(self):
        import threading
        thread_id = threading.current_thread().ident
        account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
        logger.info(f"[HANDSHAKE-DEBUG] createConnection iniciado | account={account_id} thread_id={thread_id} stack_id={id(self.getStack())} current_state={self.state}")
        self._disconnect_reason = None
        self._dispatcher = self.__create_dispatcher(self.getProp(self.PROP_DISPATCHER, self.DISPATCHER_DEFAULT))
        logger.info(f"[HANDSHAKE-DEBUG] createConnection dispatcher criado | account={account_id} thread_id={thread_id} dispatcher={id(self._dispatcher)}")
        self.state = self.__class__.STATE_CONNECTING
        endpoint = self.getProp(self.__class__.PROP_ENDPOINT)
        logger.info(f"[HANDSHAKE-DEBUG] createConnection conectando | account={account_id} thread_id={thread_id} endpoint={endpoint[0]}:{endpoint[1]}")
        logger.info(f"Connecting to {endpoint[0]}:{endpoint[1]}")    

        self._dispatcher.connect(endpoint)
        logger.info(f"[HANDSHAKE-DEBUG] createConnection connect() chamado | account={account_id} thread_id={thread_id}")

    def destroyConnection(self, reason=None):
        self._disconnect_reason = reason
        self.state = self.__class__.STATE_DISCONNECTING
        self._dispatcher.disconnect()

    def getStatus(self):
        return self.connected

    def send(self, data):
        if self.connected:
            self._dispatcher.sendData(data)

    def onRecvData(self, data):
        self.receive(data)

    def receive(self, data):
        self.toUpper(data)

    def __str__(self):
        return "Network Layer"


