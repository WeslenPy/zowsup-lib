from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode

import base64
class PushGetPnIqProtocolEntity(IqProtocolEntity):
    def __init__(self,token):
        super(PushGetPnIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:push", _type="get",to="s.whatsapp.net")
        self.token = token

    def toProtocolTreeNode(self):
        node = super(PushGetPnIqProtocolEntity, self).toProtocolTreeNode()        
        node.addChild(ProtocolTreeNode("pn",data=self.token.encode()))        
        return node
    
        

