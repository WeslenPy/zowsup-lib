from zowsuplib.axolotl.state.taskmsgstore import TaskMsgStore

import time

class LiteTrustedContactStore(TaskMsgStore):

    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

        dbConn.execute("CREATE TABLE IF NOT EXISTS trusted_contact(jid TEXT PRIMARY KEY NOT NULL,incoming_tc_token BLOB NOT NULL,timestamp LONG NOT NULL);")
                    
    def updateTrustedContact(self, jid,tctoken=None):
        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return False                        
        if tctoken is None:
            return False        
        
        self.removeTrustedContact(jid)                   
        q = "INSERT INTO trusted_contact(jid,incoming_tc_token,timestamp) VALUES(?,?,?)"
        self.dbConn.cursor().execute(q, (jid,tctoken, int(time.time())))
        self.dbConn.commit()
        return True                        

    def getTcToken(self,jid):               
        q = "SELECT incoming_tc_token FROM trusted_contact WHERE jid = ?"
        c = self.dbConn.cursor()
        c.execute(q, (jid, ))
                                
        result = c.fetchone()
        if result:                                      
            return result[0] if result else None
        else:            
            return None
        
    
    def removeTrustedContact(self,jid):
        q = "DELETE FROM trusted_contact WHERE jid = ?"
        self.dbConn.cursor().execute(q, (jid,))
        self.dbConn.commit()                
        return True






