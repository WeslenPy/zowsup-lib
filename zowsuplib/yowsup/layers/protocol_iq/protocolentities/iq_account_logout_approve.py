from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode


class AccountLogoutApproveIqProtocolEntity(IqProtocolEntity):
    
    def __init__(self,refId,approve=True):
        super(AccountLogoutApproveIqProtocolEntity, self).__init__("w:account_defence", _type="set",to="s.whatsapp.net",smax_id="87")
        self.refId = refId
        self.approve = approve

    def toProtocolTreeNode(self):
        node = super(AccountLogoutApproveIqProtocolEntity, self).toProtocolTreeNode()
        logoutNode = ProtocolTreeNode("device_logout", {"approve":"true" if self.approve else "false","id":self.refId})
        node.addChild(logoutNode)
        return node

