import os,sys
sys.path.append(os.getcwd())

# coding=UTF-8
from loguru import logger

from yowsup.stacks import YowStackBuilder
from yowsup.layers import YowLayerEvent
from yowsup.layers.protocol_iq.layer import YowIqProtocolLayer
from yowsup.layers.network import YowNetworkLayer
from app.yowbot_layer import SendLayer
from conf.constants import SysVar
from yowsup.common.tools import WATools
from axolotl.util.keyhelper import KeyHelper
from yowsup.profile.profile import YowProfile
from proto import wsend_pb2
from app.bot_env import BotEnv
from app.device_env import DeviceEnv
from app.network_env import NetworkEnv
from app.yowbot_values import YowBotType
from app.param_not_enough_exception import ParamsNotEnoughException
from yowsup.structs import ProtocolEntity
import names

import os,time,threading,uuid,json,inspect,time,socks

class BotCmd(object):
    def __init__(self, cmd , desc, order = 0):
        self.cmd  = cmd
        self.desc = desc
        self.order = order
    def __call__(self, fn):
        fn.cmd = self.cmd
        fn.desc = self.desc
        fn.order = self.order
        return fn   
        
class YowBot: 
                    
    def __init__(self,bot_id,env,bot_type=YowBotType.TYPE_RUN_MANUAL,sysvar_context=None):     
        self.botId = bot_id                
        # Cada bot mantém o contexto SysVar que estava ativo durante a criação
        # para que a thread interna use caminhos isolados por conta.
        self.sysvar_context = sysvar_context or SysVar.capture_context()
        stackBuilder = YowStackBuilder()
        self.sendLayer = SendLayer(self)        
        self.env = env if env is not None else BotEnv(deviceEnv=DeviceEnv("android"),networkEnv=NetworkEnv("direct"))

        if self.env.deviceEnv.getOSName() in ["Android","SMBA"]:
            self.idType = ProtocolEntity.ID_TYPE_ANDROID            
        else:
            self.idType = ProtocolEntity.ID_TYPE_IOS
                
        if self.botId is not None:   
            # Usa apenas o identificador lógico da conta (botId) como profile_name
            self.profile = YowProfile(self.botId)   
            self.env.networkEnv.updateByWaNum(self.botId)            
            self.sendLayer.db = self.profile.axolotl_manager  
            
        self._stack = stackBuilder\
            .pushDefaultLayers()\
            .push(self.sendLayer)\
            .build()
        
        self._stack.setProp("env",self.env)        
        self._stack.setProp("ID_TYPE",self.idType)
        # Identificador lógico da conta para camadas inferiores (ping thread, logs)
        self._stack.setProp("botId", self.botId)
        # Mantém a conexão viva com pings mais frequentes (30s) para evitar timeout de NAT/rede
        self._stack.setProp(YowIqProtocolLayer.PROP_PING_INTERVAL, 30)
        self.bot_type = bot_type              
        self.callback = self.onCallback      
        self.inloop = False              
        self.pairPhoneNumber=None
        self.cmdEventMap = {}
        
        if self.bot_type==YowBotType.TYPE_REG_COMPANION_SCANQR or self.bot_type==YowBotType.TYPE_REG_COMPANION_LINKCODE:                        
            identity = KeyHelper.generateIdentityKeyPair()
            self._stack.setProp("reg_info",{
                "keypair":WATools.generateKeyPair(),
                "regid": KeyHelper.generateRegistrationId(False),
                "identity": identity,            
                "signedprekey": KeyHelper.generateSignedPreKey(identity,0)
            })
            self._stack.setProp("botType",self.bot_type)
        else:
            self._stack.setProp("botType",YowBotType.TYPE_RUN_AUTO)

        self.cmdList = {}
        if self.botId is not None:
            self._stack.setProfile(self.profile)                                  
            members = inspect.getmembers(YowBot, predicate = inspect.isfunction)
            for m in members:            
                if hasattr(m[1], "desc"):  
                    self.cmdList[m[1].cmd] = m[1]       

    def runAsThread(self):
        def _runner():
            if self.sysvar_context:
                SysVar.apply_context(self.sysvar_context)
            self.run()

        self.thread = threading.Thread(target=_runner)
        self.thread.daemon=True       
        self.thread.start()    

    def onCallback(self,event=None,message=None,cmdresult=None,logger=logger,caller=None):

        if cmdresult is not None:
            logger.info(cmdresult)

        if event is not None:   
            if event.HasField("contact_update"):
                logger.info(f"Contact {event.contact_update.target} notification:  {event.contact_update.key} : {event.contact_update.value}")                     
            elif event.HasField("msg_log"):
                if event.msg_log.error_code:
                    logger.info(f"MsgLog {wsend_pb2.MsgLogItem.Status.Name(event.msg_log.status)}-{event.msg_log.error_code} (ID={event.msg_log.msg_id}) from {event.bot_id}")
                else:
                    logger.info(f"MsgLog {wsend_pb2.MsgLogItem.Status.Name(event.msg_log.status)}(ID={event.msg_log.msg_id}) from {event.msg_log.target}")
            else:
                logger.info(f"Event {wsend_pb2.BotEvent.Event.Name(event.event)} from {event.bot_id}")
            
        if message is not None:
            if message.HasField("participant"):
                src = f"{message.sender}::{message.participant}"
            else:
                src = message.sender
            dst = message.target                
            if message.HasField("text_message"):
                logger.info(f'Receive text message "{message.text_message.text}" from {src} to {dst}')  
            else:
                logger.info(f"Receive {wsend_pb2.Message.Type.Name(message.type)} message from {src} to {dst}") 


    def getCmdList(self):
        return self.cmdList

    def run(self):     
        
        if self.bot_type==YowBotType.TYPE_REG_COMPANION_SCANQR or self.bot_type==YowBotType.TYPE_REG_COMPANION_LINKCODE:
            logger.info("Pairing-Device Registration Start")
        else:
            logger.info("Login start")           
            logger.info(f"AccountFile={self.profile}")
                           
        try :                            
            self.inloop = True            
            self._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))                                         
            self._stack.loop()           
            logger.info("LOOP ENDED")

        except KeyboardInterrupt as erro:      
            logger.info("KeyboardInterrupt: CLOSE RUNNER ")
            self.inloop = False
            self.disconnect()                   
        except socks.SOCKS5Error:
            logger.info("PROXY ERROR, CHANGE IP AND RECONNECT")
            self.env.networkEnv.changeIP(self.bot_api.botId)     
        except OSError:
            logger.info("OS ERROR, CLOSE RUNNER")
            self.inloop = False 
            self.disconnect()                          
    
            
    def waitLogin(self):
        return self.sendLayer.waitLogin()

    def printUsage():
        members = inspect.getmembers(YowBot, predicate = inspect.isfunction)

        cmdmembers = list(filter(lambda m: hasattr(m[1], "desc"), members))

        cmdmembers.sort(key=lambda m: m[1].cmd)
        
        print("[command]                     |   [description]")
        print("----------------------------------------------------------------------------")
        for m in cmdmembers:            
            if hasattr(m[1], "desc"):                
                fn = m[1]
                print(f"{m[1].cmd.ljust(30,' ')}|\t{m[1].desc.ljust(50,' ')}")
        print("----------------------------------------------------------------------------")

    def disconnect(self):        
        self.sendLayer.userQuit = True        
        self.sendLayer.setProp("FORCEQUIT",1)                  
        if self.inloop:
            self._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        else:
            self.sendLayer.onDisconnected(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))  

    def quit(self)  :               
        self.disconnect()

    def callDirect(self,name,params,options):
        cmdId = None
        fn = self.cmdList[name] if name in self.cmdList else None   
        if fn is not None:            
            try:
                cmdId = fn(self,params,options) 
                if cmdId not in self.cmdEventMap:
                    #非直返结果
                    self.cmdEventMap[cmdId] = {"event":threading.Event()}
            except ParamsNotEnoughException:
                return None,{"code":-1,"msg":"Params Not Enough"}
                        
            if cmdId is None:
                return None,{"code":-3,"msg":"No CmdId Return"}
            
            return cmdId,None
        else:
            logger.info(f"command {name} not found")
            return None,{"code":-2,"msg":"Command Not Found"}

    def checkCmdResult(self,cmdId):        
        if cmdId not in self.cmdEventMap:
            return False        
        obj =self.cmdEventMap[cmdId]                
        return  obj["event"].isSet() 
    
    def getCmdResultDirect(self,cmdId):                
        if cmdId in self.cmdEventMap:
            obj =self.cmdEventMap[cmdId]
            del self.cmdEventMap[cmdId]
            if "error" in obj :
                return None,obj["error"]        
            elif "result" in obj :
                return obj["result"],None
            else:
                return None,None
        else:
            return None,{"code":-4,"msg":"cmdId not found"}

    def getCmdResult(self,cmdId,waitTime):
        if cmdId in self.cmdEventMap:
            obj =self.cmdEventMap[cmdId]
            if obj["event"].wait(waitTime):
                del self.cmdEventMap[cmdId]
                if "error" not in obj :
                    return obj["result"],None
                else:
                    return None,obj["error"]        
            else:
                return None,{"code":-999,"msg":"timeout"}                
        else:
            return None,{"code":-4,"msg":"cmdId not found"}
        
    def setCmdError(self,cmdId,error):
        if cmdId in self.cmdEventMap: 
            obj = self.cmdEventMap[cmdId]
            obj["error"] = error         
            obj["event"].set()  

    def setCmdResult(self,cmdId,result):

        if cmdId in self.cmdEventMap:            
            obj = self.cmdEventMap[cmdId]
            obj["result"] = result
            if obj["event"]:
                if obj["event"]=="callback":
                    self.callback(cmdresult={
                        "botId": self.botId,
                        "cmdId":cmdId,
                        "result":result,
                        "timestamp":int(time.time())
                    })
                else:                                   
                    obj["event"].set()    
        else:
            e = threading.Event()
            e.set()            
            self.cmdEventMap[cmdId] = {"result":result,"event":e}          

    def callWaitResult(self,name,params,options,waitResultTime=20):

        cmdId,errMsg = self.callDirect(name,params,options)

        if cmdId is None:
            logger.info(f"Command {name} error(execute stage），info={errMsg}")                  
            return None,errMsg
        
        result,errMsg = self.getCmdResult(cmdId,waitResultTime)
        
        if errMsg is not None:
            logger.info(f"Command {name} error(result stage），info={errMsg}") 
            return None,errMsg

        else:            
            logger.info(f"Command {name} complete，result={json.dumps(result)}")
            return result,None

    '''
    =========================THE FOLLOWING is THE DEMO COMMANDS ==========================
    '''
    
    @BotCmd("msg.send","send message")
    def sendMsg(self,params,options):                 
        return self.sendLayer.sendMsg(params,options)
    
    @BotCmd("account.getsentcount", "get count of sent messages by account and recipient")
    def getSentMessagesCount(self, params, options):
        """
        Retorna a contagem de mensagens enviadas pela conta.
        
        Parâmetros opcionais:
        - recipient: filtrar por destinatário específico
        - message_type: filtrar por tipo de mensagem (TEXT, IMAGE, etc.)
        - status: filtrar por status (EXECUTED, SENT, ERROR)
        """
        from app.db import get_sent_messages_count
        
        recipient = options.get("recipient") if "recipient" in options else None
        message_type = options.get("message_type") if "message_type" in options else None
        status = options.get("status") if "status" in options else None
        
        result = get_sent_messages_count(
            phone=self.botId,
            recipient=recipient,
            message_type=message_type,
            status=status,
        )
        
        return result    

    @BotCmd("msg.sendmedia","send media message")
    def sendMediaMsg(self,params,options):                    
        return self.sendLayer.sendMediaMsg(params,options)  
    
    @BotCmd("msg.revoke","revoke message")
    def revokeMsg(self,params,options):
        return self.sendLayer.revokeMsg(params,options)

    @BotCmd("msg.edit","edit message")
    def editMsg(self,params,options):
        return self.sendLayer.editMsg(params,options)

    @BotCmd("contact.sync", "sync contacts")
    def syncContacts(self,params,options):                
        return self.sendLayer.syncContacts(params,options)

    @BotCmd("account.init", "initialize the account (for the 1st login)")        
    def intialize(self,params,options):    
        time.sleep(1)  #wait 5 seconds
        self.sendLayer.getConfig(params,options)    
        time.sleep(2)                
        self.setSelfName(params,options)
        
        # Atualiza status da conta no banco de dados - marca como inicializada
        if self.botId is not None:
            from app.db import update_account_status
            update_account_status(self.botId, is_initialized=True)
        
        return "JUSTWAIT"     
    
    @BotCmd("group.getinvite", "get the invite code of group")
    def getgroupinvite(self,params,options):
        return self.sendLayer.getGroupInvite(params,options)    
        
    @BotCmd("group.join", "join group with an invite code")        
    def joinGroupWithCode(self,params,options):   
        return self.sendLayer.joinGroupWithCode(params,options)

    @BotCmd("group.leave", "leave group")        
    def leavegroup(self,params,options):   
        return self.sendLayer.leaveGroup(params,options)

    @BotCmd("account.setavatar", "set account avatar")
    def setAvatar(self,params,options):                
        return self.sendLayer.setAvatar(params,options)  
    
    @BotCmd("contact.trust","trust contact")
    def trustContact(self,params,options):
        return self.sendLayer.trustContact(params,options)    

    @BotCmd("account.setname", "set account name")
    def setSelfName(self, params,options):            
        if len(params)==0:
            params=[names.get_full_name()]
        self.profile.config.pushname = params[0]
        self.profile.write_config(self.profile.config)                         
        if self.env.deviceEnv.getOSName() in ["SMBA","SMB iOS"]:
            #call the api if business 
            return self.sendLayer.setBusinessName(params,options)
        else:            
            id = str(uuid.uuid4())
            self.sendLayer.setCmdResult(id,{
                "status":"OK"
            })        
            return id
        
    @BotCmd("account.setemail", "set account email")
    def setEmail(self,params,options):
        self.sendLayer.setEmail(params,options)   
        time.sleep(2)
        return self.sendLayer.verifyEmail([],{})
    
    @BotCmd("account.getemail", "get account email")
    def getEmail(self,params,options):
        return self.sendLayer.getEmail(params,options)  
    
    @BotCmd("account.verifyemail", "request email verification")
    def verifyEmail(self,params,options):
        return self.sendLayer.verifyEmail(params,options)  
    
    @BotCmd("account.verifyemailcode", "verify email code")
    def verifyEmailCode(self,params,options):
        return self.sendLayer.verifyEmailCode(params,options)          
            
    @BotCmd("account.set2fa","set account 2fa")
    def set2FA(self,params,options):
        return self.sendLayer.set2FA(params,options)

    @BotCmd("group.create","create a group")
    def makeGroup(self,params,options):
        return self.sendLayer.createGroup(params,options)
    
    @BotCmd("group.add","add member(s) to group")
    def groupAdd(self,params,options):
        return self.sendLayer.groupAdd(params,options)
    
    @BotCmd("group.promote","promote group member(s) to admin")
    def groupPromote(self,params,options):
        return self.sendLayer.groupPromote(params,options)

    @BotCmd("group.demote","demote group member(s) from admin")
    def groupDemote(self,params,options):
        return self.sendLayer.groupDemote(params,options)

    @BotCmd("group.remove","remove a member from group ")
    def groupRemove(self,params,options):
        return self.sendLayer.groupRemove(params,options)

    @BotCmd("group.info","show group information")
    def groupInfo(self,params,options):
        return self.sendLayer.groupInfo(params,options)

    @BotCmd("group.list","list all groups")
    def listGroups(self,params,options):
        return self.sendLayer.listGroups(params,options)


    @BotCmd("group.approve","approve participants to join the group")
    def groupApprove(self,params,options):
        self.sendLayer.groupApprove(params,options)

    @BotCmd("group.seticon","set icon for group")
    def setGroupPicture(self,params,options):
        return self.sendLayer.setGroupIcon(params,options)

    @BotCmd("account.getavatar", "get account avatar")
    def getSelfAvatar(self,params,options):
        return self.sendLayer.getAvatar(params,options)
    
    @BotCmd("contact.getavatar", "get account avatar")
    def getContactAvatar(self,params,options):
        return self.sendLayer.getAvatar(params,options)
    
    @BotCmd("md.link","link to companion device with qrcode-str")
    def multiDeviceLink(self,params,options):
        self.sendLayer.resetSync(params,options)
        time.sleep(3)
        self.sendLayer.multiDeviceLink(params,options)
        return "JUSTWAIT"
    
    @BotCmd("md.remove","remove companion device(s)")
    def multiDeviceRemove(self,params,options):
        return self.sendLayer.multiDeviceRemove(params,options)       
    
    @BotCmd("md.inputcode","input pair code for companion pairing")
    def inputPairingCode(self,params,options):
        return self.sendLayer.inputPairingCode(params,options)
                      
if __name__ == "__main__":    
    
    SysVar.loadConfig()  

    # default-env  android,direct
    env = BotEnv(
        deviceEnv = DeviceEnv("android",random=True), 
        networkEnv = NetworkEnv(NetworkEnv.TYPE_DIRECT)
    )

    bot = YowBot(botId="212719800440",env=env)

    bot.run()
    

    
        


                            

                            





