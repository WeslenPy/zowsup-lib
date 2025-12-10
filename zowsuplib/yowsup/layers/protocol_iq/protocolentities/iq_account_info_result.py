from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode
import codecs
class AccountInfoResultIqProtocolEntity(IqProtocolEntity):
    
    def __init__(self,id,creation,lastReg):
        super(AccountInfoResultIqProtocolEntity, self).__init__(_id=id, _type="result",_from="s.whatsapp.net")
        self.creation = creation
        self.lastReg = lastReg

    def setInfo(self,creation,lastReg):
        self.creation = creation
        self.lastReg = lastReg
    
    @staticmethod
    def fromProtocolTreeNode(node):
        entity = IqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = AccountInfoResultIqProtocolEntity
        accountNode = node.getChild("account")

        if accountNode:
            creation = int(accountNode.getAttributeValue("creation"))
            last_reg = int(accountNode.getAttributeValue("last_reg"))
            entity.setInfo(creation,last_reg)
            return entity

        return None


