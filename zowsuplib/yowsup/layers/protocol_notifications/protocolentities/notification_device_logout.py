from ....structs import ProtocolEntity, ProtocolTreeNode
from .notification import NotificationProtocolEntity

class DeviceLogoutNotificationProtocolEntity(NotificationProtocolEntity):
    '''
    <notification from="s.whatsapp.net" type="registration" id="1023970139" t="1742050151">
        <device_logout device="Xiaomi Xiaomi 14" t="1742050151" id="nOatww==" />
    </notification>
    '''

    def __init__(self, _id,  _from, device, timestamp, refId, notify, offline):
        super(DeviceLogoutNotificationProtocolEntity, self).__init__(_id, _from, timestamp, notify, offline)
        self.device = device
        self.timestamp = timestamp
        self.refId = refId

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = NotificationProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = DeviceLogoutNotificationProtocolEntity
        codeNode = node.getChild("device_logout")
        entity.device = codeNode.getAttributeValue("device")
        entity.timestamp = codeNode.getAttributeValue("t")
        entity.refId = codeNode.getAttributeValue("id")
        return entity

