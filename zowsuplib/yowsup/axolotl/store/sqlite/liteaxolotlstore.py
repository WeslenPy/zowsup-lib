from zowsuplib.axolotl.state.axolotlstore import AxolotlStore
from .liteidentitykeystore import LiteIdentityKeyStore
from .liteprekeystore import LitePreKeyStore
from .litesessionstore import LiteSessionStore
from .litesignedprekeystore import LiteSignedPreKeyStore
from .litesenderkeystore import LiteSenderKeyStore
from .litepollstore import LitePollStore
from .liteappstatekeystore import LiteAppStateStore
from .litecontactstore import LiteContactStore
from .litebroadcaststore import LiteBroadcastStore
from .litetrustedcontactstore import LiteTrustedContactStore
import sqlite3


class LiteAxolotlStore(AxolotlStore):
    def __init__(self, db):
        conn = sqlite3.connect(db, check_same_thread=False)
        conn.text_factory = bytes
        self._db = db
        self.identityKeyStore = LiteIdentityKeyStore(conn)
        self.preKeyStore = LitePreKeyStore(conn)
        self.signedPreKeyStore = LiteSignedPreKeyStore(conn)
        self.sessionStore = LiteSessionStore(conn)
        self.senderKeyStore = LiteSenderKeyStore(conn)
        self.pollStore = LitePollStore(conn)        
        self.appStateStore = LiteAppStateStore(conn)
        self.contactStore = LiteContactStore(conn)
        self.broadcastStore = LiteBroadcastStore(conn)
        self.trustedContactStore = LiteTrustedContactStore(conn)

    def __str__(self):
        return self._db

    def getIdentityKeyPair(self):
        return self.identityKeyStore.getIdentityKeyPair()

    def getLocalRegistrationId(self):
        return self.identityKeyStore.getLocalRegistrationId()

    def saveIdentity(self, recipientId, deviceId,identityKey):
        self.identityKeyStore.saveIdentity(recipientId,deviceId,identityKey)

    def isTrustedIdentity(self, recipientId,deviceId, identityKey):
        return self.identityKeyStore.isTrustedIdentity(recipientId,deviceId, identityKey)

    def loadPreKey(self, preKeyId):
        return self.preKeyStore.loadPreKey(preKeyId)

    def loadPreKeys(self):
        return self.preKeyStore.loadPendingPreKeys()

    def storePreKey(self, preKeyId, preKeyRecord):
        self.preKeyStore.storePreKey(preKeyId, preKeyRecord)

    def containsPreKey(self, preKeyId):
        return self.preKeyStore.containsPreKey(preKeyId)

    def removePreKey(self, preKeyId):
        self.preKeyStore.removePreKey(preKeyId)
        
    def removeAllPreKeys(self):
        self.preKeyStore.clear()        

    def loadSession(self, account, deviceId):
        return self.sessionStore.loadSession(account, deviceId)

    def getSubDeviceSessions(self, account):
        return self.sessionStore.getSubDeviceSessions(account)

    def storeSession(self, account, deviceId, sessionRecord):
        self.sessionStore.storeSession(account, deviceId, sessionRecord)

    def containsSession(self, account,deviceId):
        return self.sessionStore.containsSession(account, deviceId)

    def deleteSession(self, account, deviceId):
        self.sessionStore.deleteSession(account, deviceId)

    def deleteAllSessions(self, account):
        self.sessionStore.deleteAllSessions(account)

    def loadSignedPreKey(self, signedPreKeyId):
        return self.signedPreKeyStore.loadSignedPreKey(signedPreKeyId)

    def loadSignedPreKeys(self):
        return self.signedPreKeyStore.loadSignedPreKeys()

    def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        self.signedPreKeyStore.storeSignedPreKey(signedPreKeyId, signedPreKeyRecord)

    def containsSignedPreKey(self, signedPreKeyId):
        return self.signedPreKeyStore.containsSignedPreKey(signedPreKeyId)

    def removeSignedPreKey(self, signedPreKeyId):
        self.signedPreKeyStore.removeSignedPreKey(signedPreKeyId)

    def loadSenderKey(self, senderKeyName):
        return self.senderKeyStore.loadSenderKey(senderKeyName)

    def storeSenderKey(self, senderKeyName, senderKeyRecord):
        self.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord)

    def getAllAccounts(self,account):
        return self.sessionStore.getAllAccounts(account)
    
    def addAppStateKeys(self,keys):
        return self.appStateStore.addAppStateKeys(keys)

    def getOneAppStateKey(self):
        return self.appStateStore.getOneAppStateKey()

    def getAppStateKey(self,key_id):
        return self.appStateStore.getAppStateKey(key_id)

    def removeAppStateKey(self,key_id):
        return self.appStateStore.deleteAppStateKey(key_id)
    
    def addContact(self,jid):
        return self.contactStore.addContact(jid,"")
        
    def removeContact(self,jid):
        return self.contactStore.removeContact(jid)
    
    def getAllContact(self):
        return self.contactStore.getAllContact()
    
    def findContact(self,jid):
        return self.contactStore.findContact(jid)
    
    def isNewContact(self,jid):
        return self.contactStore.isNewContact(jid)
    
    def addBroadcast(self,jids,senderJid,name=None):
        return self.broadcastStore.addBroadcast(jids,senderJid,name)
    
    def findParticipantsByBcid(self,bcid):
        return self.broadcastStore.findParticipantsByBcid(bcid)
    
    def updateTrustedContact(self,jid,tctoken):
        return self.trustedContactStore.updateTrustedContact(jid,tctoken)
    
    def getTcToken(self,jid):
        return self.trustedContactStore.getTcToken(jid)    
        


