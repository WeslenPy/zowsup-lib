from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups_participants  import ParticipantsGroupsIqProtocolEntity

class PromoteParticipantsIqProtocolEntity(ParticipantsGroupsIqProtocolEntity):
    '''
    <iq type="set" id="{{id}}" xmlns="w:g2", to="{{group_jid}}">
        <promote>
            <participant jid="{{jid}}" />
            <participant jid="{{jid}}" />
        </promote>
    </iq>
    '''

    def __init__(self, group_jid, participantList, _id = None):
        super(PromoteParticipantsIqProtocolEntity, self).__init__(group_jid, participantList, "promote", _id = _id)
    



