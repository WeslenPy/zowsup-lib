# coding=UTF-8
from loguru import logger

from zowsuplib.conf.constants import SysVar
from zowsuplib.common.utils import Utils
from zowsuplib.app.bot_env import BotEnv
from zowsuplib.app.network_env import NetworkEnv
from zowsuplib.app.device_env import DeviceEnv


class ConsoleMain:

    def __init__(self):        

        self.env = BotEnv(
            networkEnv=NetworkEnv("direct"),   
            deviceEnv=DeviceEnv(SysVar.DEFAULT_ENV)
        )                   
        
    def init_log(self,level,name):
        Utils.init_log(level,name)    
                    
    def setDefaultEnvByInfo(self,info):
        self.env.deviceEnv = Utils.getDeviceEnvByInfo(info)
            
    def commonOptionsProcess(self,options) :        
                
        if options is None:
            return
                
        if "proxy" not in options:
            options["proxy"] = "DIRECT"

        if "proxy" in options and options["proxy"]!="DIRECT":
            self.env.networkEnv.updateProxyStr(options["proxy"],rawProxyStr=options["proxy"])

        if "env" in options:            
            self.env.deviceEnv = DeviceEnv(options["env"])            
        
        if "accountpath" in options:
            SysVar.ACCOUNT_PATH = options["accountpath"]

        if "cmdwait" in options:
            SysVar.CMD_WAIT = int(options["cmdwait"])

