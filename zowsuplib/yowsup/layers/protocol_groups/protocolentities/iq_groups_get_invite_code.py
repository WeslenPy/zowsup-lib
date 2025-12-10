from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups import GroupsIqProtocolEntity
class GetInviteCodeGroupsIqProtocolEntity(GroupsIqProtocolEntity):
    '''
    <iq type="get" id="{{id}}" xmlns="w:g2", to={{group_jid}}">
        <invite/>                      
    </iq>
    '''
    def __init__(self, group_jid, _id = None):
        super(GetInviteCodeGroupsIqProtocolEntity, self).__init__(to = group_jid, _id = _id, _type = "get")        

    def toProtocolTreeNode(self):
        node = super(GetInviteCodeGroupsIqProtocolEntity, self).toProtocolTreeNode()
        node.addChild(ProtocolTreeNode("invite",{}, None, None))
        return node


