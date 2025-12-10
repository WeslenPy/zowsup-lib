from zowsuplib.axolotl.state.sessionstore import SessionStore
from zowsuplib.axolotl.state.sessionrecord import SessionRecord
import sys
class LiteSessionStore(SessionStore):

    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn
        dbConn.execute("CREATE TABLE IF NOT EXISTS sessions (_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "recipient_id INTEGER,"
                       "recipient_type INTEGER NOT NULL DEFAULT 0,"
                       "device_id INTEGER, record BLOB, timestamp INTEGER);")

    def loadSession(self, account , deviceId):

        recipientId = account

        q = "SELECT record FROM sessions WHERE recipient_id = ? AND device_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipientId,  deviceId))
        result = c.fetchone()

        if result:            
            return SessionRecord(serialized=result[0])
        else:            
            return SessionRecord()

    def getSubDeviceSessions(self, recipient):        

        q = "SELECT device_id from sessions WHERE recipient_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipient,))
        result = c.fetchall()

        deviceIds = [r[0] for r in result]
        return deviceIds

    def storeSession(self, recipient, deviceId, sessionRecord):
                        
        self.deleteSession(recipient, deviceId)

        q = "INSERT INTO sessions(recipient_id, device_id, record) VALUES(?,?,?)"
        c = self.dbConn.cursor()
        serialized = sessionRecord.serialize()
        c.execute(q, (recipient, deviceId, buffer(serialized) if sys.version_info < (2,7) else serialized))
        self.dbConn.commit()

    def containsSession(self, recipient, deviceId):        

        q = "SELECT record FROM sessions WHERE recipient_id = ?  AND device_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipient, deviceId))
        result = c.fetchone()

        return result is not None

    def deleteSession(self, recipient ,deviceId):        
        q = "DELETE FROM sessions WHERE recipient_id = ? AND device_id = ?"
        self.dbConn.cursor().execute(q, (recipient, deviceId))
        self.dbConn.commit()

    def deleteAllSessions(self, recipient):        
        q = "DELETE FROM sessions WHERE recipient_id = ?"
        self.dbConn.cursor().execute(q, (recipient,))
        self.dbConn.commit()

    def getAllAccounts(self,recipient):
        q = "SELECT recipient_id,recipient_type,device_id from sessions WHERE recipient_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipient,))
        result = c.fetchall()        
        accounts = ["%d.%d:%d" % (r[0],r[1],r[2]) for r in result]
        return accounts



