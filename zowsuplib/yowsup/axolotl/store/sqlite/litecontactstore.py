from zowsuplib.axolotl.state.taskmsgstore import TaskMsgStore

import time

class LiteContactStore(TaskMsgStore):

    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

        dbConn.execute("CREATE TABLE IF NOT EXISTS contact(_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "name TEXT,"
                "jid TEXT,"
                "timestamp INTEGER);")   #这个字段设置主要用于后续清理一些过期的消息,减少执行端的空间消耗                                    
                    
    def addContact(self, jid,name=None):

        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return None
                        
        if name is None:
            name = ""
        if not self.findContact(jid):            
            q = "INSERT INTO contact(name,jid,timestamp) VALUES(?,?,?)"
            self.dbConn.cursor().execute(q, (name, jid,int(time.time())))
            self.dbConn.commit()
            return jid                
        return None


    def findContact(self,jid):      
        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return None

        q = "SELECT jid FROM contact WHERE jid = ?"
        c = self.dbConn.cursor()
        c.execute(q, (jid, ))
                                
        if c.fetchone():                                      
            return True
        else:            
            return False
        
    def isNewContact(self,jid):                        
        if jid.endswith("@s.whatsapp.net") or jid.endswith("@c.us"):
            return (not self.findContact(jid))
        return False
                
    def removeContact(self,jid):
        q = "DELETE FROM contact where jid = ?"
        self.dbConn.cursor().execute(q, (jid))
        self.dbConn.commit()        
        return True
    
    def getAllContact(self):
        #返回一个jid数组        
        q = "SELECT jid FROM contact"
        c = self.dbConn.cursor()
        c.execute(q)

        results = c.fetchall()
        jids = []
        for item in results:
            jids.append(item[0])

        return jids

    







