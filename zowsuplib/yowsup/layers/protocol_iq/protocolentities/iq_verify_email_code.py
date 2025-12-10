from ....structs import ProtocolTreeNode
from .iq import IqProtocolEntity
class VerifyEmailCodeIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None,code = None):
        super(VerifyEmailCodeIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:account" , _id = _id, _type = "get",to="s.whatsapp.net")
        self.code = code       
        
    def toProtocolTreeNode(self):
        node = super(VerifyEmailCodeIqProtocolEntity, self).toProtocolTreeNode()
        nodeVerify = ProtocolTreeNode("verify_email",{})
        nodeVerify.addChild(ProtocolTreeNode("code",{},None,self.code.encode("utf-8")))
        node.addChild(nodeVerify)      
        return node    


