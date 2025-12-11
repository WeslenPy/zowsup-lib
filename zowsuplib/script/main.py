# coding=UTF-8
import sys
import time
from loguru import logger

from zowsuplib.common.consolemain import ConsoleMain
from zowsuplib.app.yowbot import YowBot
from zowsuplib.script.cmdprocess import CmdProcess
from zowsuplib.script.interactiveprocess import InteractiveProcess
from zowsuplib.conf.constants import SysVar, GlobalVar
from zowsuplib.common.utils import Utils
from zowsuplib.yowsup.config.manager import ConfigManager
from zowsuplib.yowsup.profile.profile import YowProfile
from zowsuplib.app.device_env import DeviceEnv
from zowsuplib.settings.conf import settings

class Main(ConsoleMain):
     
    def run(self,params,options):
        
        if len(params) == 0:
            print("a phone number must be specified")        
            sys.exit(1)
        else:
            botId = params[0]
        
        if "debug" in options:
            self.init_log("DEBUG", botId + ".log")
        else:
            self.init_log("INFO", botId + ".log")

        
        if "proxy" not in options:
            options["proxy"] = "DIRECT"

        lg,lc = Utils.getLGLC(Utils.getMobileCC(botId))
        logger.info(f"LG={lg}, LC={lc}")

        self.commonOptionsProcess(options)

        # Verifica existência da conta via configuração persistida (ProfileConfig / MySQL)
        config_manager = ConfigManager()
        cfg = config_manager.load(botId, profile_only=True)
        if cfg is None:
            logger.info("account not exist !!")
            return

        info = None        
        if "env" not in options:           
        
            profile = YowProfile(botId)
            if profile.config.os_name is not None:
                logger.info("Local Profile found")
                tt = {
                    "Android":"android",
                    "SMBA":"smb_android",
                    "iOS":"ios",
                    "SMB iOS":"smb_ios"
                }
                self.env.deviceEnv = DeviceEnv(tt[profile.config.os_name])
            else:
                pass  

        logger.info(f"ENV={self.env.deviceEnv.getOSName()}")                
        logger.info(f"BotId={botId}")        
        logger.info(f"RegType={info['regType'] if info is not None else '1'}") 
        

        

        try:  
            wabot = YowBot(bot_id=botId,env=self.env,)
            logger.info(self.env.networkEnv)            
            
            if len(params) == 1:
                InteractiveProcess(wabot).run()
                pass            
            else: 
                if params[1] in wabot.getCmdList():                      
                    CmdProcess(wabot,params[1:],options).run()    
                else:
                    logger.info("Unknown Command")         

            wabot.runAsThread()

            while True:
                if wabot.sendLayer.userQuit:
                    break
                time.sleep(0.1)
        except KeyboardInterrupt:                
            wabot.disconnect()            
            
if __name__ == "__main__":
    
    GlobalVar.WANUMTYPE = 1     
    # Inicializa Settings (pydantic BaseSettings já carrega .env/variáveis)
    _ = settings
        
    if len(sys.argv)<=1:
        print("USAGE:")
        print("\nmain.py [account-number] [command] [commandParams]\n")
        YowBot.printUsage()
        sys.exit(0)
    
    params,options = Utils.cmdLineParser(sys.argv)


    Main().run(params,options)    
    

    

    
    

    


    

        
    




    



            


