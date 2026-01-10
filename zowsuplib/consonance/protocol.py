from .config.client import ClientConfig
from .handshake import WAHandshake
from .streams.segmented.segmented import SegmentedStream
from .transport import WANoiseTransport
from .exceptions.handshake_failed_exception import HandshakeFailedException
import logging
import time
from transitions import Machine
import base64
from loguru import logger

class WANoiseProtocol(object):
    STATE_INIT = 'init'
    STATE_HANDSHAKE = 'handshake'
    STATE_TRANSPORT = 'transport'
    STATE_ERROR = 'error'
    STATES = [
        STATE_INIT,
        STATE_HANDSHAKE,
        STATE_TRANSPORT,
        STATE_ERROR
    ]
    TRANSITIONS = [
        ['start', STATE_INIT, STATE_HANDSHAKE],
        ['finish', STATE_INIT, STATE_ERROR],
        ['finish', STATE_HANDSHAKE, STATE_TRANSPORT],
        ['fail', STATE_HANDSHAKE, STATE_ERROR],
        ['fail', STATE_TRANSPORT, STATE_ERROR],
        ['reset', STATE_INIT, '='],
        ['reset', STATE_TRANSPORT, STATE_INIT],
        ['reset', STATE_HANDSHAKE, STATE_INIT],
        ['reset', 'error', STATE_INIT],
        ['send', STATE_TRANSPORT, '='],
        ['receive', STATE_TRANSPORT, '='],
        ['start', STATE_ERROR, STATE_HANDSHAKE]
    ]

    def __init__(self, version_major, version_minor, 
                    protocol_state_callbacks=None, recovery_callback=None):
        """
        :param version_major:
        :type version_major: int
        :param version_minor:
        :type version_minor: int
        :param protocol_state_callbacks:
        :type protocol_state_callbacks: callable
        :param recovery_callback:
        :type recovery_callback: callable
        """
        self._version_major = version_major
        self._version_minor = version_minor
        self._protocol_state_callbacks = protocol_state_callbacks
        self._recovery_callback = recovery_callback
        self._rs = None
        self._logger = logger
        self._machine = Machine(
            states=self.STATES,
            transitions=self.TRANSITIONS,
            initial='init',
            after_state_change=self._trigger_state_callback,
            # ignore_invalid_triggers=True,  # não lança em triggers fora de ordem
        )  # type: Machine

        self._transport = None # type: WANoiseTransport
        self._last_triggered_state = None
        # Rastreamento de tempo para detecção de estados congelados
        self._handshake_start_time = None
        self._last_send_attempt_time = None
        self._handshake_timeout = 60.0  # 60 segundos timeout

    def _trigger_state_callback(self):
        if self._protocol_state_callbacks is not None and self._last_triggered_state != self._machine.state:
            self._last_triggered_state = self._machine.state
            # Limpa timer quando entra em TRANSPORT
            if self._machine.state == self.STATE_TRANSPORT:
                self._handshake_start_time = None
            self._protocol_state_callbacks(self._machine.state)

    @property
    def state(self):
        return self._machine.state

    @property
    def rs(self):
        return self._rs

    def start(self, stream, client_config, s, rs=None, mode = None, identity=None,regid=None,signedprekey=None,deviceid=None):
        """
        :param stream
        :type stream: SegmentedStream
        :param client_config:
        :type client_config: ClientConfig
        :return:
        :rtype:
        :param s:
        :type s: consonance.structs.keypair.KeyPair
        :param rs:
        :type rs: consonance.structs.publickey.PublicKey
        """        
        self._machine.start()
        # Registrar tempo de início do handshake
        self._handshake_start_time = time.time()
        handshake = WAHandshake(self._version_major, self._version_minor)
        if mode is not None:            
            handshake.setmode(mode)            
        if identity is not None:
            handshake.setIdentity(identity)
        if regid is not None:
            handshake.setRegistrationId(regid)
        if signedprekey is not None:
            handshake.setSignedPreKey(signedprekey)            
        if deviceid is not None:
            handshake.setDeviceId(deviceid)
        
        try:                                       
            result = handshake.perform(client_config, stream, s, rs)
            if result is not None:
                self._rs = handshake.rs
                self._transport = WANoiseTransport(stream, result[0], result[1])
                self._machine.finish()
                # Limpa timer quando handshake completa com sucesso
                self._handshake_start_time = None
            else:
                raise HandshakeFailedException("No cipherstates")
        except HandshakeFailedException as e:
            self._machine.fail()
            # Mantém o timer para detecção de erro persistente
            raise

    def reset(self):
        self._machine.reset()
        self._transport = None
        # Limpa timers ao resetar
        self._handshake_start_time = None
        self._last_send_attempt_time = None

    def send(self, data, recovery_callback=None):
        """
        :param data:
        :type data: bytes
        :param recovery_callback:
        :type recovery_callback: callable
        :return:
        :rtype:
        """        
        current_state = self._machine.state
        
        # Se não estiver em transporte, verifica se está congelado
        if current_state != self.STATE_TRANSPORT:
            current_time = time.time()
            self._last_send_attempt_time = current_time
            
            # Detecção de estado congelado
            should_recover = False
            recovery_reason = None
            
            if current_state == self.STATE_ERROR:
                # Estado ERROR indica que precisa de recuperação
                should_recover = True
                recovery_reason = "protocolo em estado ERROR"
            elif current_state == self.STATE_HANDSHAKE:
                # Se está em handshake há muito tempo, pode estar preso
                if self._handshake_start_time is not None:
                    elapsed = current_time - self._handshake_start_time
                    if elapsed > self._handshake_timeout:
                        should_recover = True
                        recovery_reason = f"handshake preso há {elapsed:.1f}s (timeout {self._handshake_timeout}s)"
            
            if should_recover:
                self._logger.warning(
                    f"send() ignorado: estado={current_state} (aguardando handshake) - "
                    f"Detectado estado congelado: {recovery_reason}"
                )
                # Chama callback de recuperação se disponível
                callback = recovery_callback or self._recovery_callback
                if callback:
                    try:
                        callback(recovery_reason)
                    except Exception as e:
                        self._logger.error(f"Erro ao chamar recovery_callback: {e}")
                return
            else:
                self._logger.warning("send() ignorado: estado=%s (aguardando handshake)", current_state)
                return

        try:
            self._machine.send()
            self._transport.send(data)
            # Limpa timer de última tentativa ao enviar com sucesso
            self._last_send_attempt_time = None
        except Exception as exc:  # pragma: no cover - defensivo
            self._logger.error("Erro ao enviar no transporte: %s", exc)

    def receive(self):
        """
        :param datastream
        :type SegmentedDataStream
        :return:
        :rtype: bytes
        """
        # Só recebe se já estiver em transporte; evita MachineError por estado inválido
        if self._machine.state != self.STATE_TRANSPORT:
            self._logger.debug("receive() ignorado: estado=%s (aguardando handshake)", self._machine.state)
            return None

        self._machine.receive()
        return self._transport.recv()



