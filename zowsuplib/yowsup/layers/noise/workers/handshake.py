from zowsuplib.consonance.protocol import WANoiseProtocol
from zowsuplib.consonance.streams.segmented.segmented import SegmentedStream
from zowsuplib.consonance.exceptions.handshake_failed_exception import HandshakeFailedException
from zowsuplib.consonance.config.client import ClientConfig
from zowsuplib.consonance.structs.keypair import KeyPair
from zowsuplib.consonance.structs.publickey import PublicKey

import threading
import logging
import os

from loguru import logger


class WANoiseProtocolHandshakeWorker(threading.Thread):
    def __init__(self, wanoiseprotocol, stream, client_config, s, rs=None, finish_callback=None,mode=None,identity=None, regid=None, signedprekey=None,deviceid=None, attempt_id=None):
        """
        :param wanoiseprotocol:
        :type wanoiseprotocol: WANoiseProtocol
        :param stream:
        :type stream: SegmentedStream
        :param client_config:
        :type client_config: ClientConfig
        :param s:
        :type s: KeyPair
        :param rs:
        :type rs: PublicKey | None
        """
        super(WANoiseProtocolHandshakeWorker, self).__init__()
        self.daemon = True

        self._protocol = wanoiseprotocol # type: WANoiseProtocol
        self._stream = stream # type: SegmentedStream
        self._client_config = client_config # type: ClientConfig
        self._s = s # type: KeyPair
        self._rs = rs # type: PublicKey
        self._finish_callback = finish_callback
        self._attempt_id = attempt_id

        self._mode = mode
        self._identity = identity
        self._regid = regid
        self._signedprekey = signedprekey    
        self._deviceid = deviceid    
        self.name = f"handshake_{attempt_id}"

    def run(self):
        import threading
        import traceback
        thread_id = threading.current_thread().ident
        logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] worker.run() iniciado | thread_id={thread_id} worker_thread={self.ident}")
        self._protocol.reset()
        error = None
        logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] worker starting | thread_id={thread_id} mode={self._mode} deviceid={self._deviceid} rs={'present' if self._rs else 'none'} protocol={id(self._protocol)} stream={id(self._stream)}")
        logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] local_static keypair: {id(self._s) if self._s else None} remote_static publickey: {id(self._rs) if self._rs else None}")
        try:          
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] client_config username={self._client_config.username} mcc={self._client_config.useragent.mcc} mnc={self._client_config.useragent.mnc} passive={self._client_config.passive} short_connect={self._client_config.short_connect}")
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] chamando protocol.start() | thread_id={thread_id}")
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] protocol.start params: mode={self._mode} identity={self._identity is not None} regid={self._regid is not None} signedprekey={self._signedprekey is not None} deviceid={self._deviceid}")
            self._protocol.start(self._stream, self._client_config, self._s, self._rs,mode=self._mode,identity= self._identity,regid = self._regid,signedprekey = self._signedprekey,deviceid=self._deviceid)       
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] protocol.start returned without exception | thread_id={thread_id}")
            
        except HandshakeFailedException as e:
            error = e
            error_msg = str(e)
            is_cancelled = "cancelled" in error_msg.lower() or "Stream cancelled" in error_msg
            
            if is_cancelled:
                # Stream foi cancelado (provavelmente por desconexão) - não é um erro crítico
                logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] Handshake cancelled | thread_id={thread_id} error={error_msg}")
            else:
                # Erro real durante handshake
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] HandshakeFailedException capturada | thread_id={thread_id} error={e} error_type={type(e).__name__}")
                logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] HandshakeFailedException traceback:\n{traceback.format_exc()}")
                logger.error(f"[handshake {self._attempt_id}] handshake failed: {e}")
        except Exception as e:
            error = e
            logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] Exception inesperada capturada | thread_id={thread_id} error={e} error_type={type(e).__name__}")
            logger.error(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] Exception traceback:\n{traceback.format_exc()}")
            logger.exception(f"[handshake {self._attempt_id}] unexpected error during handshake")

        logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] worker.run() finalizando | thread_id={thread_id} error={error} finish_callback={'present' if self._finish_callback else 'none'}")
        if self._finish_callback is not None:
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] chamando finish_callback | thread_id={thread_id} error={error}")
            self._finish_callback(error)
            logger.info(f"[HANDSHAKE-DEBUG] [handshake {self._attempt_id}] finish_callback retornou | thread_id={thread_id}")


