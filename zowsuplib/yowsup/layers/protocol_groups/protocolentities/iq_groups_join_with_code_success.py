from ....common import YowConstants
from ....structs import ProtocolTreeNode
from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
class SuccessJoinWithCodeGroupsIqProtocolEntity(ResultIqProtocolEntity):
    '''
    <iq type="result" id="{{id}}" from="g.us">
        <group jid="{group_id}"></group>
    </iq>
    '''

    def __init__(self, _id, groupId):
        super(SuccessJoinWithCodeGroupsIqProtocolEntity, self).__init__(_from = YowConstants.WHATSAPP_GROUP_SERVER, _id = _id)
        self.setProps(groupId)

    def setProps(self, groupId):
        self.groupId = groupId

    def toProtocolTreeNode(self):
        node = super(SuccessJoinWithCodeGroupsIqProtocolEntity, self).toProtocolTreeNode()
        node.addChild(ProtocolTreeNode("group",{"jid": self.groupId}))
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = ResultIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = SuccessJoinWithCodeGroupsIqProtocolEntity
        entity.setProps(node.getChild("group").getAttributeValue("jid"))
        return entity


