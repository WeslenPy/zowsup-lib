from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
class SuccessGetInviteCodeGroupsIqProtocolEntity(ResultIqProtocolEntity):
    '''
    <iq type="result" id="{{id}}" from="group_jid">
        <invite code="code" />
    </iq>
    '''

    def __init__(self, _id, group_jid):
        super(SuccessGetInviteCodeGroupsIqProtocolEntity, self).__init__(_from = group_jid, _id = _id)        
        self.groupJid = group_jid
        self.inviteCode = None

    def setProps(self, group_jid,code):
        self.groupJid = group_jid
        self.inviteCode = code      

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = super(SuccessGetInviteCodeGroupsIqProtocolEntity, SuccessGetInviteCodeGroupsIqProtocolEntity).fromProtocolTreeNode(node)
        entity.__class__ = SuccessGetInviteCodeGroupsIqProtocolEntity
        entity.setProps(node.getAttributeValue("from"),node.getChild("invite").getAttributeValue("code"))
        return entity
        


