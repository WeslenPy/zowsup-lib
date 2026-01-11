from ....layers.network.dispatcher.dispatcher import YowConnectionDispatcher
import socket
import logging

from loguru import logger


class SocketConnectionDispatcher(YowConnectionDispatcher):
    def __init__(self, connectionCallbacks):
        super(SocketConnectionDispatcher, self).__init__(connectionCallbacks)
        self.socket = None

    def connect(self, host):
        if not self.socket:
            self.socket = socket.socket()
            self.connectAndLoop(host)
        else:
            logger.error("Already connected?")

    def disconnect(self):
        import threading
        thread_id = threading.current_thread().ident
        account_id = "unknown"
        if hasattr(self.connectionCallbacks, 'getStack'):
            stack = self.connectionCallbacks.getStack()
            if stack:
                account_id = stack.getProp("botId") or stack.getProp("jid") or "unknown"
        
        logger.info(
            f"[NETWORK-DEBUG] SocketDispatcher.disconnect chamado | "
            f"account={account_id} thread_id={thread_id}"
        )
        
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_WR)
                self.socket.close()
            except socket.error as e:
                logger.error(e)
                self.socket = None
                self.connectionCallbacks.onDisconnected()
        else:
            logger.error("Not connected?")

    def connectAndLoop(self, host):
        import threading
        thread_id = threading.current_thread().ident
        account_id = "unknown"
        if hasattr(self.connectionCallbacks, 'getStack'):
            stack = self.connectionCallbacks.getStack()
            if stack:
                account_id = stack.getProp("botId") or stack.getProp("jid") or "unknown"
        
        socket = self.socket
        self.connectionCallbacks.onConnecting()
        try:
            socket.connect(host)
            self.connectionCallbacks.onConnected()
            while True:
                data = socket.recv(1024)
                if len(data):
                    self.connectionCallbacks.onRecvData(data)
                else:
                    logger.info(
                        f"[NETWORK-DEBUG] SocketDispatcher.connectAndLoop: recv() retornou 0 bytes | "
                        f"account={account_id} thread_id={thread_id}"
                    )
                    break
            self.connectionCallbacks.onDisconnected()
        except Exception as e:
            logger.error(
                f"[NETWORK-DEBUG] SocketDispatcher.connectAndLoop: exceção | "
                f"account={account_id} thread_id={thread_id} error={e}"
            )
            self.connectionCallbacks.onConnectionError(e)
        finally:
            self.socket = None
            socket.close()

    def sendData(self, data):
        try:
            self.socket.send(data)
        except socket.error as e:
            logger.error(e)
            self.disconnect()


