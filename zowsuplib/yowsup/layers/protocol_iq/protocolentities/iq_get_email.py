from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
class GetEmailIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None):
        super(GetEmailIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:account" , _id = _id, _type = "get",to="s.whatsapp.net")
        
    def toProtocolTreeNode(self):
        node = super(GetEmailIqProtocolEntity, self).toProtocolTreeNode()
        nodeEmail = ProtocolTreeNode("email",{})
        node.addChild(nodeEmail)   
        return node    


