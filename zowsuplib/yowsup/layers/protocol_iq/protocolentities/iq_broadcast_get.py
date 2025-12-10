from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode
class GetBroadcastListProtocolEntity(IqProtocolEntity):
    def __init__(self):
        super(GetBroadcastListProtocolEntity, self).__init__("w:b", _type="get",to="s.whatsapp.net")

    def toProtocolTreeNode(self):
        node = super(GetBroadcastListProtocolEntity, self).toProtocolTreeNode()
        node.addChild(ProtocolTreeNode("lists"))
        return node

