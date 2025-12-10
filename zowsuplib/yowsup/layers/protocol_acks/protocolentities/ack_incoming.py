from ....structs import ProtocolEntity, ProtocolTreeNode
from .ack import AckProtocolEntity
from .ack_outgoing import OutgoingAckProtocolEntity
class IncomingAckProtocolEntity(AckProtocolEntity):

    '''
    <ack t="{{TIMESTAMP}}" from="{{FROM_JID}}" id="{{MESSAGE_ID}}" class="{{message | receipt | ?}}">
    </ack>
    '''

    def __init__(self, _id, _class, _from,timestamp, participant=None):
        super(IncomingAckProtocolEntity, self).__init__(_id, _class)
        self.setIncomingData(_from, timestamp,participant)

    def setIncomingData(self, _from, timestamp,participant):
        self._from = _from
        self.timestamp = timestamp
        self.participant = participant
    
    def toProtocolTreeNode(self):
        node = super(IncomingAckProtocolEntity, self).toProtocolTreeNode()
        node.setAttribute("from", self._from)
        node.setAttribute("t", self.timestamp)
        return node

    def getFrom(self):
        return self._from
    
    def getParticipant(self):
        return self.participant        


    def __str__(self):
        out  = super(IncomingAckProtocolEntity, self).__str__()
        out += "From: %s\n" % self._from
        out += "Timestamp: %s\n" % self.timestamp
        out += "Participant: %s\n" % self.participant
        return out
    
    def ack(self):
        return OutgoingAckProtocolEntity(self.getId(), "receipt",self._type, self.getFrom(), participant = self.participant)        
    

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = AckProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = IncomingAckProtocolEntity
        entity.setIncomingData(
            node.getAttributeValue("from"),
            node.getAttributeValue("t"),
            node.getAttributeValue("participant")
        )
        return entity


