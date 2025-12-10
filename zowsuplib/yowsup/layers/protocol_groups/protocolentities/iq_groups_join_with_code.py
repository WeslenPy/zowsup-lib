from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups import GroupsIqProtocolEntity
class JoinWithCodeGroupsIqProtocolEntity(GroupsIqProtocolEntity):
    '''
    <iq type="set" id="{{id}}" xmlns="w:g2", to={{group_jid}}">
        <invite code="XXXXXXX" />                      
    </iq>
    '''
    def __init__(self, code, _id = None):
        super(JoinWithCodeGroupsIqProtocolEntity, self).__init__(to = "g.us", _id = _id, _type = "set")
        self.setProps(code)

    def setProps(self, code):
        self.code = code

    def toProtocolTreeNode(self):
        node = super(JoinWithCodeGroupsIqProtocolEntity, self).toProtocolTreeNode()
        node.addChild(ProtocolTreeNode("invite",{"code":self.code}, None, None))
        return node


