from zowsuplib.yowsup.profile.profile import YowProfile
from ...common import YowConstants
from ...layers.axolotl.no_target_exception import NoTargetException
from zowsuplib.proto.e2e_pb2 import Message
from ...layers.axolotl.protocolentities import *
from ...layers.auth.layer_authentication import YowAuthenticationProtocolLayer
from ...layers.protocol_groups.protocolentities import InfoGroupsIqProtocolEntity, InfoGroupsResultIqProtocolEntity
from zowsuplib.axolotl.protocol.whispermessage import WhisperMessage
from zowsuplib.axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage
from ...layers.protocol_messages.protocolentities.message import MessageMetaAttributes
from ...layers.axolotl.protocolentities.iq_keys_get_result import MissingParametersException
from ...layers.protocol_contacts.protocolentities  import *
from ...axolotl import exceptions
from .layer_base import AxolotlBaseLayer
from ...common.tools import WATools
from ...layers.protocol_acks.protocolentities.ack_incoming import IncomingAckProtocolEntity

from ...structs import  ProtocolTreeNode
import base64,os

import logging

from loguru import logger


class AxolotlSendLayer(AxolotlBaseLayer):
    MAX_SENT_QUEUE = 256

    def __init__(self):
        super(AxolotlSendLayer, self).__init__()

        self.sessionCiphers = {}
        self.groupCiphers = {}

        self.sentQueue = []

    def __str__(self):
        return "Axolotl Layer"
    

    def send(self, node):          
        if node.tag == "message" and node["to"] not in self.skipEncJids:
            self.processPlaintextNodeAndSend(node)
        else:
            self.toLower(node)

    def receive(self, protocolTreeNode):
        def on_get_keys_success(node, retry_entity, success_jids, errors):                        
            if len(errors):                
                self.on_get_keys_process_errors(errors)
            elif len(success_jids) == 1:                                        
                self.processPlaintextNodeAndSend(node, retry_entity)
                #self.sendToContactsWithSessions(node, success_jids) 
                #self.sendToGroupWithSessions(node,None)
            else:
                raise NotImplementedError()

        if not self.processIqRegistry(protocolTreeNode):
            if protocolTreeNode.tag == "receipt":
                '''
                Going to keep all group message enqueued, as we get receipts from each participant
                So can't just remove it on first receipt. Therefore, the MAX queue length mechanism should better be working
                '''
                messageNode = self.getEnqueuedMessageNode(protocolTreeNode["id"], protocolTreeNode["participant"] is not None)


                if  protocolTreeNode["type"] == "retry":
                    retryReceiptEntity = RetryIncomingReceiptProtocolEntity.fromProtocolTreeNode(protocolTreeNode)
                    self.toLower(retryReceiptEntity.ack().toProtocolTreeNode()) #对重试那个包的ack，遵循协议    
                    if messageNode :
                        logger.info(f"Got retry to from {protocolTreeNode['from']} for message {protocolTreeNode['id']}, and Axolotl layer has the message")
                        self.getKeysFor(
                            [protocolTreeNode["participant"] or protocolTreeNode["from"]],
                            lambda successJids, errors: on_get_keys_success(messageNode, retryReceiptEntity, successJids, errors)
                        )         
                    else:
                        logger.debug("ignore retry receipt, because message not found in Axolotl")               

                else:
                    logger.debug("bubbling non-retry-receipt upwards")
                    self.toUpper(protocolTreeNode)                    


    def on_get_keys_process_errors(self, errors):
        # type: (dict) -> None
        for jid, error in errors.items():
            if isinstance(error, MissingParametersException):
                logger.error(f"Failed to create prekeybundle for {jid}, user had missing parameters: {error.parameters}, "
                             "is that a valid user?")                
            elif isinstance(error, exceptions.UntrustedIdentityException):
                logger.error(f"Failed to create session for {jid} as user's identity is not trusted. ")
            else:
                logger.error(f"Failed to process keys for {error[0]}, is that a valid user? Exception: {error[1]}")

    def processPlaintextNodeAndSend(self, node, retryReceiptEntity = None):
        if "," in node["to"]:
            #多个目标，直接发
            jids = node["to"].split(",")
            logger.info("multi target send detect")                        
            #目标是第一个人
            node["to"] = jids[0]
            self.ensureSessionsAndSendToContacts(node, jids) 
        else:
            #单个目标，找到这个目标的所有设备来发
            #             
            account = node["to"].split('@')[0]        
            isGroup = YowConstants.WHATSAPP_GROUP_SERVER in node["to"] or  "broadcast" in node["to"]

            #isGroup= False

            def on_iq_success(result, original_iq_entity): 
                entity = DevicesResultSyncIqProtocolEntity.fromProtocolTreeNode(result)
                jids = entity.collectAllResultJids()
            
                self.ensureSessionsAndSendToContacts(node, jids)

            def on_iq_error(entity, original_iq_entity): 
                logger.error("Failed to sync user devices")
                        
            
            if isGroup:                
                self.sendToGroup(node, retryReceiptEntity)
            else:                                             
                if ":" in account:
                    #指定设备
                    accounts = [account]
                    #获取account相关的所有accounts
                    jids = ["%s@%s" % (r,YowConstants.WHATSAPP_SERVER) for r in accounts]

                    self.ensureSessionsAndSendToContacts(node, jids)                    
                elif  "lid" in node["to"]:
                    self.ensureSessionsAndSendToContacts(node, [node["to"]])
                else :                    
                    #不指定设备，需要查客户所有的终端                                        
                    entity = DevicesGetSyncIqProtocolEntity([node["to"]])
                    self._sendIq(entity, on_iq_success, on_iq_error)                                

    def enqueueSent(self, node):
        logger.debug("enqueueSent(node=[omitted])")
        if len(self.sentQueue) >= self.__class__.MAX_SENT_QUEUE:
            logger.warning("Discarding queued node without receipt")
            self.sentQueue.pop(0)
        self.sentQueue.append(node)

    def getEnqueuedMessageNode(self, messageId, keepEnqueued = False):
        for i in range(0, len(self.sentQueue)):
            if self.sentQueue[i]["id"] == messageId:
                if keepEnqueued:
                    return self.sentQueue[i]
                return self.sentQueue.pop(i)
            
    def sendEncEntities(self, node, encEntities, participant=None,tctoken=None):
        logger.debug(f"sendEncEntities(node=[omitted], encEntities=[omitted], participant={participant})")

        message_attrs = MessageMetaAttributes.from_message_protocoltreenode(node)
        message_attrs.participant = participant        
        messageEntity = EncryptedMessageProtocolEntity(
            encEntities,
            node["type"],
            message_attrs
        )
                

        if participant is None:        
            self.enqueueSent(node)
            
        nodeSend = messageEntity.toProtocolTreeNode()
        #把biz节点复制转发

        if participant is None:        
            self.enqueueSent(node)

        nodeSend = messageEntity.toProtocolTreeNode()
        #把biz节点复制转发

        if node.getAttributeValue("category") == "peer":
            pass
        else:
            reporting = ProtocolTreeNode("reporting")
            reporting_token = ProtocolTreeNode("reporting_token",{"v":"2"})
            reporting_token.setData(os.urandom(16))            
            reporting.addChild(reporting_token)
            nodeSend.addChild(reporting)

        if tctoken:            
            tctoken = ProtocolTreeNode("tctoken",{},None,tctoken)
            nodeSend.addChild(tctoken)            

        biz = node.getChild("biz")
        if biz is not None:
            nodeSend.addChild(biz)

        profile = self.getProp("profile")
        if profile.config.device_identity is not None:                
            diddata = base64.b64decode(profile.config.device_identity)
            did = ProtocolTreeNode("device-identity", {},None,diddata)
            nodeSend.addChild(did)
        
        self.toLower(nodeSend)


    def sendToContact(self, node):
        
        recipient_id = node["to"].split('@')[0]
        protoNode = node.getChild("proto")
        messageData = protoNode.getData()
        ciphertext = self.manager.encrypt(
            recipient_id,
            messageData
        )           

        mediaType = protoNode["mediatype"]
        return self.sendEncEntities(node, [EncProtocolEntity(EncProtocolEntity.TYPE_MSG if ciphertext.__class__ == WhisperMessage else EncProtocolEntity.TYPE_PKMSG, 2, ciphertext.serialize(), mediaType)])

    def sendToContactAsPkmsg(self, node):

        recipient_id = node["to"].split('@')[0]
        protoNode = node.getChild("proto")
        messageData = protoNode.getData()
        mediaType = protoNode["mediatype"]
        
        to_jid = node["to"]
        if "@" not in to_jid:
            to_jid = f"{to_jid}@{YowConstants.WHATSAPP_SERVER}"
        
        recipientId, a, deviceid = WATools.jidDecode(to_jid)
        
        session_backup = None
        had_session = False
        if self.manager.session_exists(to_jid):
            try:
                session_record = self.manager._store.loadSession(recipientId, deviceid)
                session_backup = session_record
                had_session = True
                logger.debug(f"Sessão existente encontrada para {to_jid}, será deletada temporariamente")
            except Exception as e:
                logger.warning(f"Erro ao carregar sessão para backup: {e}")
        
        if had_session:
            try:
                self.manager._store.deleteSession(recipientId, deviceid)
                logger.debug(f"Sessão deletada temporariamente para {to_jid}")
            except Exception as e:
                logger.warning(f"Erro ao deletar sessão: {e}")
        
        def on_get_keys_success(node, success_jids, errors):
            try:
                if len(errors):
                    self.on_get_keys_process_errors(errors)
                    if had_session and session_backup:
                        try:
                            self.manager._store.storeSession(recipientId, deviceid, session_backup)
                            logger.debug(f"Sessão restaurada para {to_jid}")
                        except Exception as e:
                            logger.warning(f"Erro ao restaurar sessão: {e}")
                    return
                
                if len(success_jids) == 0:
                    logger.error(f"Nenhuma PreKey obtida para {to_jid}, não é possível enviar como PKMSG")
                    if had_session and session_backup:
                        try:
                            self.manager._store.storeSession(recipientId, deviceid, session_backup)
                            logger.debug(f"Sessão restaurada para {to_jid}")
                        except Exception as e:
                            logger.warning(f"Erro ao restaurar sessão: {e}")
                    return
                
                jid = success_jids[0]
                recipient_id = jid.split('@')[0]
                
                ciphertext = self.manager.encrypt(recipient_id, messageData)
                
                if ciphertext.__class__ != PreKeyWhisperMessage:
                    logger.warning(f"Esperado PreKeyWhisperMessage, mas obteve {ciphertext.__class__.__name__}")
                
                enc_entity = EncProtocolEntity(
                    EncProtocolEntity.TYPE_PKMSG,
                    2,
                    ciphertext.serialize(),
                    mediaType
                )
                
                self.sendEncEntities(node, [enc_entity])
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem como PKMSG: {e}")
                if had_session and session_backup:
                    try:
                        self.manager._store.storeSession(recipientId, deviceid, session_backup)
                        logger.debug(f"Sessão restaurada após erro para {to_jid}")
                    except Exception as restore_error:
                        logger.warning(f"Erro ao restaurar sessão após erro: {restore_error}")
        
        self.getKeysFor(
            [to_jid],
            lambda success_jids, errors: on_get_keys_success(node, success_jids, errors)
        )

    def ensureSessionsAndSendToContacts(self, node, jids):

        logger.debug(f"ensureSessionsAndSendToContacts(node=[omitted], jids={jids})")
        allJids = []
        jidsNoSession = []

        for jid in jids:
            if not self.manager.session_exists(jid.split('@')[0]):
                jidsNoSession.append(jid)
            else:
                allJids.append(jid)
        
        def on_get_keys_success(node, success_jids, errors):                                    
            if len(errors):
                self.on_get_keys_process_errors(errors)
                return 

            allJids.extend(success_jids)
            #所有能成功建立session的，都发        
                   
            if len(success_jids)>0:
                if node.getAttributeValue("category")=="peer":                    
                    self.sendToPeerWithSessions(node,allJids[0])
                else:
                    self.sendToContactsWithSessions(node, allJids)

        if len(jidsNoSession):
            self.getKeysFor(jidsNoSession, lambda successJids, errors: on_get_keys_success(node, successJids, errors))

        else:
            if node.getAttributeValue("category")=="peer":                    
                self.sendToPeerWithSessions(node,allJids[0])
            else:
                self.sendToContactsWithSessions(node, allJids) 

    def sendToPeerWithSessions(self,node,jid):    
    
        protoNode = node.getChild("proto")
        messageData = protoNode.getData()         
        ciphertext = self.manager.encrypt(
            jid.split('@')[0],                
            messageData                
        )             
        encEntities = [
            EncProtocolEntity(
                    EncProtocolEntity.TYPE_MSG if ciphertext.__class__ == WhisperMessage else EncProtocolEntity.TYPE_PKMSG
                , 2, ciphertext.serialize(), protoNode["mediatype"],  jid=None
            )
        ]       
        self.sendEncEntities(node, encEntities)  


    def sendToContactsWithSessions(self, node, jids, retryCount=0):

        jids = jids or []
        targetJid = node["to"]
        db = self.getStack().getProp("profile").axolotl_manager
        tctoken = db._store.getTcToken(targetJid)        
        protoNode = node.getChild("proto")
        encEntities = []       
        messageData = protoNode.getData()        
        participant = jids[0] if len(jids) == 1 and retryCount > 0 else None         

        for jid in jids:            
            messageData = protoNode.getData()
            
            ciphertext = self.manager.encrypt(
                jid.split('@')[0],                
                messageData     
            )              
            
            encEntities.append(
                EncProtocolEntity(
                        EncProtocolEntity.TYPE_MSG if ciphertext.__class__ == WhisperMessage else EncProtocolEntity.TYPE_PKMSG
                    , 2, ciphertext.serialize(), protoNode["mediatype"],  jid=None if participant else jid
                )
            )
        
        self.sendEncEntities(node, encEntities, participant,tctoken)

    def sendToGroupWithSessions(self, node, jidsNeedSenderKey = None, retryCount=0):

        logger.debug(
            "sendToGroupWithSessions(node=[omitted], jidsNeedSenderKey=%s, retryCount=%d)" % (jidsNeedSenderKey, retryCount)
        )
        jidsNeedSenderKey = jidsNeedSenderKey or []
        groupJid = node["to"]
        protoNode = node.getChild("proto")
        encEntities = []
        participant = jidsNeedSenderKey[0] if len(jidsNeedSenderKey) == 1 and retryCount > 0 else None 
        if len(jidsNeedSenderKey):
            senderKeyDistributionMessage = self.manager.group_create_skmsg(groupJid)
            for jid in jidsNeedSenderKey:
                message =  self.serializeSenderKeyDistributionMessageToProtobuf(node["to"], senderKeyDistributionMessage)
                if retryCount > 0:
                    message.MergeFromString(protoNode.getData())
                ciphertext = self.manager.encrypt(jid.split('@')[0], message.SerializeToString())
                encEntities.append(
                    EncProtocolEntity(
                            EncProtocolEntity.TYPE_MSG if ciphertext.__class__ == WhisperMessage else EncProtocolEntity.TYPE_PKMSG
                        , 2, ciphertext.serialize(), protoNode["mediatype"],  jid=None if participant else jid,count=str(retryCount)
                    )
                )

        if not retryCount:
            messageData = protoNode.getData()
            try:
                ciphertext = self.manager.group_encrypt(groupJid, messageData)
            except exceptions.NoSessionException as e:
                # Sender key não existe, criar antes de criptografar
                logger.warning(f"Sender key não encontrado para grupo {groupJid}, criando... (erro: {e})")
                self.manager.group_create_skmsg(groupJid)
                # Tentar criptografar novamente
                try:
                    ciphertext = self.manager.group_encrypt(groupJid, messageData)
                except exceptions.NoSessionException as e2:
                    logger.error(f"Falha ao criptografar mensagem para grupo {groupJid} mesmo após criar sender key: {e2}")
                    raise
            mediaType = protoNode["mediatype"]
            encEntities.append(EncProtocolEntity(EncProtocolEntity.TYPE_SKMSG, 2, ciphertext, mediaType))

        self.sendEncEntities(node, encEntities, participant)

    def ensureSessionsAndSendToGroup(self, node, jids):
        logger.debug(f"ensureSessionsAndSendToGroup(node=[omitted], jids={jids})")

        allJids = []
        jidsNoSession = []    
        standardJids = []
        for jid in jids:
            standardJids.append(jid.replace(".0:0","").replace(".1:",":"))

        for jid in standardJids:
            if not self.manager.session_exists(jid.split('@')[0]):          
                jidsNoSession.append(jid) #如果是xxxx.0:0, 规范是不加任何后缀，否则解码后就会对应不上)        
            else:
                allJids.append(jid)

        def on_get_keys_success(node, success_jids, errors):
            if len(errors):
                self.on_get_keys_process_errors(errors)
            allJids.extend(success_jids)
            self.sendToGroupWithSessions(node, allJids)
                        
        if len(jidsNoSession):
            self.getKeysFor(jidsNoSession, lambda successJids, errors: on_get_keys_success(node, successJids, errors))
        else:
            self.sendToGroupWithSessions(node, standardJids)

    def sendToGroup(self, node, retryReceiptEntity = None):


        logger.debug(f"sendToGroup(node={node}, retryReceiptEntity={retryReceiptEntity})")



        retry_info = f"[retry_count={retryReceiptEntity.getRetryCount()}, retry_jid={retryReceiptEntity.getRetryJid()}]" if retryReceiptEntity is not None else "[None]"
        logger.debug(f"sendToGroup(node=[omitted], retryReceiptEntity={retry_info})")

        groupJid = node["to"]        
        logger.debug(f"groupJid={groupJid}")
        ownJid = self.getLayerInterface(YowAuthenticationProtocolLayer).getUsername(True)
        senderKeyRecord = self.manager.load_senderkey(node["to"])

        def sendToGroup(resultNode, requestEntity):
            groupInfo = InfoGroupsResultIqProtocolEntity.fromProtocolTreeNode(resultNode)
            jids = list(groupInfo.getParticipants().keys()) #keys in py3 returns dict_keys            
            if ownJid in jids:
                jids.remove(ownJid)            

            return self.ensureSessionsAndSendToGroup(node, jids)

        if groupJid=="status@broadcast":
            # Para status@broadcast, obtém todos os contatos conhecidos

            profile: YowProfile = self.getProp("profile")
            logger.debug("Tentando obter identidades como fallback para status@broadcast")
            identity_store = profile.axolotl_manager._store

            logger.debug(f"identity_store: {identity_store}")
            logger.info(f"profile: {profile}")
        
            jids = identity_store.getAllContact()

            logger.debug(f"jids: {jids}")
            
            if jids:
                logger.info(f"Enviando status para {len(jids)} contatos via status@broadcast")
                self.ensureSessionsAndSendToGroup(node, jids)
            else:
                logger.warning("Nenhum contato encontrado para status@broadcast, enviando sem destinatários específicos")
                # Envia mesmo assim - o WhatsApp pode lidar com isso (pode ser que não tenha contatos ainda)
                self.ensureSessionsAndSendToGroup(node, [])   

        elif groupJid.endswith("@broadcast"):
            jids = self._manager._store.findParticipantsByBcid(groupJid)            
            self.ensureSessionsAndSendToGroup(node, jids)   

        elif senderKeyRecord.isEmpty():
            logger.debug("senderKeyRecord is empty, requesting group info")
            groupInfoIq = InfoGroupsIqProtocolEntity(groupJid)            
            self._sendIq(groupInfoIq, sendToGroup)            
        else:
            logger.debug("We have a senderKeyRecord")
            retryCount = 0
            jidsNeedSenderKey = []
            if retryReceiptEntity is not None:
                retryCount = retryReceiptEntity.getRetryCount()
                jidsNeedSenderKey.append(retryReceiptEntity.getRetryJid())            
            self.sendToGroupWithSessions(node, jidsNeedSenderKey, retryCount)

    def serializeSenderKeyDistributionMessageToProtobuf(self, groupId, senderKeyDistributionMessage, message = None):
        m = message or Message()
        m.sender_key_distribution_message.group_id = groupId
        m.sender_key_distribution_message.axolotl_sender_key_distribution_message = senderKeyDistributionMessage.serialize()
        m.sender_key_distribution_message.axolotl_sender_key_distribution_message = senderKeyDistributionMessage.serialize()
        # m.conversation = text
        return m
    


