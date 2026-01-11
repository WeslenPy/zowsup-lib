import random

from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.extras.processing.handshakestate_guarded import GuardedHandshakeState
from dissononce.extras.processing.handshakestate_switchable import SwitchableHandshakeState
from dissononce.processing.handshakepatterns.handshakepattern import HandshakePattern
from dissononce.processing.handshakepatterns.interactive.IK import IKHandshakePattern
from dissononce.processing.handshakepatterns.interactive.XX import XXHandshakePattern
from dissononce.processing.modifiers.fallback import FallbackPatternModifier
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.aesgcm import AESGCMCipher
from dissononce.hash.sha256 import SHA256Hash
from dissononce.dh.keypair import KeyPair
from dissononce.dh.x25519.public import PublicKey
from dissononce.dh.private import PrivateKey
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.extras.dh.dangerous.dh_nogen import NoGenDH
from dissononce.exceptions.decrypt import DecryptFailedException
from google.protobuf.message import DecodeError

from .dissononce_extras.processing.symmetricstate_wa import WASymmetricState
from .proto import wa5_pb2
from .streams.segmented.segmented import SegmentedStream
from .certman.certman import CertMan
from .exceptions.new_rs_exception import NewRemoteStaticException
from .config.client import ClientConfig
from .structs.publickey import PublicKey
from .util.byte import ByteUtil
from.exceptions.handshake_failed_exception import HandshakeFailedException
import struct,binascii
import base64,hashlib,logging
from loguru import logger

