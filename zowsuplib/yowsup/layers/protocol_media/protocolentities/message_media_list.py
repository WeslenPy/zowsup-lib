from ....layers.protocol_messages.protocolentities.attributes.attributes_message_meta import MessageMetaAttributes
from .message_media import MediaMessageProtocolEntity
from ....layers.protocol_messages.protocolentities.attributes.attributes_buttons_response import ButtonsResponseAttributes
from ....layers.protocol_messages.protocolentities.attributes.attributes_message import MessageAttributes

'''
BUTTON , LIST AND TEMPLATE MESSAGE WAS DEPRECATED BECAUSE OF THE  SERVER FILTERS  UPDATED AT 2023.5.11
'''
class ListMediaMessageProtocolEntity(MediaMessageProtocolEntity):
    def __init__(self, list_attr, message_meta_attrs):        
        super(ListMediaMessageProtocolEntity, self).__init__(
            "list", MessageAttributes(list=list_attr), message_meta_attrs
        )

    @property
    def title(self):
        return self.message_attributes.list.title

    @title.setter
    def title(self, value):
        self.message_attributes.list.title = value

    @property
    def description(self):
        return self.message_attributes.list.description

    @description.setter
    def description(self, value):
        self.message_attributes.list.description = value

    @property
    def text(self):
        return self.message_attributes.list.text

    @text.setter
    def text(self, value):
        self.message_attributes.list.text = value

    @property
    def footer(self):
        return self.message_attributes.list.footer
        
    @footer.setter
    def footer(self, value):
        self.message_attributes.list.footer = value        

    @property
    def list_content(self):
        return self.message_attributes.list.list_content
        
    @list_content.setter
    def list_content(self, value):
        self.message_attributes.list.list_content = value        


