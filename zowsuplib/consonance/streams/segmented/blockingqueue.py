from .segmented import SegmentedStream
import threading

try:
    import Queue
except ImportError:
    import queue as Queue

# Import exception for cancellation
from zowsuplib.consonance.exceptions.handshake_failed_exception import HandshakeFailedException


class BlockingQueueSegmentedStream(SegmentedStream):

    EVENT_READ  = 1
    EVENT_WRITE = 2
    
    # Poison pill value to signal cancellation
    _POISON_PILL = None

    def __init__(self):
        self._readqueue = Queue.Queue()
        self._writequeue = Queue.Queue()
        self._events_callback = None
        self._cancelled = False
        self._lock = threading.Lock()

    def set_events_callback(self, events_callback):
        self._events_callback = events_callback

    def remove_events_callback(self):
        self._events_callback = None

    def cancel(self):
        """
        Cancela operações pendentes no stream.
        Desbloqueia qualquer thread bloqueada em read_segment() ou get_write_segment().
        """
        with self._lock:
            if self._cancelled:
                return  # Já cancelado
            
            self._cancelled = True
            
            # Enviar poison pill para desbloquear read_segment()
            try:
                self._readqueue.put(self._POISON_PILL, block=False)
            except:
                pass
            
            # Enviar poison pill para desbloquear get_write_segment()
            try:
                self._writequeue.put(self._POISON_PILL, block=False)
            except:
                pass

    def is_cancelled(self):
        """Verifica se o stream foi cancelado."""
        with self._lock:
            return self._cancelled

    def put_read_segment(self, data):
        """
        :param data:
        :type data: bytes
        :return:
        :rtype:
        """
        if self._cancelled:
            return  # Ignorar dados se cancelado
        
        try:
            self._readqueue.put(data, block=False)
        except Queue.Full:
            pass  # Queue cheia, ignorar

    def get_write_segment(self):
        """
        :return:
        :rtype: bytes
        """
        # NÃO chamar callback aqui - isso causa recursão infinita!
        # O callback é chamado em write_segment() quando dados são colocados na queue.
        # Este método apenas retira dados da queue.
        
        data = self._writequeue.get(block=True)
        
        # Verificar se recebeu poison pill
        if data is self._POISON_PILL or self._cancelled:
            raise HandshakeFailedException("Stream cancelled during write operation")
        
        return data

    def read_segment(self):
        """
        Lê um segmento do stream.
        
        :return: bytes
        :raises HandshakeFailedException: Se o stream foi cancelado
        """
        # Verificar cancelamento antes de bloquear
        if self._cancelled:
            raise HandshakeFailedException("Stream cancelled")
        
        if self._events_callback is not None:
            self._events_callback(self.EVENT_READ)

        data = self._readqueue.get(block=True)
        
        # Verificar se recebeu poison pill ou se foi cancelado durante a espera
        if data is self._POISON_PILL or self._cancelled:
            raise HandshakeFailedException("Stream cancelled during read operation")
        
        return data

    def write_segment(self, data):
        if self._cancelled:
            return  # Ignorar escrita se cancelado
        
        self._writequeue.put(data)

        if self._events_callback is not None:
            self._events_callback(self.EVENT_WRITE)



