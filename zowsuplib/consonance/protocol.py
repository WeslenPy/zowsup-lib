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
        import threading
        thread_id = threading.current_thread().ident
        new_state = self._machine.state
        old_state = self._last_triggered_state
        
        if self._protocol_state_callbacks is not None and old_state != new_state:
            logger.info(f"[LOGIN-DEBUG] WANoiseProtocol._trigger_state_callback() - mudança de estado | thread_id={thread_id} old_state={old_state} new_state={new_state}")
            self._last_triggered_state = new_state
            # Limpa timer quando entra em TRANSPORT
            if new_state == self.STATE_TRANSPORT:
                elapsed = time.time() - self._handshake_start_time if self._handshake_start_time else None
                logger.info(f"[LOGIN-DEBUG] Entrando em estado TRANSPORT - handshake concluído | thread_id={thread_id} elapsed_time={elapsed:.2f}s" if elapsed else f"[LOGIN-DEBUG] Entrando em estado TRANSPORT - handshake concluído | thread_id={thread_id}")
                self._handshake_start_time = None
            elif new_state == self.STATE_HANDSHAKE:
                logger.info(f"[LOGIN-DEBUG] Entrando em estado HANDSHAKE | thread_id={thread_id}")
            elif new_state == self.STATE_ERROR:
                logger.error(f"[LOGIN-DEBUG] Entrando em estado ERROR | thread_id={thread_id}")
            elif new_state == self.STATE_INIT:
                logger.info(f"[LOGIN-DEBUG] Entrando em estado INIT | thread_id={thread_id}")
            
            logger.info(f"[LOGIN-DEBUG] Chamando protocol_state_callbacks com novo estado | thread_id={thread_id} state={new_state}")
            self._protocol_state_callbacks(new_state)

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
        import threading
        thread_id = threading.current_thread().ident
        
        logger.info(f"[LOGIN-DEBUG] WANoiseProtocol.start() chamado | thread_id={thread_id} mode={mode} deviceid={deviceid} rs={'present' if rs else 'none'}")
        logger.info(f"[LOGIN-DEBUG] client_config: username={client_config.username if client_config.username else 'None'} passive={client_config.passive} short_connect={client_config.short_connect} | thread_id={thread_id}")
        logger.info(f"[LOGIN-DEBUG] Mudando estado de INIT para HANDSHAKE | thread_id={thread_id}")
        self._machine.start()
        # Registrar tempo de início do handshake
        self._handshake_start_time = time.time()
        logger.info(f"[LOGIN-DEBUG] Estado mudou para HANDSHAKE, criando WAHandshake | thread_id={thread_id} version={self._version_major}.{self._version_minor}")
        handshake = WAHandshake(self._version_major, self._version_minor)
        if mode is not None:
            logger.info(f"[LOGIN-DEBUG] Configurando handshake mode={mode} | thread_id={thread_id}")
            handshake.setmode(mode)            
        if identity is not None:
            logger.info(f"[LOGIN-DEBUG] Configurando identity key | thread_id={thread_id}")
            handshake.setIdentity(identity)
        if regid is not None:
            logger.info(f"[LOGIN-DEBUG] Configurando registration ID | thread_id={thread_id}")
            handshake.setRegistrationId(regid)
        if signedprekey is not None:
            logger.info(f"[LOGIN-DEBUG] Configurando signed prekey | thread_id={thread_id}")
            handshake.setSignedPreKey(signedprekey)            
        if deviceid is not None:
            logger.info(f"[LOGIN-DEBUG] Configurando device ID={deviceid} | thread_id={thread_id}")
            handshake.setDeviceId(deviceid)
        
        logger.info(f"[LOGIN-DEBUG] Iniciando handshake.perform() | thread_id={thread_id} handshake_type={'IK' if rs else 'XX'}")
        try:                                       
            result = handshake.perform(client_config, stream, s, rs)
            if result is not None:
                logger.info(f"[LOGIN-DEBUG] handshake.perform() retornou com sucesso, obtendo cipherstates | thread_id={thread_id}")
                self._rs = handshake.rs
                logger.info(f"[LOGIN-DEBUG] Criando WANoiseTransport com cipherstates | thread_id={thread_id}")
                self._transport = WANoiseTransport(stream, result[0], result[1])
                logger.info(f"[LOGIN-DEBUG] Mudando estado de HANDSHAKE para TRANSPORT | thread_id={thread_id}")
                self._machine.finish()
                # Limpa timer quando handshake completa com sucesso
                self._handshake_start_time = None
                logger.info(f"[LOGIN-DEBUG] Handshake concluído com sucesso, protocolo em estado TRANSPORT | thread_id={thread_id}")
            else:
                logger.error(f"[LOGIN-DEBUG] handshake.perform() retornou None - sem cipherstates | thread_id={thread_id}")
                raise HandshakeFailedException("No cipherstates")
        except HandshakeFailedException as e:
            logger.error(f"[LOGIN-DEBUG] HandshakeFailedException durante handshake.perform() | thread_id={thread_id} error={e}")
            logger.info(f"[LOGIN-DEBUG] Mudando estado para ERROR devido a falha no handshake | thread_id={thread_id}")
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



