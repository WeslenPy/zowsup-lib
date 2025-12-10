# coding=UTF-8
import threading
import time
import json
import shlex
from unicodedata import name
from loguru import logger

from zowsuplib.conf.constants import SysVar
from zowsuplib.proto import wsend_pb2
from zowsuplib.common.utils import Utils

class InteractiveProcess:

    def __init__(self,bot):                                
        self.bot = bot            

        self.thread = threading.Thread(target=self.runThread)
        self.thread.daemon=True

    def waitLogin(self):
        return self.bot.waitLogin() 

    def runThread(self):
        logger.info(f"Waiting BOT {self.bot.botId} ") 

        if self.waitLogin():       
            if self.bot.sendLayer.detect40x:
                logger.info(f"BOT {self.bot.botId} login failed")    
                self.bot.disconnect()                 
            else:
                logger.info(f"BOT {self.bot.botId} ready.")      

                time.sleep(1)

                while True:

                    cmd = input("CMD > ")
                    cmd = "CMD "+cmd #
                    params,options = Utils.cmdLineParser(shlex.split(cmd))

                    if len(params)==0:
                        continue

                    if len(params)==1 and params[0]=="exit":
                        self.bot.quit()
                        break

                    if len(params[0].strip())>0:

                        waitTime = 0            

                        if params[0]=="init":                
                            waitTime = 10                            
                        elif params[0]=="mdlink":
                            waitTime = 60
                        else:
                            waitTime = 20

                        if SysVar.CMD_WAIT is not None:                
                            waitTime = SysVar.CMD_WAIT             
                                        
                        cmdId,errMsg = self.bot.callDirect(params[0],params[1:] if  len(params)>1 else [],options)        

                        if errMsg is not None:
                            logger.info(f"Commmand {params[0]} error(execute stage），info={errMsg}")      
                        else:                    
                            if cmdId=="JUSTWAIT":                         
                                logger.info("Command complete") 
                            else:
                                result,errMsg = self.bot.getCmdResult(cmdId,waitTime)                    
                                if errMsg is not None:
                                    logger.info(f"Command {params[0]} error (result stage），info={errMsg}") 
                                else:
                                    logger.info(f"Command {params[0]} complete，result={json.dumps(result)}")

                                   
                self.bot.disconnect()           

        else:
            logger.info(f"BOT {self.bot.botId} connection timeout")    
            self.bot.disconnect() 
    
    def run(self):       

        self.thread.start()




        

        




        
        
                



