# coding=UTF-8
import threading
import time
import json
from unicodedata import name
from loguru import logger

from zowsuplib.conf.constants import SysVar
from zowsuplib.proto import wsend_pb2

class CmdProcess:

    def __init__(self,bot,args,options,taskId=None,partNo=None):                                
        self.bot = bot            
        self.args = args        
        self.options = options

        self.thread = threading.Thread(name=f"cmdprocess_{self.bot.botId}", target=self.runThread)
        self.thread.setDaemon(True)

    def waitLogin(self):
        return self.bot.waitLogin() 

    def runThread(self):
        logger.info(f"Waiting BOT {self.bot.botId} ") 

        if self.waitLogin():       
            if self.bot.sendLayer.detect40x:
                logger.info(f"BOT {self.bot.botId} login failed")    
                self.bot.disconnect()                 
            else:
                logger.info(f"BOT {self.bot.botId} ready，starting command")                
                waitTime = 0            

                if self.args[0]=="init":                
                    waitTime = 10                            
                elif self.args[0]=="mdlink":
                    waitTime = 60
                else:
                    waitTime = 20

                if SysVar.CMD_WAIT is not None:                
                    waitTime = SysVar.CMD_WAIT             
                                
                cmdId,errMsg = self.bot.callDirect(self.args[0],self.args[1:] if  len(self.args)>1 else [],self.options)        

                if errMsg is not None:
                    logger.info(f"Commmand {self.args[0]} error(execute stage），info={errMsg}")      
                else:                    
                    if cmdId=="JUSTWAIT":                         
                        logger.info(f"Command JUSTWAIT {waitTime} seconds") 
                        time.sleep(waitTime)
                        logger.info("Command complete") 
                    else:
                        result,errMsg = self.bot.getCmdResult(cmdId,waitTime)                    

                        if errMsg is not None:
                            logger.info(f"Command {self.args[0]} error (result stage），info={errMsg}") 
                    
                        else:
                            logger.info(f"Command {self.args[0]} complete，result={json.dumps(result)}")

                                   
                self.bot.disconnect()           

        else:
            logger.info(f"BOT {self.bot.botId} connection timeout")    
            self.bot.disconnect() 
    
    def run(self):       

        self.thread.start()




        

        




        
        
                



