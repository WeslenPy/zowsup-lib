from .device_env_config import *


class DeviceEnv:

    ENV_MAP = {
        "android":EnvAndroid,
        "ios":EnvIos,
        "smb_android":EnvSmbAndroid,
        "smb_ios":EnvSmbIos,
      
    }    

    ENV_DICT = {
        1:"android",
        2:"smb_android",
        3:"ios",
        4:"smb_ios"  
    }

    def __init__(self,name,random=False,envObj=None):

        if random or envObj is None:
            self.obj = DeviceEnv.ENV_MAP[name].randomEnv()
            
        else:
            self.obj = DeviceEnv.ENV_MAP[name](
                version=envObj["version"],
                osVersion=envObj["osVersion"],
                deviceName=envObj["deviceName"],
                buildVersion=envObj["buildVersion"],
                manufacturer=envObj["manufacturer"],
                deviceModelType=envObj["deviceModelType"]
            )     

    def setDeviceModelType(self,value):
        self.obj.setDeviceModelType(value)

    def setPlatform(self,value):
        self.obj.setPlatform(value)

    def setVersion(self,value):
        self.obj.setVersion(value)

    def setManufacturer(self,value):
        self.obj.setManufacturer(value)

    def setDeviceName(self,value):
        self.obj.setDeviceName(value)

    def setOSVersion(self,value):
        self.obj.setOSVersion(value)

    def setBuildVersion(self,value):
        self.obj.setBuildVersion(value)

    def setOSName(self,value):
        self.obj.setOSName(value)

    def getPlatform(self):
        return self.obj.getPlatform()
    
    def getVersion(self):
        return self.obj.getVersion()
    
    def getManufacturer(self):
        return self.obj.getManufacturer()
    
    def getDeviceName(self):
        return self.obj.getDeviceName()
    
    def getDeviceName2(self):
        return self.obj.getDeviceName2()    
    
    def getOSVersion(self):
        return self.obj.getOSVersion()
    
    def getBuildVersion(self):
        return self.obj.getBuildVersion()
    
    def getOSName(self):
        return self.obj.getOSName()
    
    def getToken(self,number):
        return self.obj.getToken(number)
    
    def getUserAgent(self):
        return self.obj.getUserAgent()
    
    def getDeviceModelType(self):
        return self.obj.getDeviceModelType()
    


            


    


