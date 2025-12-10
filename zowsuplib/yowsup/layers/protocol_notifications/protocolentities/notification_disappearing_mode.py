from ....structs import ProtocolEntity, ProtocolTreeNode
from .notification import NotificationProtocolEntity
from zowsuplib.proto import e2e_pb2
class DisapperingModeNotificationProtocolEntity(NotificationProtocolEntity):
    '''
        <notification from="8619874406144@s.whatsapp.net" type="disappearing_mode" id="2584939774" offline="0" t="1740650922">
            <disappearing_mode duration="7776000" t="1740650922" />
        </notification>
    '''

    def __init__(self, _id,  _from,  timestamp, notify, offline, duration="0"):
        super(DisapperingModeNotificationProtocolEntity, self).__init__("disappearing_mode",_id, _from, timestamp, notify, offline)        
        self.duration = duration
    
    @staticmethod
    def fromProtocolTreeNode(node):
        entity = NotificationProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = DisapperingModeNotificationProtocolEntity
        dmNode = node.getChild("disappearing_mode")        
        entity.duration = dmNode.getAttributeValue("duration")        
        return entity