class WAHandshake(object):
    def __init__(self, version_major, version_minor):
        self._prologue = b"WA" + bytearray([version_major, version_minor])
        self._handshakestate = None  # type: HandshakeState | None
        self.mode = None
        self.identity = None
        self.regid = None
        self.signedprekey = None
        self.deviceid = None
    
    def setmode(self,mode):
        self.mode = mode
        
    def getIdentity(self):
        return self.identity

    def getSignedPreKey(self):
        return self.signedprekey

    def getRegistrationId(self):
        return self.regid

    def setIdentity(self,value):
        self.identity = value

    def setSignedPreKey(self,value):
        self.signedprekey = value

    def setRegistrationId(self,value):
        self.regid = value

    def setDeviceId(self,value):
        self.deviceid = value


    def perform(self, client_config, stream, s, rs=None, e=None):
        """
        :param client_config:
        :type client_config:
        :param stream:
        :type stream:
        :param s:
        :type s: consonance.structs.keypair.KeyPair
        :param rs:
        :type rs: consonance.structs.publickey.PublicKey | None
        :type e: consonance.structs.keypair.KeyPair | None
        :return:
        :rtype:
        """
        import threading
        thread_id = threading.current_thread().ident
        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() chamado | thread_id={thread_id} stream={id(stream)} s={id(s) if s else None} rs={id(rs) if rs else None} e={id(e) if e else None}")
        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() client_config: username={client_config.username} platform={client_config.useragent.platform} app_version={client_config.useragent.app_version}")
        logger.debug(f"perform(client_config={client_config}, stream={stream}, s={s}, rs={rs}, e={e})")
        dh = X25519DH()
        if e is not None:
            dh = NoGenDH(dh, PrivateKey(e.private.data))
        
        self._handshakestate = SwitchableHandshakeState(
            GuardedHandshakeState(
                HandshakeState(
                    WASymmetricState(
                        CipherState(
                            AESGCMCipher()
                        ),
                        SHA256Hash()
                    ),
                    dh
                )
            )
        )  # type: SwitchableHandshakeState
        dissononce_s = KeyPair(
            PublicKey(s.public.data),
            PrivateKey(s.private.data)
        )
        dissononce_rs = PublicKey(rs.data) if rs else None
        client_payload = self._create_full_payload(client_config,s)

        #logger.debug("Create client_payload=%s" % client_payload)
        import threading
        thread_id = threading.current_thread().ident
        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() iniciando handshake | thread_id={thread_id} rs={'present' if rs is not None else 'none'}")
        try:
            if rs is not None:
                logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() usando handshake IK (rs presente) | thread_id={thread_id}")
                try:                    
                    cipherstatepair = self._start_handshake_ik(stream, client_payload, dissononce_s, dissononce_rs)
                    logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() _start_handshake_ik retornou com sucesso | thread_id={thread_id}")
                except NewRemoteStaticException as ex:
                    logger.warning(f"[HANDSHAKE-DEBUG] WAHandshake.perform() NewRemoteStaticException, fazendo fallback para XX | thread_id={thread_id} exception={ex}")
                    logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() Nova chave estática remota detectada no server_hello, será salva após handshake | thread_id={thread_id}")
                    cipherstatepair = self._switch_handshake_xxfallback(stream, dissononce_s, client_payload, ex.server_hello)
                    logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() _switch_handshake_xxfallback retornou com sucesso | thread_id={thread_id}")
                    # A nova chave estática remota (rs) estará disponível em self._handshakestate.rs após o fallback
                    if self._handshakestate.rs:
                        new_rs_hex = self._handshakestate.rs.data.hex()[:32] if self._handshakestate.rs.data else "N/A"
                        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() Nova chave estática remota obtida: {new_rs_hex}... | thread_id={thread_id}")
            else:
                logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() usando handshake XX (rs ausente) | thread_id={thread_id}")
                cipherstatepair = self._start_handshake_xx(stream, client_payload, dissononce_s)
                logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() _start_handshake_xx retornou com sucesso | thread_id={thread_id}")
            logger.info(f"[HANDSHAKE-DEBUG] WAHandshake.perform() handshake concluído com sucesso | thread_id={thread_id}")
            return cipherstatepair
        except DecryptFailedException as e:
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake.perform() DecryptFailedException | thread_id={thread_id} error={e}")
            logger.exception(e)
            raise HandshakeFailedException(e)
        except DecodeError as e:
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake.perform() DecodeError | thread_id={thread_id} error={e}")
            logger.exception(e)
            raise HandshakeFailedException(e)

    @property
    def rs(self):
        return PublicKey(self._handshakestate.rs.data) if self._handshakestate.rs else None

    def _switch_handshake_xxfallback(self, stream, s, client_payload, server_hello):
        """
        :param handshake_pattern:
        :type handshake_pattern: HandshakePattern
        :param stream:
        :type stream: SegmentedStream
        :param s:
        :type s: KeyPair
        :param e:
        :type e: KeyPair
        :param client_payload:
        :type client_payload:
        :param server_hello:
        :type server_hello:
        :return:
        :rtype: tuple(CipherState,CipherState)
        """        
        self._handshakestate.switch(
                handshake_pattern=FallbackPatternModifier().modify(XXHandshakePattern()),
                initiator=True,
                prologue=self._prologue,
                s=s
            )
        payload_buffer = bytearray()
        self._handshakestate.read_message(server_hello.ephemeral + server_hello.static + server_hello.payload, payload_buffer)
        certman = CertMan()
        if certman.is_valid(self._handshakestate.rs, bytes(payload_buffer)):
            logger.debug("cert is valid")
        else:
            logger.error("cert is not valid")
        message_buffer = bytearray()
        cipherpair = self._handshakestate.write_message(client_payload.SerializeToString(), message_buffer)
        static, payload = ByteUtil.split(bytes(message_buffer), 48, len(message_buffer) - 48)
        client_finish = wa5_pb2.HandshakeMessage.ClientFinish()
        client_finish.static = static
        client_finish.payload = payload
        outgoing_handshakemessage = wa5_pb2.HandshakeMessage()        
        outgoing_handshakemessage.client_finish.MergeFrom(client_finish)

        stream.write_segment(outgoing_handshakemessage.SerializeToString())

        return cipherpair        

    def _start_handshake_xx(self, stream, client_payload, s):
        """
        :param stream:
        :type stream: SegmentedStream
        :param client_payload:
        :type client_payload:
        :param s:
        :type s: KeyPair
        :return:
        :rtype:
        """
        self._handshakestate.initialize(
            handshake_pattern=XXHandshakePattern(),
            initiator=True,
            prologue=self._prologue,
            s=s            
        )
        ephemeral_public = bytearray()
        self._handshakestate.write_message(b'', ephemeral_public)
        handshakemessage = wa5_pb2.HandshakeMessage()
        client_hello = wa5_pb2.HandshakeMessage.ClientHello()
        client_hello.ephemeral = bytes(ephemeral_public)
        handshakemessage.client_hello.MergeFrom(client_hello)
        stream.write_segment(handshakemessage.SerializeToString())
        import threading
        thread_id = threading.current_thread().ident
        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_xx() lendo server_hello | thread_id={thread_id}")
        incoming_handshakemessage = wa5_pb2.HandshakeMessage()
        try:
            segment_data = stream.read_segment()
            logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_xx() segment recebido | thread_id={thread_id} segment_len={len(segment_data) if segment_data else 0}")
            incoming_handshakemessage.ParseFromString(segment_data)
            logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_xx() segment parseado | thread_id={thread_id} has_server_hello={incoming_handshakemessage.HasField('server_hello')}")
        except Exception as parse_error:
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_xx() erro ao ler/parsear segment | thread_id={thread_id} error={parse_error} error_type={type(parse_error).__name__}")
            raise HandshakeFailedException(f"Erro ao ler segment do servidor: {parse_error}")
        
        if not incoming_handshakemessage.HasField("server_hello"):
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_xx() server_hello ausente | thread_id={thread_id} fields={incoming_handshakemessage.ListFields()}")
            raise HandshakeFailedException("Handshake message does not contain server hello!")
        server_hello = incoming_handshakemessage.server_hello
        payload_buffer = bytearray()
        self._handshakestate.read_message(
            server_hello.ephemeral + server_hello.static + server_hello.payload, payload_buffer
        )
        certman = CertMan()
        if certman.is_valid(self._handshakestate.rs, bytes(payload_buffer)):
            logger.debug("cert is valid")
        else:
            logger.error("cert is not valid")

        message_buffer = bytearray()
        cipherpair = self._handshakestate.write_message(client_payload.SerializeToString(), message_buffer)

        static, payload = ByteUtil.split(bytes(message_buffer), 48, len(message_buffer) - 48)

        client_finish = wa5_pb2.HandshakeMessage.ClientFinish()
        client_finish.static = static
        client_finish.payload = payload
        outgoing_handshakemessage = wa5_pb2.HandshakeMessage()        
        outgoing_handshakemessage.client_finish.MergeFrom(client_finish)

        stream.write_segment(outgoing_handshakemessage.SerializeToString())
        
        return cipherpair

    def _start_handshake_ik(self, stream, client_payload, s, rs):
        """
        :param stream:
        :type stream: SegmentedStream
        :param s:
        :type s: KeyPair
        :param rs:
        :type rs: PublicKey
        :return:
        :rtype:
        """
        self._handshakestate.initialize(
            handshake_pattern=IKHandshakePattern(),
            initiator=True,
            prologue=self._prologue,
            s=s,
            rs=rs
        )

        message_buffer = bytearray()
        self._handshakestate.write_message(client_payload.SerializeToString(), message_buffer)                        
        ephemeral_public, static_public, payload = ByteUtil.split(bytes(message_buffer), 32, 48, len(message_buffer))
        handshakemessage = wa5_pb2.HandshakeMessage()
        client_hello = wa5_pb2.HandshakeMessage.ClientHello()
        client_hello.ephemeral = ephemeral_public
        client_hello.static = static_public
        client_hello.payload = payload
        handshakemessage.client_hello.MergeFrom(client_hello)
        import threading
        thread_id = threading.current_thread().ident
        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() enviando client_hello | thread_id={thread_id}")
        stream.write_segment(handshakemessage.SerializeToString())
        logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() client_hello enviado, aguardando resposta | thread_id={thread_id}")
        
       
        incoming_handshakemessage = wa5_pb2.HandshakeMessage()
        try:
            segment_data = stream.read_segment()
            
            logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() segment recebido | thread_id={thread_id} segment_len={len(segment_data) if segment_data else 0}")
            incoming_handshakemessage.ParseFromString(segment_data)
            logger.info(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() segment parseado | thread_id={thread_id} has_server_hello={incoming_handshakemessage.HasField('server_hello')}")
        except Exception as read_error:
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() erro ao ler segment | thread_id={thread_id} error={read_error} error_type={type(read_error).__name__}")
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() traceback completo:\n{__import__('traceback').format_exc()}")
            raise HandshakeFailedException(f"Handshake exception after server read: {read_error}")
        
        if not incoming_handshakemessage.HasField("server_hello"):
            logger.error(f"[HANDSHAKE-DEBUG] WAHandshake._start_handshake_ik() server_hello ausente | thread_id={thread_id} fields={incoming_handshakemessage.ListFields()}")
            raise HandshakeFailedException("Handshake message does not contain server hello!")

        server_hello = incoming_handshakemessage.server_hello
        if server_hello.HasField("static"):
            raise NewRemoteStaticException(server_hello)
                    
        payload_buffer = bytearray()        
        
        return self._handshakestate.read_message(
            server_hello.ephemeral + server_hello.static + server_hello.payload, payload_buffer
        )        
            

    def NewRemoteStaticException(self, stream, s, client_payload, server_hello):
        """
        :param handshake_pattern:
        :type handshake_pattern: HandshakePattern
        :param stream:
        :type stream: SegmentedStream
        :param s:
        :type s: KeyPair
        :param e:
        :type e: KeyPair
        :param client_payload:
        :type client_payload:
        :param server_hello:
        :type server_hello:
        :return:
        :rtype: tuple(CipherState,CipherState)
        """
        self._handshakestate.switch(
                handshake_pattern=FallbackPatternModifier().modify(XXHandshakePattern()),
                initiator=False,
                prologue=self._prologue,
                s=s
            )
        payload_buffer = bytearray()        
        self._handshakestate.read_message(server_hello.ephemeral + server_hello.static + server_hello.payload, payload_buffer)
        certman = CertMan()
        if certman.is_valid(self._handshakestate.rs, bytes(payload_buffer)):
            logger.debug("cert is valid")
        else:
            logger.error("cert is not valid")

        message_buffer = bytearray()
        cipherpair = self._handshakestate.write_message(client_payload.SerializeToString(), message_buffer)
        static, payload = ByteUtil.split(bytes(message_buffer), 48, len(message_buffer) - 48)
        client_finish = wa5_pb2.HandshakeMessage.ClientFinish()
        client_finish.static = static
        client_finish.payload = payload
        outgoing_handshakemessage = wa5_pb2.HandshakeMessage()
        outgoing_handshakemessage.client_finish.MergeFrom(client_finish)
        stream.write_segment(outgoing_handshakemessage.SerializeToString())
        return cipherpair

    def _create_full_payload(self, client_config,s):
        """
        :param client_config:
        :type client_config: ClientConfig
        :return:
        :rtype: wa5_pb2.ClientPayload
        """        
        client_payload = wa5_pb2.ClientPayload()
        user_agent = wa5_pb2.ClientPayload.UserAgent()
        user_agent_app_version = wa5_pb2.ClientPayload.UserAgent.AppVersion()

        user_agent.platform = client_config.useragent.platform
        user_agent.mcc = client_config.useragent.mcc
        user_agent.mnc = client_config.useragent.mnc
        user_agent.os_version = client_config.useragent.os_version
        user_agent.manufacturer = client_config.useragent.manufacturer
        user_agent.device = client_config.useragent.device
        user_agent.os_build_number = client_config.useragent.os_build_number
        user_agent.phone_id = client_config.useragent.phone_id        

        #user_agent.device_exp_id = client_config.useragent.device_exp_id
        
        user_agent.locale_language_iso_639_1 = client_config.useragent.locale_lang
        user_agent.locale_country_iso_3166_1_alpha_2 = client_config.useragent.locale_country       

        user_agent.release_channel = 0 #RELEASE
        user_agent.device_type = 0  #PHONE

        if client_config.useragent.device_model_type is not None:
            user_agent.device_model_type = client_config.useragent.device_model_type
             
        user_agent_app_version.primary = client_config.useragent.app_version.primary
        user_agent_app_version.secondary = client_config.useragent.app_version.secondary
        user_agent_app_version.tertiary = client_config.useragent.app_version.tertiary
        user_agent_app_version.quaternary = client_config.useragent.app_version.quaternary

        user_agent.app_version.MergeFrom(user_agent_app_version)

        client_payload.passive = client_config.passive
        #max_int = int((2**32) / 2)

        #client_payload.session_id = random.randint(-max_int, max_int-1)
        client_payload.short_connect = True
        client_payload.connect_type = 1
        client_payload.connect_reason = 1
        client_payload.dns_source.dns_method = 0
        client_payload.connect_attempt_count = 0        
        client_payload.user_agent.MergeFrom(user_agent)         

        
                
        if self.mode is None: 
            client_payload.username = client_config.username            
            client_payload.push_name = client_config.pushname

            if self.deviceid is not None:
                client_payload.device = self.deviceid
            else:
                client_payload.device = 0
        else:              
            client_payload.device_pairing_data.e_regid=self.regid.to_bytes(4,"big")

            client_payload.device_pairing_data.e_keytype=b"\x05"            
            client_payload.device_pairing_data.e_ident=self.identity.publicKey.serialize()[1:]            
            client_payload.device_pairing_data.e_skey_id=self.signedprekey.getId().to_bytes(4,"big")
            client_payload.device_pairing_data.e_skey_val=self.signedprekey.getKeyPair().publicKey.serialize()[1:]

            sign = self.signedprekey.getSignature()
            client_payload.device_pairing_data.e_skey_sig = sign

            m= hashlib.md5()
            m.update(client_config.useragent.app_version.getVersion().encode())            
            client_payload.device_pairing_data.build_hash=base64.b64decode(m.hexdigest())    #这里还有疑问
            #client_payload.device_pairing_data.build_hash = m.digest()                
            client_payload.device_pairing_data.device_props.os = client_config.useragent.os_version
            client_payload.device_pairing_data.device_props.version.primary = client_config.useragent.app_version.primary
            client_payload.device_pairing_data.device_props.version.secondary = client_config.useragent.app_version.secondary
            client_payload.device_pairing_data.device_props.version.tertiary = client_config.useragent.app_version.tertiary
            client_payload.device_pairing_data.device_props.version.quaternary = client_config.useragent.app_version.quaternary
            client_payload.device_pairing_data.device_props.platform_type = 9
            client_payload.device_pairing_data.device_props.require_full_sync = 1
            client_payload.oc = True
            client_payload.lc = 1            
                                 
        return client_payload

