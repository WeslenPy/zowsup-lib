from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups_participants import ParticipantsGroupsIqProtocolEntity

class AddParticipantsIqProtocolEntity(ParticipantsGroupsIqProtocolEntity):
    '''
    <iq type="set" id="{{id}}" xmlns="w:g2", to="{{group_jid}}">
        <add>
            <participant jid="{{jid}}" />
            <participant jid="{{jid}}" />
        </add>
    </iq>
    '''

    def __init__(self, group_jid, participantList, _id = None):
        super(AddParticipantsIqProtocolEntity, self).__init__(group_jid, participantList, "add", _id = _id)





