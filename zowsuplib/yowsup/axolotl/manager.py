from zowsuplib.axolotl.util.keyhelper import KeyHelper
from zowsuplib.axolotl.identitykeypair import IdentityKeyPair
from zowsuplib.axolotl.groups.senderkeyname import SenderKeyName
from zowsuplib.axolotl.axolotladdress import AxolotlAddress
from zowsuplib.axolotl.sessioncipher import SessionCipher
from zowsuplib.axolotl.groups.groupcipher import GroupCipher
from zowsuplib.axolotl.groups.groupsessionbuilder import GroupSessionBuilder
from zowsuplib.axolotl.sessionbuilder import SessionBuilder
from zowsuplib.axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage
from zowsuplib.axolotl.protocol.whispermessage import WhisperMessage
from zowsuplib.axolotl.state.prekeybundle import PreKeyBundle
from zowsuplib.axolotl.untrustedidentityexception import UntrustedIdentityException
from zowsuplib.axolotl.invalidmessageexception import InvalidMessageException
from zowsuplib.axolotl.duplicatemessagexception import DuplicateMessageException
from zowsuplib.axolotl.invalidkeyidexception import InvalidKeyIdException
from zowsuplib.axolotl.nosessionexception import NoSessionException
from zowsuplib.axolotl.protocol.senderkeydistributionmessage import SenderKeyDistributionMessage
from zowsuplib.axolotl.state.axolotlstore import AxolotlStore
from zowsuplib.yowsup.axolotl.store.sqlaxolotlstore import SqlAxolotlStore
from ..axolotl.store.sqlite.liteaxolotlstore import LiteAxolotlStore
from ..axolotl import exceptions
import random
import sys
import base64
from ..common.tools import WATools

from loguru import logger


