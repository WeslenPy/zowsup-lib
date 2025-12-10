# coding=UTF-8
import sys
import base64

from zowsuplib.common.consolemain import ConsoleMain
from zowsuplib.yowsup.config.manager import ConfigManager
from zowsuplib.yowsup.axolotl.factory import AxolotlManagerFactory
from zowsuplib.conf.constants import SysVar, GlobalVar
from zowsuplib.common.utils import Utils


class Export6(ConsoleMain):

    def run(self,params,options):

        if len(params)<1:
            print("NOT ENOUGH PARAMS")

        self.commonOptionsProcess(options)

        numarr = params[0].split(",")
        for number in numarr:
            config_manager = ConfigManager()
            # Carrega config usando profile_name = número (ProfileConfig / MySQL)
            config = config_manager.load(number, profile_only=True)
            kp = config.client_static_keypair
            pk1 = str(base64.b64encode(kp.public.data),"UTF-8")
            sk1 = str(base64.b64encode(kp.private.data),"UTF-8")
            db = AxolotlManagerFactory().get_manager(number,number)
            pk2 = str(base64.b64encode(db.identity.publicKey.serialize()[1:]),'UTF-8')
            sk2 = str(base64.b64encode(db.identity.privateKey.serialize()),'UTF-8') 
            sixth = str(base64.b64encode(config.phone.encode()+"#".encode()+config.id),"UTF-8")
            
            print(f"{config.phone},{pk1},{sk1},{pk2},{sk2},{sixth}")

if __name__ == "__main__":

    GlobalVar.WANUMTYPE = 1     

    SysVar.loadConfig()       
    params,options = Utils.cmdLineParser(sys.argv)
    Export6().run(params,options)    



    








