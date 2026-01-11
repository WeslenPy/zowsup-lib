from ....layers.network.dispatcher.dispatcher import YowConnectionDispatcher
from ....common import asyncore
import logging
import socket
import traceback
import time

from loguru import logger


class AsyncoreConnectionDispatcher(YowConnectionDispatcher, asyncore.dispatcher_with_send):
    def __init__(self, connectionCallbacks):         
        super(AsyncoreConnectionDispatcher, self).__init__(connectionCallbacks)
        self.socket_map = {}
        asyncore.dispatcher_with_send.__init__(self,map=self.socket_map)
        self._connected = False
        self._networkEnv = connectionCallbacks.getStack().getProp("env").networkEnv

    def sendData(self, data):
        if self._connected:                                           
            self.out_buffer = self.out_buffer + data                        
            self.initiate_send()
        else:
            logger.warning(f"Attempted to send {len(data)} bytes while still not connected")

    def connect(self, host):
        import threading
        account_id = self.connectionCallbacks.getStack().getProp("botId") or self.connectionCallbacks.getStack().getProp("jid") or "unknown"
        thread_id = threading.current_thread().ident
        
        logger.info(f"[PROXY] [account={account_id}] Iniciando conexão | destino={host} | thread_id={thread_id}")
        logger.debug(f"connect({str(host)})")
        self.connectionCallbacks.onConnecting()
        
        proxy = None        
        if self._networkEnv.type!="direct":
            proxy_host = getattr(self._networkEnv, 'host', None)
            proxy_port = getattr(self._networkEnv, 'port', None)
            proxy_user = getattr(self._networkEnv, 'username', None)
            proxy_pass = getattr(self._networkEnv, 'password', None)
            
            logger.info(f"[PROXY] [account={account_id}] ✅ PROXY ATIVO | Proxy: {proxy_host}:{proxy_port} | Auth: {'Sim' if proxy_user else 'Não'}")
            logger.info(f"[PROXY] [account={account_id}] Conectando via proxy {proxy_host}:{proxy_port} para destino {host}")
            
            proxy = {
                "host": proxy_host,
                "port": proxy_port,
                "username": proxy_user,
                "password": proxy_pass,
                "rdns":True
            }
        else:
            logger.info(f"[PROXY] [account={account_id}] ❌ PROXY INATIVO - Conexão direta (sem proxy)")
            logger.debug("no proxy set, direct network")

        logger.info(f"[PROXY] [account={account_id}] Criando socket | tipo={'COM PROXY' if proxy else 'DIRETO'} | destino={host}")
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM,proxy)        
        asyncore.dispatcher_with_send.connect(self, host)        
        asyncore.loop(timeout=1,map=self.socket_map)           
        

    def handle_connect(self):
        import threading
        account_id = self.connectionCallbacks.getStack().getProp("botId") or self.connectionCallbacks.getStack().getProp("jid") or "unknown"
        thread_id = threading.current_thread().ident
        
        proxy_info = ""
        if self._networkEnv.type != "direct":
            proxy_host = getattr(self._networkEnv, 'host', None)
            proxy_port = getattr(self._networkEnv, 'port', None)
            proxy_info = f" via proxy {proxy_host}:{proxy_port}"
        
        logger.info(f"[PROXY] [account={account_id}] ✅ Conexão estabelecida{proxy_info} | thread_id={thread_id}")
        logger.debug("handle_connect")
        if not self._connected:
            self._connected = True            
            self.connectionCallbacks.onConnected()

    def handle_close(self):
        logger.debug("handle_close")
        self.close()        
        self.socket_map = None
        self._connected = False                
        self.connectionCallbacks.onDisconnected()

    def handle_error(self):
        print(traceback.format_exc())                
        self.handle_close()

    def handle_read(self):
        data = self.recv(1024)
        self.connectionCallbacks.onRecvData(data)

    def disconnect(self):                     
        self.handle_close()


