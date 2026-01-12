from zowsuplib.yowsup.common.tools import Jid
from .layer_base import AxolotlBaseLayer
from .layer_send import AxolotlSendLayer

from ...layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from zowsuplib.proto.e2e_pb2 import Message
from ...layers.axolotl.protocolentities import *
from ...layers.protocol_messages.protocolentities.proto import ProtoProtocolEntity
from ...layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
from ...axolotl import exceptions

from zowsuplib.axolotl.untrustedidentityexception import UntrustedIdentityException

import logging
from loguru import logger
import time
from ...layers.protocol_messages.protocolentities.message import MessageMetaAttributes
from ...layers.protocol_messages.protocolentities.message_text import TextMessageProtocolEntity


class AxolotlReceivelayer(AxolotlBaseLayer):
    def __init__(self):
        super(AxolotlReceivelayer, self).__init__()
        self.v2Jids = [] #people we're going to send v2 enc messages
        self.sessionCiphers = {}
        self.groupCiphers = {}
        self.pendingIncomingMessages = {} #(jid, participantJid?) => message
        self._retries = {}

    def receive(self, protocolTreeNode):
        """
        :type protocolTreeNode: ProtocolTreeNode
        """        

        logger.info(f"receive: {protocolTreeNode}")
        if not self.processIqRegistry(protocolTreeNode):            
            if protocolTreeNode.tag == "message":
                logger.info(f"receive: message")
                self.onMessage(protocolTreeNode)
            elif protocolTreeNode.tag == "receipt":
                logger.info(f"receive: receipt - from={protocolTreeNode.getAttributeValue('from')}, type={protocolTreeNode.getAttributeValue('type')}, participant={protocolTreeNode.getAttributeValue('participant')}")
                #receipts will be handled by send layer                
                self.toUpper(protocolTreeNode)
            else:
                # Outros tipos de nós passam para cima
                self.toUpper(protocolTreeNode)            
        else:
            logger.info(f"receive: processIqRegistry")

    def processPendingIncomingMessages(self, jid, participantJid = None):
        conversationIdentifier = (jid, participantJid)
        if conversationIdentifier in self.pendingIncomingMessages:
            for messageNode in self.pendingIncomingMessages[conversationIdentifier]:
                self.onMessage(messageNode)

            del self.pendingIncomingMessages[conversationIdentifier]

    def onMessage(self, protocolTreeNode):          
        logger.debug(f"[AxolotlReceive] onMessage chamado - tag: {protocolTreeNode.tag}, from: {protocolTreeNode.getAttributeValue('from')}")
        encNode = protocolTreeNode.getChild("enc")                
        if encNode:            
            logger.debug(f"[AxolotlReceive] Mensagem criptografada encontrada, chamando handleEncMessage")
            self.handleEncMessage(protocolTreeNode)
        else:
            logger.debug(f"[AxolotlReceive] Mensagem não criptografada, enviando para layer superior")
            self.toUpper(protocolTreeNode)

    def handleEncMessage(self, node):                                
        """
        Processa mensagens criptografadas e trata exceções de descriptografia.
        
        Fluxo:
        1. Identifica o tipo de mensagem (SKMSG, PKMSG, MSG)
        2. Tenta descriptografar
        3. Trata exceções (InvalidMessageException, NoSessionException, etc.)
        """
        encMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)       
        isGroup =  node["participant"] is not None
        senderJid = node["participant"] if isGroup else node["from"]

        logger.debug(f"[AxolotlReceive] handleEncMessage: processando mensagem criptografada de {node['from'] or  'unknown'}")
        logger.debug(f"[AxolotlReceive] handleEncMessage: node: {node}")

        logger.debug(f"[AxolotlReceive] handleEncMessage: encMessageProtocolEntity: {encMessageProtocolEntity}")
        
        if node.getChild("enc")["v"] == "2" and node["from"] not in self.v2Jids:
            self.v2Jids.append(node["from"])

        try:
            handled = False
            if encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_SKMSG):
                logger.debug(f"[AxolotlReceive] handleEncMessage: mensagem TYPE_SKMSG (grupo)")
                handled = self.handleSenderKeyMessage(node)               
                           
            if not handled:                                                                 
                if encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_PKMSG):
                    logger.debug(f"[AxolotlReceive] handleEncMessage: mensagem TYPE_PKMSG (PreKey)")
                    self.handlePreKeyWhisperMessage(node)
                elif encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSG):
                    logger.debug(f"[AxolotlReceive] handleEncMessage: mensagem TYPE_MSG (Whisper)")
                    self.handleWhisperMessage(node)             
                else:
                    logger.warning(f"[AxolotlReceive] handleEncMessage: tipo de mensagem não reconhecido, enviando receipt")
                    self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())              

            self.reset_retries(node["id"])

        except exceptions.InvalidKeyIdException:
            logger.warning(f"Invalid KeyId for {encMessageProtocolEntity.getAuthor(False)}, going to send the receipt to ignore subsequence push")
            self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())
                   
            
        except exceptions.InvalidMessageException as e:
            try:
                author = encMessageProtocolEntity.getAuthor(False) if hasattr(encMessageProtocolEntity, 'getAuthor') else "unknown"
            except:
                author = node.get("from", "unknown")
            
            error_msg = str(e) if str(e) else "Invalid message (Bad MAC ou sessão desincronizada)"
            logger.warning(f"[AxolotlReceive] InvalidMessage para {author}: {error_msg}")
            
            retry_count = self._retries.get(node["id"], 0)
            if retry_count >= 2:
                # Tentou 3 vezes, provavelmente é um problema do remetente ou sessão muito desincronizada
                logger.warning(f"[AxolotlReceive] InvalidMessage após 2 tentativas para mensagem {node['id']}, enviando mensagem PKMSG para sincronização")
                self.send_pkmsg_for_invalid_message(node["from"], node["id"], node["participant"])
            else:
                # Envia retry para tentar sincronizar a sessão novamente
                logger.debug(f"[AxolotlReceive] Enviando retry para mensagem {node['id']} (tentativa {retry_count + 1}/2)")
                self.send_retry(node, self.manager.registration_id)                

        except exceptions.NoSessionException:            
            logger.warning(f"No session for {encMessageProtocolEntity.getAuthor(False)}, getting their keys now")
            self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())  

            conversationIdentifier = (node["from"], node["participant"])

            if conversationIdentifier not in self.pendingIncomingMessages:
                self.pendingIncomingMessages[conversationIdentifier] = []
            self.pendingIncomingMessages[conversationIdentifier].append(node)

            successFn = lambda successJids, b: self.processPendingIncomingMessages(*conversationIdentifier) if len(successJids) else None

            self.getKeysFor([senderJid], successFn)
        except exceptions.DuplicateMessageException:
            logger.warning("Received a message that we've previously decrypted, "
                           "going to send the delivery receipt myself")        
            self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())    

        except UntrustedIdentityException as e:
            if self.getProp(PROP_IDENTITY_AUTOTRUST, False):
                logger.warning(f"Autotrusting identity for {e.getName()}")
                self.manager.trust_identity(e.getName(), e.getIdentityKey())
                return self.handleEncMessage(node)
            else:                
                logger.error("Ignoring message with untrusted identity")
                self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())    

    def handleMsMessage(self,node):
        logger.info(f"handleMsMessage: {node}")

        pass

        '''
        msMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)
        enc = msMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSMSG)
        plaintext = self.manager.decrypt_msg(msMessageProtocolEntity.getAuthor(False), enc.getData(),
                                               enc.getVersion() == 2)

        if enc.getVersion() == 2:
            self.parseAndHandleMessageProto(msMessageProtocolEntity, plaintext)

        node = msMessageProtocolEntity.toProtocolTreeNode()
        print(node)
        node.addChild((ProtoProtocolEntity(plaintext, enc.getMediaType())).toProtocolTreeNode())
        '''


    def handlePreKeyWhisperMessage(self, node):

        pkMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)
        enc = pkMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_PKMSG)

        plaintext = self.manager.decrypt_pkmsg(pkMessageProtocolEntity.getAuthor(True), enc.getData(),
                                               enc.getVersion() == 2)

        logger.info(f"[AxolotlReceive] handlePreKeyWhisperMessage: plaintext descriptografado (bytes): {len(plaintext) if plaintext else 0} bytes")

        if enc.getVersion() == 2:
            logger.debug(f"[AxolotlReceive] handlePreKeyWhisperMessage: fazendo parse do protobuf")
            self.parseAndHandleMessageProto(pkMessageProtocolEntity, plaintext)

        node = pkMessageProtocolEntity.toProtocolTreeNode()
        node.addChild((ProtoProtocolEntity(plaintext, enc.getMediaType())).toProtocolTreeNode())

        logger.debug(f"[AxolotlReceive] handlePreKeyWhisperMessage: enviando mensagem descriptografada para layer superior")
        self.toUpper(node)

    def handleWhisperMessage(self, node):

        encMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)

        enc = encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSG)
        logger.debug(f"[AxolotlReceive] handleWhisperMessage: tentando descriptografar mensagem TYPE_MSG")
        
        try:
            plaintext = self.manager.decrypt_msg(encMessageProtocolEntity.getAuthor(False), enc.getData(),
                                                 enc.getVersion() == 2)
        except exceptions.InvalidMessageException:
            raise
        except Exception as e:
            logger.error(f"[AxolotlReceive] handleWhisperMessage: erro inesperado ao descriptografar: {e}", exc_info=True)
            raise
        
        logger.debug(f"[AxolotlReceive] handleWhisperMessage: plaintext descriptografado (bytes): {len(plaintext) if plaintext else 0} bytes")

        if enc.getVersion() == 2:
            logger.debug(f"[AxolotlReceive] handleWhisperMessage: fazendo parse do protobuf")
            self.parseAndHandleMessageProto(encMessageProtocolEntity, plaintext)

        node = encMessageProtocolEntity.toProtocolTreeNode()
        node.addChild((ProtoProtocolEntity(plaintext, enc.getMediaType())).toProtocolTreeNode())

        logger.debug(f"[AxolotlReceive] handleWhisperMessage: enviando mensagem descriptografada para layer superior")
        self.toUpper(node)

    def handleSenderKeyMessage(self, node):
        encMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)
        enc = encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_SKMSG)

        try:
            plaintext = self.manager.group_decrypt(
                groupid=encMessageProtocolEntity.getFrom(True),
                participantid=encMessageProtocolEntity.getParticipant(False),
                data=enc.getData()
            )
            self.parseAndHandleMessageProto(encMessageProtocolEntity, plaintext)
            node = encMessageProtocolEntity.toProtocolTreeNode()
            node.addChild((ProtoProtocolEntity(plaintext, enc.getMediaType())).toProtocolTreeNode())
            logger.debug(f"[AxolotlReceive] handleSenderKeyMessage: enviando mensagem descriptografada para layer superior")
            self.toUpper(node)
            return True
        except exceptions.NoSessionException:
            # Não há sessão de grupo: envia retry e marca como handled para evitar receipt incorreto
            logger.warning(f"Got retry to {encMessageProtocolEntity.getAuthor(False)}, going to send a retry")
            try:
                self.send_retry(node, self.manager.registration_id)
            except Exception as e:
                logger.error(f"[AxolotlReceive] Falha ao enviar retry para mensagem de grupo: {e}")
            return True

    def parseAndHandleMessageProto(self, encMessageProtocolEntity, serializedData):
       
        m = Message()
        try:
            m.ParseFromString(serializedData)
            logger.debug(f"[AxolotlReceive] parseAndHandleMessageProto: protobuf parseado com sucesso")
        except Exception as e:
            logger.error(f"[AxolotlReceive] parseAndHandleMessageProto: erro ao fazer parse do protobuf: {e}")
            print("DUMP:")
            print(serializedData)
            print([s for s in serializedData])
            raise
        if not m or not serializedData:
            raise exceptions.InvalidMessageException()

        if m.HasField("sender_key_distribution_message"):
            logger.info(f"[AxolotlReceive] parseAndHandleMessageProto: HasField sender_key_distribution_message - criando sessão de grupo")
            self.handleSenderKeyDistributionMessage(
                m.sender_key_distribution_message,
                encMessageProtocolEntity.getParticipant(False)
            )

        return m

    def handleSenderKeyDistributionMessage(self, senderKeyDistributionMessage, participantId):
        groupId = senderKeyDistributionMessage.group_id
        self.manager.group_create_session(
            groupid=groupId,
            participantid=participantId,
            skmsgdata=senderKeyDistributionMessage.axolotl_sender_key_distribution_message
        )

    def send_retry(self, message_node, registration_id):
        message_id = message_node["id"]
        if message_id in self._retries:
            count = self._retries[message_id]
            count += 1
        else:
            count = 1
        self._retries[message_id] = count
        retry = RetryOutgoingReceiptProtocolEntity.fromMessageNode(message_node, registration_id)
        retry.count = count
        self.toLower(retry.toProtocolTreeNode())

    def send_pkmsg_for_invalid_message(self, sender_jid, message_id, participant=None):
       
        try:
            logger.info(f"[AxolotlReceive] Enviando mensagem PKMSG vazia para {sender_jid} devido a InvalidMessageException")

            send_layer = self.getLayerInterface(AxolotlSendLayer)
            if send_layer is None:
                logger.error("[AxolotlReceive] AxolotlSendLayer não encontrado no stack")
                return
            
            normalized_sender_jid = Jid.normalize(sender_jid)
            if normalized_sender_jid is None:
                logger.error(f"[AxolotlReceive] JID inválido: {sender_jid}")
                return

            message_attrs = MessageMetaAttributes(
                id=f"sync_{message_id}_{int(time.time())}",
                recipient=normalized_sender_jid,
                timestamp=int(time.time())
            )

            message_entity = TextMessageProtocolEntity("", message_attrs)

            message_node = message_entity.toProtocolTreeNode()
            message_node.setAttribute("to", normalized_sender_jid)
            message_node.setAttribute("type", "text")

            if participant:
                message_node.setAttribute("participant", participant)

            send_layer.sendToContactAsPkmsg(message_node)
            logger.debug(f"[AxolotlReceive] Mensagem PKMSG enviada com sucesso para {normalized_sender_jid}")

        except Exception as e:
            logger.error(f"[AxolotlReceive] Erro ao enviar mensagem PKMSG para {normalized_sender_jid if 'normalized_sender_jid' in locals() else sender_jid}: {e}")

    def reset_retries(self, message_id):
        if message_id in self._retries:
            del self._retries[message_id]


