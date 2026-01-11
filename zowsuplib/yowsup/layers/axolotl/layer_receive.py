from .layer_base import AxolotlBaseLayer

from ...layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from zowsuplib.proto.e2e_pb2 import Message
from ...layers.axolotl.protocolentities import *
from ...layers.protocol_messages.protocolentities.proto import ProtoProtocolEntity
from ...layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
from ...axolotl import exceptions

from zowsuplib.axolotl.untrustedidentityexception import UntrustedIdentityException

import logging
from loguru import logger


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
            # Tenta descriptografar mensagem de grupo (SenderKey)
            if encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_SKMSG):
                logger.debug(f"[AxolotlReceive] handleEncMessage: mensagem TYPE_SKMSG (grupo)")
                handled = self.handleSenderKeyMessage(node)               
                           
            # Se não foi mensagem de grupo, tenta mensagem individual
            if not handled:                                                                 
                if encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_PKMSG):
                    logger.debug(f"[AxolotlReceive] handleEncMessage: mensagem TYPE_PKMSG (PreKey)")
                    self.handlePreKeyWhisperMessage(node)
                elif encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSG):
                    logger.debug(f"[AxolotlReceive] handleEncMessage: mensagem TYPE_MSG (Whisper)")
                    self.handleWhisperMessage(node)             
                else:
                    # Tipo de mensagem não reconhecido, envia receipt
                    logger.warning(f"[AxolotlReceive] handleEncMessage: tipo de mensagem não reconhecido, enviando receipt")
                    self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())              

            # Se chegou aqui, a mensagem foi processada com sucesso
            self.reset_retries(node["id"])

        except exceptions.InvalidKeyIdException:
            logger.warning(f"Invalid KeyId for {encMessageProtocolEntity.getAuthor(False)}, going to send the receipt to ignore subsequence push")
            self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())
                   
            
        except exceptions.InvalidMessageException as e:
            # InvalidMessageException pode ocorrer por várias razões:
            # - Bad MAC (Message Authentication Code incorreto) - sessão desincronizada
            # - Sessão desincronizada entre remetente e destinatário
            # - Mensagem corrompida durante transmissão
            # - Chaves de sessão incorretas ou desatualizadas
            # 
            # Isso é um caso esperado em algumas situações (ex: sessão desincronizada),
            # então tratamos como WARNING, não ERROR
            try:
                author = encMessageProtocolEntity.getAuthor(False) if hasattr(encMessageProtocolEntity, 'getAuthor') else "unknown"
            except:
                author = node.get("from", "unknown")
            
            error_msg = str(e) if str(e) else "Invalid message (Bad MAC ou sessão desincronizada)"
            logger.warning(f"[AxolotlReceive] InvalidMessage para {author}: {error_msg}")
            
            retry_count = self._retries.get(node["id"], 0)
            if retry_count >= 2:
                # Tentou 3 vezes, provavelmente é um problema do remetente ou sessão muito desincronizada
                logger.warning(f"[AxolotlReceive] InvalidMessage após 2 tentativas para mensagem {node['id']}, enviando receipt e desistindo")
                self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())   
            else:            
                # Envia retry para tentar sincronizar a sessão novamente
                logger.debug(f"[AxolotlReceive] Enviando retry para mensagem {node['id']} (tentativa {retry_count + 1}/2)")
                self.send_retry(node, self.manager.registration_id)                

        except exceptions.NoSessionException:            
            logger.warning(f"No session for {encMessageProtocolEntity.getAuthor(False)}, getting their keys now")
            #self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"], participant=node["participant"]).toProtocolTreeNode())  

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
        """
        Fluxo de descriptografia:
        1. manager.decrypt_pkmsg() → descriptografa usando AES (retorna plaintext em bytes)
        2. parseAndHandleMessageProto() → apenas faz parse do protobuf (NÃO descriptografa)
        3. Adiciona plaintext ao nó como <proto> e envia para layer superior
        """
        pkMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)
        enc = pkMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_PKMSG)
        
        # PASSO 1: DESCRIPTOGRAFIA REAL acontece aqui
        # decrypt_pkmsg() → sessionCipher.decryptPkmsg() → decryptWithSessionRecord() 
        # → decryptWithSessionState() → getPlaintext() → AES.decrypt()
        # Retorna: plaintext (bytes) contendo o protobuf Message serializado JÁ DESCRIPTOGRAFADO
        plaintext = self.manager.decrypt_pkmsg(pkMessageProtocolEntity.getAuthor(True), enc.getData(),
                                               enc.getVersion() == 2)

        logger.info(f"[AxolotlReceive] handlePreKeyWhisperMessage: plaintext descriptografado (bytes): {len(plaintext) if plaintext else 0} bytes")

        # PASSO 2: Parse do protobuf (NÃO descriptografa, apenas faz parse)
        # Isso é necessário para processar sender_key_distribution_message se existir
        if enc.getVersion() == 2:
            logger.debug(f"[AxolotlReceive] handlePreKeyWhisperMessage: fazendo parse do protobuf")
            self.parseAndHandleMessageProto(pkMessageProtocolEntity, plaintext)

        # PASSO 3: Adiciona o plaintext (bytes já descriptografados) ao nó como <proto>
        # A layer superior (YowMessagesProtocolLayer) vai extrair esses bytes e fazer parse novamente
        node = pkMessageProtocolEntity.toProtocolTreeNode()
        node.addChild((ProtoProtocolEntity(plaintext, enc.getMediaType())).toProtocolTreeNode())

        logger.debug(f"[AxolotlReceive] handlePreKeyWhisperMessage: enviando mensagem descriptografada para layer superior")
        self.toUpper(node)

    def handleWhisperMessage(self, node):
        """
        Fluxo de descriptografia:
        1. manager.decrypt_msg() → descriptografa usando AES (retorna plaintext em bytes)
        2. parseAndHandleMessageProto() → apenas faz parse do protobuf (NÃO descriptografa)
        3. Adiciona plaintext ao nó como <proto> e envia para layer superior
        
        Nota: InvalidMessageException, NoSessionException, etc. podem ser lançadas aqui
        e serão tratadas em handleEncMessage. Não capturamos aqui para manter o código limpo.
        """
        encMessageProtocolEntity = EncryptedMessageProtocolEntity.fromProtocolTreeNode(node)

        enc = encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSG)
        logger.debug(f"[AxolotlReceive] handleWhisperMessage: tentando descriptografar mensagem TYPE_MSG")
        
        # PASSO 1: DESCRIPTOGRAFIA REAL acontece aqui
        # decrypt_msg() → sessionCipher.decryptMsg() → decryptWithSessionRecord() 
        # → decryptWithSessionState() → getPlaintext() → AES.decrypt()
        # Retorna: plaintext (bytes) contendo o protobuf Message serializado JÁ DESCRIPTOGRAFADO
        # Pode lançar InvalidMessageException, NoSessionException, etc. que serão tratadas em handleEncMessage
        try:
            plaintext = self.manager.decrypt_msg(encMessageProtocolEntity.getAuthor(False), enc.getData(),
                                                 enc.getVersion() == 2)
        except exceptions.InvalidMessageException:
            # Re-lança para ser tratada em handleEncMessage
            # Não logamos aqui para evitar duplicação de logs
            raise
        except Exception as e:
            # Qualquer outra exceção inesperada
            logger.error(f"[AxolotlReceive] handleWhisperMessage: erro inesperado ao descriptografar: {e}", exc_info=True)
            raise
        
        logger.debug(f"[AxolotlReceive] handleWhisperMessage: plaintext descriptografado (bytes): {len(plaintext) if plaintext else 0} bytes")

        # PASSO 2: Parse do protobuf (NÃO descriptografa, apenas faz parse)
        if enc.getVersion() == 2:
            logger.debug(f"[AxolotlReceive] handleWhisperMessage: fazendo parse do protobuf")
            self.parseAndHandleMessageProto(encMessageProtocolEntity, plaintext)

        # PASSO 3: Adiciona o plaintext (bytes já descriptografados) ao nó como <proto>
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
        """
        IMPORTANTE: Este método NÃO descriptografa nada!
        
        O serializedData JÁ está descriptografado (é o plaintext retornado por decrypt_pkmsg/decrypt_msg).
        Este método apenas:
        1. Faz parse do protobuf Message (serializedData → objeto Message)
        2. Processa sender_key_distribution_message se existir (para criar sessões de grupo)
        
        A descriptografia REAL acontece ANTES, em:
        - manager.decrypt_pkmsg() → sessionCipher.decryptPkmsg() → AES.decrypt()
        - manager.decrypt_msg() → sessionCipher.decryptMsg() → AES.decrypt()
        """
        m = Message()
        try:
            # Parse do protobuf (serializedData já está descriptografado)
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

        # Processa sender_key_distribution_message se existir (para criar sessões de grupo)
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

    def reset_retries(self, message_id):
        if message_id in self._retries:
            del self._retries[message_id]


