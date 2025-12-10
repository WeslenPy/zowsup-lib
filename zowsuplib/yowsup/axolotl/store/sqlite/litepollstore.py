from zowsuplib.axolotl.state.pollstore import PollStore
from zowsuplib.axolotl.state.sessionrecord import SessionRecord
import sys
import hashlib
class LitePollStore(PollStore):

    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

        dbConn.execute("CREATE TABLE IF NOT EXISTS poll (_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "poll_msg_id INTEGER,"
                "enc_key BLOB,"
                "name TEXT);")          

        dbConn.execute("CREATE TABLE IF NOT EXISTS poll_option (_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "poll_msg_id INTEGER,"
                "option_name TEXT,"
                "option_sha256 BLOB);")                             

    def deletePoll(self, poll_msg_id):
        q = "DELETE FROM poll_option WHERE poll_msg_id = ?"
        c = self.dbConn.cursor().execute(q, (poll_msg_id, ))
        q = "DELETE FROM poll WHERE poll_msg_id = ?"
        c = self.dbConn.cursor().execute(q, (poll_msg_id, ))
        self.dbConn.commit()        


    def storePoll(self, poll_msg_id,name,enc_key,options):


        q = "INSERT INTO poll(poll_msg_id,enc_key, name) VALUES(?,?,?)"
        c = self.dbConn.cursor()
        c.execute(q, (poll_msg_id, enc_key,name))

        for item in options:
            q = "INSERT INTO poll_option(poll_msg_id, option_name,option_sha256) VALUES(?,?,?)"
            c = self.dbConn.cursor()
            hash = hashlib.sha256(item.encode()).digest()            
            c.execute(q, (poll_msg_id, item,hash))

        self.dbConn.commit()

    
    def decryptOptions(self,poll_msg_id,option_sha256_list):

        print(poll_msg_id)
        print(option_sha256_list)

        options = []        
        for sha256_item in option_sha256_list:
            print(sha256_item)
            q = "SELECT option_name FROM poll_option WHERE poll_msg_id = ? AND option_sha256 = ?"
            c = self.dbConn.cursor()
            c.execute(q, (poll_msg_id,  sha256_item))
            result = c.fetchone()
            if result:                                      
                options.append(result[0].decode("utf-8"))
            else:            
                options.append("ITEM ERROR")           
                    
        return options    

    
    def getPollEncKey(self,poll_msg_id):
        print(poll_msg_id)
        q = "SELECT enc_key FROM poll WHERE poll_msg_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (poll_msg_id, ))
        result = c.fetchone()
        if result:                                      
            return result[0]
        else:            
            return None







