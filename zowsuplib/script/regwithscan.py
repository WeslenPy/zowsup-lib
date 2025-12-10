# coding=UTF-8
import sys
from loguru import logger

from zowsuplib.app.yowbot import YowBot
from zowsuplib.conf.constants import SysVar
from zowsuplib.common.utils import Utils
from zowsuplib.common.consolemain import ConsoleMain
from zowsuplib.app.yowbot_values import YowBotType

class RegWithScan(ConsoleMain):
    def run(self,params,options):
        self.commonOptionsProcess(options)   
        if "debug" in options:
            self.init_log("DEBUG", "regwithscan.log")
        else:
            self.init_log("INFO", "regwithscan.log")

        try:  
            wabot = YowBot(bot_id=None,env=self.env,bot_type=YowBotType.TYPE_REG_COMPANION_SCANQR)                      
            wabot.run()
        except KeyboardInterrupt:        
            print("error")
            
if __name__ == "__main__":

    SysVar.loadConfig()
    
    params,options = Utils.cmdLineParser(sys.argv) 
    RegWithScan().run(params,options)    

       

    

    

    
    

    


    

        
    




    



            


