#from .protomessage import ProtomessageProtocolEntity
from .message import MessageMetaAttributes
from .attributes.attributes_message import MessageAttributes
from .protomessage import ProtomessageProtocolEntity


class InteractiveMessageProtocolEntity(ProtomessageProtocolEntity):
    def __init__(self, content ,message_meta_attributes=None,to=None):
        # flexible attributes for temp backwards compat
        assert(bool(message_meta_attributes) ^ bool(to)), "Either set message_meta_attributes, or to, and not both"
        if to:
            message_meta_attributes = MessageMetaAttributes(recipient=to)
                                    
        super(InteractiveMessageProtocolEntity, self).__init__("text", MessageAttributes(interactive = content), message_meta_attributes)
        self.content = content

    def getContent(self):
        return self.content

    def setContent(self, value):
        self.content = value


