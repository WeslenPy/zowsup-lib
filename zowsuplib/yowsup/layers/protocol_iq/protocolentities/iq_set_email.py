from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
class SetEmailIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None,email = "unknown4096@gmail.com"):
        super(SetEmailIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:account" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.email = email       
        
    def toProtocolTreeNode(self):
        node = super(SetEmailIqProtocolEntity, self).toProtocolTreeNode()
        nodeEmail = ProtocolTreeNode("email",{})
        nodeEmail.addChild(ProtocolTreeNode("email_address",{},None,self.email.encode("utf-8")))
        node.addChild(nodeEmail)      
        return node    


