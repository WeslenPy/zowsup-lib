from ...layers import YowProtocolLayer
from .protocolentities import ImageDownloadableMediaMessageProtocolEntity
from .protocolentities import AudioDownloadableMediaMessageProtocolEntity
from .protocolentities import VideoDownloadableMediaMessageProtocolEntity
from .protocolentities import DocumentDownloadableMediaMessageProtocolEntity
from .protocolentities import StickerDownloadableMediaMessageProtocolEntity
from .protocolentities import LocationMediaMessageProtocolEntity
from .protocolentities import ContactMediaMessageProtocolEntity
from .protocolentities import ResultRequestUploadIqProtocolEntity
from .protocolentities import MediaMessageProtocolEntity
from .protocolentities import ExtendedTextMediaMessageProtocolEntity
from .protocolentities import ButtonsResponseMediaMessageProtocolEntity
from .protocolentities import ListResponseMediaMessageProtocolEntity
from .protocolentities import ProductMediaMessageProtocolEntity
from ...layers.protocol_iq.protocolentities import IqProtocolEntity, ErrorIqProtocolEntity
import logging
import traceback

from loguru import logger


class YowMediaProtocolLayer(YowProtocolLayer):
    def __init__(self):
        handleMap = {
            "message": (self.recvMessageStanza, self.sendMessageEntity),
            "iq": (self.recvIq, self.sendIq)
        }
        super(YowMediaProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Media Layer"

    def sendMessageEntity(self, entity):
        if entity.getType() == "media":                    
            self.entityToLower(entity)

    def recvMessageStanza(self, node):    


                                
        if node.getAttributeValue("type") == "medianotify":
            self.toLower(MediaMessageProtocolEntity.fromProtocolTreeNode(node).ack(True).toProtocolTreeNode())
            
        if node.getAttributeValue("type") == "media":                                          
            mediaNode = node.getChild("proto")                         
            if mediaNode is None:
                return
                        
            try:                
                if mediaNode.getAttributeValue("mediatype") == "image":
                    entity = ImageDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)     
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "sticker":
                    entity = StickerDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") in ("audio", "ptt"):
                    entity = AudioDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") in ("video", "gif"):
                    entity = VideoDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "location":
                    entity = LocationMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "vcard":
                    entity = ContactMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "document":                    
                    entity = DocumentDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "url":                
                    entity = ExtendedTextMediaMessageProtocolEntity.fromProtocolTreeNode(node)                            
                    print(entity)        
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "buttons_response":
                    entity = ButtonsResponseMediaMessageProtocolEntity.fromProtocolTreeNode(node)                
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "list_response":
                    entity = ListResponseMediaMessageProtocolEntity.fromProtocolTreeNode(node)                
                    self.toUpper(entity)                
                elif mediaNode.getAttributeValue("mediatype") == "product":
                    entity = ProductMediaMessageProtocolEntity.fromProtocolTreeNode(node)                
                    self.toUpper(entity)                     

                elif mediaNode.getAttributeValue("mediatype") == "1p_sticker":
                    entity = StickerDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                elif mediaNode.getAttributeValue("mediatype") == "avatar_sticker":
                    entity = StickerDownloadableMediaMessageProtocolEntity.fromProtocolTreeNode(node)
                    self.toUpper(entity)
                else:
                    logger.warn(f"Unsupported mediatype: {mediaNode.getAttributeValue('mediatype')}, will send receipts")
                    self.toLower(MediaMessageProtocolEntity.fromProtocolTreeNode(node).ack(True).toProtocolTreeNode())
            
            except:
                print(traceback.format_exc())
                logger.warn(f"mediatype: {mediaNode.getAttributeValue('mediatype')}, process with exception ")
                self.toLower(MediaMessageProtocolEntity.fromProtocolTreeNode(node).ack(True).toProtocolTreeNode())

    

    def sendIq(self, entity):
        """
        :type entity: IqProtocolEntity
        """
        if entity.getType() == IqProtocolEntity.TYPE_SET and entity.getXmlns() == "w:m":
            #media conn!
            self._sendIq(entity, self.onRequestMediaConnSuccess, self.onRequestMediaConnError)

    def recvIq(self, node):
        pass        
        """
        :type node: ProtocolTreeNode
        """

    def onRequestMediaConnSuccess(self, resultNode, requestUploadEntity):
        self.toUpper(ResultRequestUploadIqProtocolEntity.fromProtocolTreeNode(resultNode))

    def onRequestMediaConnError(self, errorNode, requestUploadEntity):
        self.toUpper(ErrorIqProtocolEntity.fromProtocolTreeNode(errorNode))
