from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
import time
class CleanDirtyIqProtocolEntity(IqProtocolEntity):

    #type: account_sync | groups

    def __init__(self, _id = None,type = "account_sync"):
        super(CleanDirtyIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:dirty" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.type = type

    def toProtocolTreeNode(self):        
        node = super(CleanDirtyIqProtocolEntity, self).toProtocolTreeNode()
        clean = ProtocolTreeNode("clean",{'type':self.type,"timestamp":str(int(time.time()))})
        node.addChild(clean)     
        print(node) 
        return node    


