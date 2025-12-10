from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
class Set2FAIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None,code = "123456", email = "unknown4096@gmail.com"):
        super(Set2FAIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:account" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.code = code
        self.email = email       


    def toProtocolTreeNode(self):
        node = super(Set2FAIqProtocolEntity, self).toProtocolTreeNode()
        node2fa = ProtocolTreeNode("2fa",{})
        node2fa.addChild(ProtocolTreeNode("code",{},None,self.code.encode("utf-8")))
        node2fa.addChild(ProtocolTreeNode("email",{},None,self.email.encode("utf-8")))
        node.addChild(node2fa)      
        return node    


