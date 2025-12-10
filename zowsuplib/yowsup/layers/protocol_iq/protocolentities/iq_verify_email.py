from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
class VerifyEmailIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None):
        super(VerifyEmailIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:account" , _id = _id, _type = "set",to="s.whatsapp.net")

        
    def toProtocolTreeNode(self):
        node = super(VerifyEmailIqProtocolEntity, self).toProtocolTreeNode()
        nodeEmail = ProtocolTreeNode("verify_email",{})
           
        nodeLg =  ProtocolTreeNode("lg",{},None,"en".encode())
        nodeEmail.addChild(nodeLg)
        nodeLg =  ProtocolTreeNode("lc",{},None,"US".encode())
        nodeEmail.addChild(nodeLg)
        node.addChild(nodeEmail)   
        return node    


