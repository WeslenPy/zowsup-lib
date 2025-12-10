from .device_env_config import *
from .device_env import DeviceEnv
from .network_env import NetworkEnv

class BotEnv(object):
            
    def __init__(self,deviceEnv=None, networkEnv=None):

        if deviceEnv is None:
            deviceEnv = DeviceEnv("android")
        
        if networkEnv is None:
            networkEnv = NetworkEnv("direct")

        self.deviceEnv = deviceEnv
        self.networkEnv = networkEnv

    def setDeviceEnv(self,deviceEnv):
        self.deviceEnv = deviceEnv

    def setNetworkEnv(self,networkEnv):
        self.networkEnv = networkEnv

    




    