class AxolotlManager(object):

    COUNT_GEN_PREKEYS = 812
    THRESHOLD_REGEN = 10
    MAX_SIGNED_PREKEY_ID = 16777215

    def __init__(self, store, username):
        """
        :param store:
        :type store: AxolotlStore
        :param username:
        :type username: str
        """
        self._username = username # type: str
        self._store:SqlAxolotlStore = store # type: LiteAxolotlStore
        self._identity = self._store.getIdentityKeyPair() # type: IdentityKeyPair
        self._registration_id = self._store.getLocalRegistrationId() # type: int | None

        assert self._registration_id is not None
        assert self._identity is not None

        self._group_session_builder = GroupSessionBuilder(self._store) # type: GroupSessionBuilder
        self._session_ciphers = {} # type: dict[str, SessionCipher]
        self._group_ciphers = {} # type: dict[str, GroupCipher]
        logger.debug(f"Initialized AxolotlManager [username={self._username}, db={store}]")


    @property
    def registration_id(self):
        return self._registration_id

    @property
    def identity(self):
        return self._identity
    
    def get_all_accounts(self,username):
        ret = self._store.getAllAccounts(username)        
        return ret

    def level_prekeys(self, force=False):        
        logger.debug(f"level_prekeys(force={force})")
        len_pending_prekeys = len(self._store.loadPreKeys())
        logger.debug(f"len(pending_prekeys) = {len_pending_prekeys}")
        
        
        if force or len_pending_prekeys < self.THRESHOLD_REGEN:
            count_gen = self.COUNT_GEN_PREKEYS
            max_prekey_id = self._store.preKeyStore.loadMaxPreKeyId()
            logger.info(f"Generating {count_gen} prekeys, current max_prekey_id={max_prekey_id}")
            prekeys = KeyHelper.generatePreKeys(max_prekey_id + 1, count_gen)
            logger.info(f"Storing {len(prekeys)} prekeys")
            for i in range(0, len(prekeys)):
                key = prekeys[i]
                logger.debug(f"Storing prekey {i + 1}/{len(prekeys)} \r")
                self._store.storePreKey(key.getId(), key)
            return prekeys
        
        
        return []


    def load_unsent_prekeys(self):
        logger.debug("load_unsent_prekeys")
        unsent = self._store.preKeyStore.loadUnsentPendingPreKeys()
        if len(unsent) > 0:
            logger.info(f"Loaded {len(unsent)} unsent prekeys")
        return unsent

    def set_prekeys_as_sent(self, prekeyIds):
        """
        :param prekeyIds:
        :type prekeyIds: list
        :return:
        :rtype:
        """
        logger.debug(f"set_prekeys_as_sent(prekeyIds=[{len(prekeyIds)} prekeyIds])")
        self._store.preKeyStore.setAsSent([prekey.getId() for prekey in prekeyIds])

    def generate_signed_prekey(self):
        logger.debug("generate_signed_prekey")
        latest_signed_prekey = self.load_latest_signed_prekey(generate=False)
        if latest_signed_prekey is not None:                        
            if latest_signed_prekey.getId() == self.MAX_SIGNED_PREKEY_ID:
                new_signed_prekey_id = (self.MAX_SIGNED_PREKEY_ID / 2) + 1
            else:
                new_signed_prekey_id = latest_signed_prekey.getId() + 1
        else:
            new_signed_prekey_id = random.randint(0,800)            
        signed_prekey = KeyHelper.generateSignedPreKey(self._identity, new_signed_prekey_id)
        self._store.storeSignedPreKey(signed_prekey.getId(), signed_prekey)
        return signed_prekey

    def load_latest_signed_prekey(self, generate=False):
        logger.debug("load_latest_signed_prekey")
        signed_prekeys = self._store.loadSignedPreKeys()
        if len(signed_prekeys):
            return signed_prekeys[-1]

        return self.generate_signed_prekey() if generate else None
    
    def _get_session_cipher(self, username,deviceid=0):
        logger.debug(f"get_session_cipher(username={username})")
        key = "%s-%d" % (username,deviceid)        
        if key in self._session_ciphers:
            session_cipher = self._session_ciphers[key]
        else:                        
            session_cipher= SessionCipher(self._store, self._store, self._store, self._store, username, deviceid)
            self._session_ciphers[key] = session_cipher
        return session_cipher

    def _get_group_cipher(self, groupid, username):
        logger.debug(f"get_group_cipher(groupid={groupid}, username={username})")
        senderkeyname = SenderKeyName(groupid, AxolotlAddress(username, 0))
        if senderkeyname in self._group_ciphers:
            group_cipher = self._group_ciphers[senderkeyname]
        else:
            group_cipher = GroupCipher(self._store.senderKeyStore, senderkeyname)
            self._group_ciphers[senderkeyname] = group_cipher
        return group_cipher

    def _generate_random_padding(self):
        logger.debug("generate_random_padding")
        num = random.randint(1,255)
        return bytes(bytearray([num] * num))

    def _unpad(self, data):
        padding_byte = data[-1] if type(data[-1]) is int else ord(data[-1]) # bec inconsistent API?
        padding = padding_byte & 0xFF
        return data[:-padding]

    def encrypt(self, username, message):
        # to avoid the hassle of encoding issues and associated unnecessary crashes,
        # don't log the message content.
        # see https://github.com/tgalal/yowsup/issues/2732
        logger.debug(f"encrypt(username={username}, message=[omitted])")
        """
        :param username:
        :type username: str
        :param data:
        :type data: bytes
        :return:
        :rtype:
        """
        recipientId,a,deviceid = WATools.jidDecode(username)

        cipher = self._get_session_cipher(recipientId,deviceid)        
        return cipher.encrypt(message + self._generate_random_padding())
    
    def decrypt_pkmsg(self, senderid, data, unpad):
        logger.debug(f"decrypt_pkmsg(senderid={senderid}, data=(omitted), unpad={unpad})")
        pkmsg = PreKeyWhisperMessage(serialized=data)

        recipientId,a,deviceid = WATools.jidDecode(senderid)        
        try:
            plaintext = self._get_session_cipher(recipientId,deviceid).decryptPkmsg(pkmsg)
            return self._unpad(plaintext) if unpad else plaintext
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No session")
        except InvalidKeyIdException as e:
            raise exceptions.InvalidKeyIdException(str(e) if str(e) else "Invalid key ID")
        except InvalidMessageException as e:
            # Preserva a mensagem original da exceção (pode conter "Bad Mac!" ou outras informações)
            raise exceptions.InvalidMessageException(str(e) if str(e) else "Invalid message")
        except DuplicateMessageException as e:
            raise exceptions.DuplicateMessageException(str(e) if str(e) else "Duplicate message")


    def decrypt_msg(self, senderid, data, unpad):
        logger.debug(f"decrypt_msg(senderid={senderid}, data=[omitted], unpad={unpad})")
        msg = WhisperMessage(serialized=data)
        recipientId,a,deviceid = WATools.jidDecode(senderid)

        try:
            plaintext = self._get_session_cipher(recipientId,deviceid).decryptMsg(msg)

            return self._unpad(plaintext) if unpad else plaintext
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No session")
        except InvalidKeyIdException as e:
            raise exceptions.InvalidKeyIdException(str(e) if str(e) else "Invalid key ID")
        except InvalidMessageException as e:
            # Preserva a mensagem original da exceção (pode conter "Bad Mac!" ou outras informações)
            # Isso ajuda no diagnóstico quando a exceção é tratada em camadas superiores
            raise exceptions.InvalidMessageException(str(e) if str(e) else "Invalid message")
        except DuplicateMessageException as e:
            raise exceptions.DuplicateMessageException(str(e) if str(e) else "Duplicate message")

    def group_encrypt(self, groupid, message):
        """
        :param groupid:
        :type groupid: str
        :param message:
        :type message: bytes
        :return:
        :rtype:
        """
        # to avoid the hassle of encoding issues and associated unnecessary crashes,
        # don't log the message content.
        # see https://github.com/tgalal/yowsup/issues/2732
        logger.debug(f"group_encrypt(groupid={groupid}, message=[omitted])")
        group_cipher = self._get_group_cipher(groupid, self._username)
        try:
            return group_cipher.encrypt(message + self._generate_random_padding())
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No sender key for group")

    def group_decrypt(self, groupid, participantid, data):
        logger.debug(f"group_decrypt(groupid={groupid}, participantid={participantid}, data=[omitted])")
        group_cipher = self._get_group_cipher(groupid, participantid)
        try:
            plaintext = group_cipher.decrypt(data)
            plaintext = self._unpad(plaintext)
            return plaintext
        except NoSessionException:
            raise exceptions.NoSessionException()
        except DuplicateMessageException:
            raise exceptions.DuplicateMessageException()
        except InvalidMessageException:
            raise exceptions.InvalidMessageException()

    def group_create_skmsg(self, groupid):
        logger.debug(f"group_create_skmsg(groupid={groupid})")
        senderKeyName = SenderKeyName(groupid, AxolotlAddress(self._username, 0))
        return self._group_session_builder.create(senderKeyName)

    def group_create_session(self, groupid, participantid, skmsgdata):
        """
        :param groupid:
        :type groupid: str
        :param participantid:
        :type participantid: str
        :param skmsgdata:
        :type skmsgdata: bytearray
        :return:
        :rtype:
        """
        logger.debug(f"group_create_session(groupid={groupid}, participantid={participantid}, skmsgdata=[omitted])")
        senderKeyName = SenderKeyName(groupid, AxolotlAddress(participantid, 0))
        senderkeydistributionmessage = SenderKeyDistributionMessage(serialized=skmsgdata)
        self._group_session_builder.process(senderKeyName, senderkeydistributionmessage)

    def create_session(self, username, prekeybundle, autotrust=False):
        """
        :param username:
        :type username: str
        :param prekeybundle:
        :type prekeybundle: PreKeyBundle
        :return:
        :rtype:
        """
        logger.debug(f"create_session(username={username}, prekeybundle=[omitted], autotrust={autotrust})")

        recipient,a,deviceid = WATools.jidDecode(username)     

        session_builder = SessionBuilder(self._store, self._store, self._store, self._store, recipient, deviceid)        
        try:                        
            session_builder.processPreKeyBundle(prekeybundle)                        
        except UntrustedIdentityException as ex:
            if autotrust:
                self.trust_identity(ex.getName(), ex.getIdentityKey())
            else:
                raise exceptions.UntrustedIdentityException(ex.getName(), ex.getIdentityKey())

    def session_exists(self, username):
        """
        :param username:
        :type username: str
        :return:
        :rtype:
        """        
        logger.debug(f"session_exists({username})?")
        recipient,a,deviceid = WATools.jidDecode(username)   
        return self._store.containsSession(recipient, deviceid)
    
    def get_all_session_usernames(self,username):
        #获取一个用户名的所有关联终端的session，主要用来用来发消息
        logger.debug("get_all_session_usernames")
        return self._store.get_all_session_usernames(username)

    def load_senderkey(self, groupid):
        logger.debug(f"load_senderkey(groupid={groupid})")
        senderkeyname = SenderKeyName(groupid, AxolotlAddress(self._username, 0))
        return self._store.loadSenderKey(senderkeyname)

    def trust_identity(self, account ,identitykey):
        logger.debug(f"trust_identity(account={account}, identitykey=[omitted])")

        recipient,a,deviceid = WATools.jidDecode(account) 
        self._store.saveIdentity(recipient,deviceid,identitykey)


