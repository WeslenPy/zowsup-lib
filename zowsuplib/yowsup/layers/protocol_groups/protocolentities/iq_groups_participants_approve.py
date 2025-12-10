from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups import GroupsIqProtocolEntity

class ApproveParticipantsGroupsIqProtocolEntity(GroupsIqProtocolEntity):
    '''
    <iq type="set" id="{{id}}" xmlns="w:g2", to={{group_jid}}">
        <membership_requests_action>
            <approve or reject>
                <participant jid="{{jid}}" />
                <participant jid="{{jid}}" />
            </approve or reject>
        </list>
    </iq>
    '''    
    def __init__(self, group_jid, participantList, action,_id = None):
        super(ApproveParticipantsGroupsIqProtocolEntity, self).__init__(to = group_jid, _id = _id, _type = "set")
        self.setProps(group_jid = group_jid, participantList = participantList,action=action)

    def setProps(self, group_jid, participantList,action):
        self.group_jid = group_jid
        self.participantList = participantList        
        self.action = action
        
    def toProtocolTreeNode(self):
        node = super(ApproveParticipantsGroupsIqProtocolEntity, self).toProtocolTreeNode()
        participantNodes = []
        for participant in self.participantList:
            participantNodes.append(ProtocolTreeNode("participant", {"jid":participant},None))
        actionnode = ProtocolTreeNode(self.action,{},participantNodes)    
        opnode = ProtocolTreeNode("membership_requests_action",{},[actionnode])
        node.addChild(opnode)            
        return node




