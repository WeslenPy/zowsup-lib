from loguru import logger
from ....layers.protocol_messages.protocolentities.attributes.attributes_message_meta import MessageMetaAttributes
from ....layers.protocol_messages.protocolentities.attributes.attributes_extendedtext import ExtendedTextAttributes
from ....layers.protocol_messages.protocolentities.protomessage import ProtomessageProtocolEntity
from ....layers.protocol_messages.protocolentities.attributes.attributes_message import MessageAttributes


class ExtendedTextMessageProtocolEntity(ProtomessageProtocolEntity):
    def __init__(self, extended_text_attrs, message_meta_attrs):
        # type: (ExtendedTextAttributes, MessageMetaAttributes) -> None
        super(ExtendedTextMessageProtocolEntity, self).__init__(
            "text", MessageAttributes(extended_text=extended_text_attrs), message_meta_attrs
        )

    @property
    def text(self):
        return self.message_attributes.extended_text.text

    @text.setter
    def text(self, value):
        self.message_attributes.extended_text.text = value

    @property
    def context_info(self):
        logger.info(f"context_info: {self.message_attributes.extended_text.context_info}")
        return self.message_attributes.extended_text.context_info

    @context_info.setter
    def context_info(self, value):
        logger.info(f"context_info setter: {value}")
        self.message_attributes.extended_text.context_info = value


