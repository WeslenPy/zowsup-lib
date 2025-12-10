from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity

class AppSyncResetIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None):
        super(AppSyncResetIqProtocolEntity, self).__init__("w:sync:app:state" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.type = type

    def toProtocolTreeNode(self):
        node = super(AppSyncResetIqProtocolEntity, self).toProtocolTreeNode()
        x = ProtocolTreeNode("delete_all_data",{})
        node.addChild(x)      
        return node    


