from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups import GroupsIqProtocolEntity

class ParticipantsGroupsIqProtocolEntity(GroupsIqProtocolEntity):
    '''
    <iq type="get" id="{{id}}" xmlns="w:g2", to={{group_jid}}">
        <list></list>
    </iq>
    '''
    modes=["add","promote","remove","demote"]
    def __init__(self, jid, participantList, _mode, _id = None):
        super(ParticipantsGroupsIqProtocolEntity, self).__init__(to = jid, _id = _id, _type = "set")
        self.setProps(group_jid = jid, participantList = participantList, mode = _mode)

    def setProps(self, group_jid, participantList, mode):
        #assert type(participantList) is list, "Must be a list of jids, got %s instead." % type(participantList)
        #assert mode in self.modes, "Mode should be in: '" + "', '".join(self.modes) + "' but is '" + mode + "'"
        self.group_jid = group_jid
        self.participantList = participantList
        self.mode = mode
        
    def toProtocolTreeNode(self):
        node = super(ParticipantsGroupsIqProtocolEntity, self).toProtocolTreeNode()
        participantNodes = []
        for participant in self.participantList:            
            participantNodes.append(ProtocolTreeNode("participant", {"jid":participant}))         
        opnode = ProtocolTreeNode(self.mode,{},participantNodes)          
        node.addChild(opnode)        
        return node



