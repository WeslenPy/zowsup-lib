from .protomessage import ProtomessageProtocolEntity
from .message import MessageMetaAttributes
from .attributes.attributes_message import MessageAttributes
from zowsuplib.proto.e2e_pb2 import *


class ReactionMessageProtocolEntity(ProtomessageProtocolEntity):
    def __init__(self,reaction_attr,message_meta_attributes=None, to=None):
        
        assert(bool(message_meta_attributes) ^ bool(to)), "Either set message_meta_attributes, or to, and not both"        
        if to:
            message_meta_attributes = MessageMetaAttributes(recipient=to)

        super(ReactionMessageProtocolEntity, self).__init__("reaction", MessageAttributes(reaction = reaction_attr), message_meta_attributes)




    


