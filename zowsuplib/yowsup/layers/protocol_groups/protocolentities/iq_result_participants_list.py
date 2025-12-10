from ....structs import ProtocolTreeNode
from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
class ListParticipantsResultIqProtocolEntity(ResultIqProtocolEntity):
    '''
    <iq type="result" from="{{GROUP_ID}}" id="{{IQ_ID}}">
        <participant jid="{{PARTICIPANT_JID}}" />
    </iq>
    '''

    def __init__(self, _from, participantList):
        super(ListParticipantsResultIqProtocolEntity, self).__init__(_from = _from)
        self.setParticipants(participantList)

    def __str__(self):
        out = super(ListParticipantsResultIqProtocolEntity, self).__str__()
        out += "Participants: %s\n" % " ".join(self.participantList)
        return out

    def getParticipants(self):
        return self.participantList

    def setParticipants(self, participants):
        self.participantList = participants


    @staticmethod
    def fromProtocolTreeNode(node):
        entity = ResultIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = ListParticipantsResultIqProtocolEntity
        entity.setParticipants([ pNode.getAttributeValue("jid") for pNode in node.getAllChildren() ])
        return entity


