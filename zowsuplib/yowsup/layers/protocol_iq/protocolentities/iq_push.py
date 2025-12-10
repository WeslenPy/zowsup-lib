from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode
class PushIqProtocolEntity(IqProtocolEntity):
    def __init__(self):
        super(PushIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:push", _type="get",to="s.whatsapp.net")

    def toProtocolTreeNode(self):
        node = super(PushIqProtocolEntity, self).toProtocolTreeNode()
        node.addChild(ProtocolTreeNode("config",{"version":"1"}))
        return node

