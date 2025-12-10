from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
class PassiveIqProtocolEntity(IqProtocolEntity):
    
    def __init__(self, _id = None):
        super(PassiveIqProtocolEntity, self).__init__("passive" , _id = _id, _type = "set",to="s.whatsapp.net")        

    def toProtocolTreeNode(self):
        node = super(PassiveIqProtocolEntity, self).toProtocolTreeNode()
        clean = ProtocolTreeNode("active",{})
        node.addChild(clean)      
        return node    


