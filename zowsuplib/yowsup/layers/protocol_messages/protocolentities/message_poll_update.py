from .protomessage import ProtomessageProtocolEntity
from .message import MessageMetaAttributes
from .attributes.attributes_message import MessageAttributes
from zowsuplib.proto.e2e_pb2 import *


class PollUpdateMessageProtocolEntity(ProtomessageProtocolEntity):
    def __init__(self,poll_update_attr,message_meta_attributes=None, to=None):
        
        assert(bool(message_meta_attributes) ^ bool(to)), "Either set message_meta_attributes, or to, and not both"        
        if to:
            message_meta_attributes = MessageMetaAttributes(recipient=to)

        super(PollUpdateMessageProtocolEntity, self).__init__("poll", MessageAttributes(poll_update = poll_update_attr), message_meta_attributes)




    


