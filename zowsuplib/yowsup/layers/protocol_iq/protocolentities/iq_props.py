from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode
class PropsIqProtocolEntity(IqProtocolEntity):
    def __init__(self):
        super(PropsIqProtocolEntity, self).__init__("w", _type="get",to="s.whatsapp.net")

    def toProtocolTreeNode(self):
        node = super(PropsIqProtocolEntity, self).toProtocolTreeNode()
        node.addChild(ProtocolTreeNode("props",{"protocol":"2","hash":""}))
        return node

