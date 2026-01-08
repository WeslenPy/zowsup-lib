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
        logger.debug(f"connect({str(host)})")
        self.connectionCallbacks.onConnecting()
        
        proxy = None        
        if self._networkEnv.type!="direct":
            logger.debug(f"proxy set {self._networkEnv.host} {self._networkEnv.port} {self._networkEnv.username} {self._networkEnv.password}")
            proxy = {
                "host":self._networkEnv.host ,
                "port":self._networkEnv.port,
                "username":self._networkEnv.username,
                "password":self._networkEnv.password,
                "rdns":True
            }
        else:
            logger.debug("no proxy set, direct network")

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM,proxy)        
        
        try:
            asyncore.dispatcher_with_send.connect(self, host)
        except OSError as e:
            # Em Windows, connect_ex pode retornar erro 10060 (timeout) imediatamente
            # mesmo em modo não-bloqueante. Neste caso, precisamos tratar como EINPROGRESS
            # e permitir que o loop processe a conexão de forma assíncrona.
            import os
            from zowsuplib.yowsup.common.asyncore import EINPROGRESS, EALREADY, EWOULDBLOCK, EINVAL
            
            err = e.errno if hasattr(e, 'errno') else (e.args[0] if e.args else None)
            
            # WSAETIMEDOUT (10060) no Windows pode ocorrer imediatamente em sockets não-bloqueantes
            # quando a conexão não pode ser estabelecida rapidamente. Tratamos como EINPROGRESS.
            if err == 10060 and os.name == 'nt':
                # Timeout imediato no Windows - trata como conexão em progresso
                logger.debug(f"connect() retornou timeout (10060), tratando como conexão em progresso")
                self.connecting = True
                self.addr = host
                # Não fecha o socket, permite que o loop tente novamente
                return
            elif err in (EINPROGRESS, EALREADY, EWOULDBLOCK) or (err == EINVAL and os.name == 'nt'):
                # Erro esperado para conexão não-bloqueante, o loop processará
                logger.debug(f"connect() retornou {err}, conexão será processada assincronamente")
                return
            else:
                # Outro erro - relança a exceção
                logger.error(f"Erro de conexão não tratado: {e} (errno={err})")
                raise
        
        # NÃO chama asyncore.loop() bloqueante aqui
        # O StackLoopManager processará todos os socket_maps de forma não-bloqueante
        # Apenas inicia a conexão, o loop será processado pelo manager centralizado
        

    def handle_connect(self):
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


