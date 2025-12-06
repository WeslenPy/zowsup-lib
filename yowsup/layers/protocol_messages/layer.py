from ...layers import YowProtocolLayer
from .protocolentities import *
from ...layers.protocol_messages.protocolentities.attributes.converter import AttributesConverter
from ...layers.protocol_messages.protocolentities.attributes.attributes_message_meta import MessageMetaAttributes
from ...layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from ...layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity

import logging
from loguru import logger


class YowMessagesProtocolLayer(YowProtocolLayer):
    def __init__(self):
        handleMap = {
            "message": (self.recvMessageStanza, self.sendMessageEntity)
        }
        super(YowMessagesProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Messages Layer"

    def sendMessageEntity(self, entity):        
        if entity.getType() in ["text","poll","reaction"]:                              
            self.entityToLower(entity)

    ###recieved node handlers handlers    
    def recvMessageStanza(self, node):            
        """
        Processa mensagens recebidas do AxolotlReceiveLayer.
        
        Fluxo:
        1. Recebe nó com <proto> contendo bytes do protobuf Message (já descriptografado)
        2. Converte bytes → protobuf Message usando protobytes_to_proto()
        3. Converte protobuf Message → MessageAttributes usando proto_to_message()
        4. Cria entidade específica (TextMessageProtocolEntity, ExtendedTextMessageProtocolEntity, etc.)
        5. Envia para SendLayer.onMessage() via toUpper()
        """
        logger.debug(f"[MessagesLayer] recvMessageStanza chamado - from: {node.getAttributeValue('from')}, type: {node.getAttributeValue('type')}")

        # Ignora mensagens de newsletter
        if node.getAttributeValue("from").endswith("@newsletter"):
            self.toLower(OutgoingReceiptProtocolEntity(
                            messageIds=[node["id"]],
                            to=node["from"],
                            view=True,
                            serverIds=node["server_id"]
                        ).toProtocolTreeNode())    
            return               
         
        # Extrai o nó <proto> que contém os bytes do protobuf (já descriptografado pelo AxolotlReceiveLayer)
        protoNode = node.getChild("proto")                                
        if protoNode is None:
            logger.warning(f"[MessagesLayer] recvMessageStanza: nó sem <proto>, ignorando")
            return
        
        # Processa mensagens de reação
        if node.getAttributeValue("type")=="reaction":
            converter = AttributesConverter.get()
            # Converte bytes → protobuf Message
            proto = converter.protobytes_to_proto(protoNode.getData())
            # Converte protobuf Message → MessageAttributes
            message = converter.proto_to_message(proto,from_jid=node.getAttributeValue("from"))

            self.toUpper(
                ReactionMessageProtocolEntity(
                    message.reaction,
                    MessageMetaAttributes.from_message_protocoltreenode(node,proto)
                )
            )
        
        # Processa mensagens de poll
        elif node.getAttributeValue("type")=="poll":
            converter = AttributesConverter.get()
            message_db = self.getStack().getProp("profile").axolotl_manager  

            proto = converter.protobytes_to_proto(protoNode.getData())
            message = converter.proto_to_message(proto,from_jid=node.getAttributeValue("from"),message_db=message_db)

            self.toUpper(
                PollUpdateMessageProtocolEntity(
                    message.poll_update,
                    MessageMetaAttributes.from_message_protocoltreenode(node,proto)
                )
            )       
        else:                                 
            # Processa mensagens normais (text, extended_text, etc.)
            if protoNode and protoNode["mediatype"] is None:
                # mediatype é processado em outras layers (YowMediaProtocolLayer)
                converter = AttributesConverter.get()
                
                # PASSO 1: Converte bytes → protobuf Message
                # protoNode.getData() retorna os bytes do protobuf (já descriptografado)
                proto = converter.protobytes_to_proto(protoNode.getData())
                
                # PASSO 2: Converte protobuf Message → MessageAttributes
                # Isso extrai conversation, extended_text, image, etc. do protobuf
                message = converter.proto_to_message(proto)   

                logger.debug(f"[MessagesLayer] recvMessageStanza: message attributes extraídos - conversation: {message.conversation is not None}, extended_text: {message.extended_text is not None}")

                # PASSO 3: Cria entidade específica baseada no tipo de mensagem
                if message.conversation:
                    # Mensagem de texto simples
                    logger.debug(f"[MessagesLayer] Criando TextMessageProtocolEntity")
                    self.toUpper(
                        TextMessageProtocolEntity(
                            message.conversation, 
                            MessageMetaAttributes.from_message_protocoltreenode(node,proto),                            
                        )
                    )
                elif message.extended_text:
                    # Mensagem de texto estendido (pode ter URL, preview, etc.)
                    logger.debug(f"[MessagesLayer] Criando ExtendedTextMessageProtocolEntity")
                    self.toUpper(
                        ExtendedTextMessageProtocolEntity(
                            message.extended_text,
                            MessageMetaAttributes.from_message_protocoltreenode(node,proto)
                        )
                    )                                                                       
                    
                elif not message.sender_key_distribution_message:
                    # Tipo de mensagem não suportado
                    logger.warning(f"[MessagesLayer] Tipo de mensagem não suportado: {message}, enviando receipt")
                    self.toLower(
                        OutgoingReceiptProtocolEntity(
                            messageIds=[node["id"]],
                            to=node["from"],
                            participant=node["participant"]
                        ).toProtocolTreeNode()
                    )              



