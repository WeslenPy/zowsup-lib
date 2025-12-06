# coding=UTF-8
import sys,os
sys.path.append(os.getcwd())

import traceback
from loguru import logger
from yowsup.registration import WAReset2FARequest
from yowsup.config.manager import ConfigManager
from conf.constants import SysVar
from common.utils import Utils
from common.consolemain import ConsoleMain
class Reset2FA(ConsoleMain):

    def run(self,params,options):

        if "env" not in options:
            options["env"] = SysVar.DEFAULT_ENV
            logger.info(f"set default env to {options['env']}")
                
        number = params[0]
        wipe_token = params[1]
        self.commonOptionsProcess(options,waNum=number)       
        config_manager = ConfigManager()
        # Carrega config usando apenas o identificador da conta (ProfileConfig / MySQL)
        config = config_manager.load(number, profile_only=True)
        try:
            req = WAReset2FARequest(config,wipe_token,self.env)            
            result = req.send(preview=False)         
            print(result)   
        except:
            logger.error(traceback.format_exc())
            Utils.outputResult({
                "retcode":-1,            
                "msg":"exception",
                "details":traceback.format_exc()
            })    
            sys.exit(1)   
                          
if __name__ == "__main__":
    SysVar.loadConfig()
    Utils.init_log("INFO")     
    params,options = Utils.cmdLineParser(sys.argv)    
    Reset2FA().run(params,options)    