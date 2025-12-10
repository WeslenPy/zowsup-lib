from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode
import codecs
class AccountInfoIqProtocolEntity(IqProtocolEntity):
    
    def __init__(self):
        super(AccountInfoIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:account", _type="get",to="s.whatsapp.net")

    def toProtocolTreeNode(self):
        node = super(AccountInfoIqProtocolEntity, self).toProtocolTreeNode()
        accountNode = ProtocolTreeNode("account", {})
        node.addChild(accountNode)
        return node

