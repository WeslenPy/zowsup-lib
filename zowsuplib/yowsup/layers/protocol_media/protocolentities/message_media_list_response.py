from ....layers.protocol_messages.protocolentities.attributes.attributes_message_meta import MessageMetaAttributes
from .message_media import MediaMessageProtocolEntity
from ....layers.protocol_messages.protocolentities.attributes.attributes_buttons_response import ButtonsResponseAttributes
from ....layers.protocol_messages.protocolentities.attributes.attributes_message import MessageAttributes


'''
BUTTON , LIST AND TEMPLATE MESSAGE WAS DEPRECATED BECAUSE OF THE  SERVER FILTERS  UPDATED AT 2023.5.11
'''
class ListResponseMediaMessageProtocolEntity(MediaMessageProtocolEntity):
    def __init__(self, list_response_attr, message_meta_attrs):
        # type: (ListResponseAttributes, MessageMetaAttributes) -> None
        super(ListResponseMediaMessageProtocolEntity, self).__init__(
            "list_response", MessageAttributes(list_response=list_response_attr), message_meta_attrs
        )

    @property
    def selected_row_id(self):
        return self.message_attributes.list_response.selected_row_id

    @selected_row_id.setter
    def selected_row_id(self, value):
        self.message_attributes.list_response.selected_row_id = value

    @property
    def title(self):
        return self.message_attributes.list_response.title

    @title.setter
    def title(self, value):
        self.message_attributes.list_response.title = value

    @property
    def list_type(self):
        return self.message_attributes.list_response.list_type

    @list_type.setter
    def list_type(self, value):
        self.message_attributes.list_response.list_type = value


