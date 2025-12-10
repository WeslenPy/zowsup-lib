from ....layers.protocol_messages.protocolentities.protomessage import ProtomessageProtocolEntity
from ....layers.protocol_messages.protocolentities.attributes.attributes_message import MessageAttributes
from ....layers.protocol_messages.protocolentities.attributes.attributes_message_meta import MessageMetaAttributes

import logging
from loguru import logger

import traceback


class MediaMessageProtocolEntity(ProtomessageProtocolEntity):
    TYPE_MEDIA_IMAGE = "image"
    TYPE_MEDIA_VIDEO = "video"
    TYPE_MEDIA_AUDIO = "audio"
    TYPE_MEDIA_CONTACT = "contact"
    TYPE_MEDIA_LOCATION = "location"
    TYPE_MEDIA_DOCUMENT = "document"
    TYPE_MEDIA_GIF = "gif"
    TYPE_MEDIA_PTT = "ptt"
    TYPE_MEDIA_URL = "url"
    TYPE_MEDIA_STICKER = "sticker"
    TYPE_MEDIA_BUTTONS_RESPONSE = "buttons_response"
    TYPE_MEDIA_LIST = "list"
    TYPE_MEDIA_LIST_RESPONSE = "list_response"
    TYPE_PRODUCT = "product"
    TYPE_MEDIA_STICKER = "1p_sticker"
    TYPE_MEDIA_AVATAR_STICKER = "avatar_sticker"

    TYPES_MEDIA = (
        TYPE_MEDIA_IMAGE, TYPE_MEDIA_AUDIO, TYPE_MEDIA_VIDEO,
        TYPE_MEDIA_CONTACT, TYPE_MEDIA_LOCATION, TYPE_MEDIA_DOCUMENT,
        TYPE_MEDIA_GIF, TYPE_MEDIA_PTT, TYPE_MEDIA_URL, TYPE_MEDIA_STICKER,
        TYPE_MEDIA_BUTTONS_RESPONSE,TYPE_MEDIA_LIST,TYPE_MEDIA_LIST_RESPONSE,
        TYPE_PRODUCT,TYPE_MEDIA_STICKER,TYPE_MEDIA_AVATAR_STICKER
    )

    def __init__(self, media_type, message_attrs, message_meta_attrs):
        """
        :type media_type: str
        :type message_attrs: MessageAttributes
        :type message_meta_attrs: MessageMetaAttributes
        """
        super(MediaMessageProtocolEntity, self).__init__("media", message_attrs, message_meta_attrs)
        self.media_type = media_type  # type: str

    def __str__(self):
        out = super(MediaMessageProtocolEntity, self).__str__()
        out += "\nmediatype=%s" % self.media_type
        return out

    @property
    def media_type(self):
        return self._media_type

    @media_type.setter
    def media_type(self, value):
        if value not in MediaMessageProtocolEntity.TYPES_MEDIA:
            logger.warning(f"media type: '{value}' is not supported")
        self._media_type = value

    def toProtocolTreeNode(self):
        node = super(MediaMessageProtocolEntity, self).toProtocolTreeNode()
        protoNode = node.getChild("proto")
        protoNode["mediatype"] = self.media_type
        return node

    @classmethod
    def fromProtocolTreeNode(cls, node):                

        entity = ProtomessageProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = cls
        entity.media_type = node.getChild("proto")["mediatype"]
        return entity


