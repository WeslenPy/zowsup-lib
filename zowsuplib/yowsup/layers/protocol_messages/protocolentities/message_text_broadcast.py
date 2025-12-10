from .message_text import TextMessageProtocolEntity
from ....structs import ProtocolTreeNode
import time
from .message import MessageMetaAttributes
class BroadcastTextMessage(TextMessageProtocolEntity):
    def __init__(self, bcid, phash,body):        
        super(BroadcastTextMessage, self).__init__(body, message_meta_attributes=MessageMetaAttributes(
            recipient=bcid,
            phash = phash        
        ))
                        
    def toProtocolTreeNode(self):
        node = super(BroadcastTextMessage, self).toProtocolTreeNode()
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = TextMessageProtocolEntity.fromProtocolTreeNode(node)
        return entity


