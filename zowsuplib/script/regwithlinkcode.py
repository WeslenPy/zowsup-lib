# coding=UTF-8
import sys
from loguru import logger

from zowsuplib.app.yowbot import YowBot
from zowsuplib.conf.constants import SysVar, GlobalVar
from zowsuplib.common.utils import Utils
from zowsuplib.common.consolemain import ConsoleMain
from zowsuplib.app.yowbot_values import YowBotType

class RegWithLinkCode(ConsoleMain):    

    def run(self,params,options):
        
        if len(params) == 0:
            print("a phone number must be specified")        
            sys.exit(1)
        else:
            botId = params[0]        

        if len(params) >1 :
            linkCode = params[1]
        else:
            linkCode = "AAAAAAAA"

        if "debug" in options:
            self.init_log("DEBUG", botId + ".log")
        else:
            self.init_log("INFO", botId + ".log")
            

        self.commonOptionsProcess(options)   
        try:  
            wabot = YowBot(bot_id=None,env=self.env,bot_type=YowBotType.TYPE_REG_COMPANION_LINKCODE  )            
            wabot.pairPhoneNumber = botId
            wabot.pairLinkCode = linkCode
            wabot.run()
        except KeyboardInterrupt:        
            print("error")
            
if __name__ == "__main__":

    GlobalVar.BOTTYPE = 2  # 注册模式    
    #随机一个设备
    SysVar.loadConfig()    

    params,options = Utils.cmdLineParser(sys.argv) 
    RegWithLinkCode().run(params,options)    
        
    

    


    

        
    




    



            


