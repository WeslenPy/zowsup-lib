from .iq import IqProtocolEntity
from ....structs import ProtocolTreeNode

import base64
class PushSetIdIqProtocolEntity(IqProtocolEntity):
    def __init__(self,id):        
        super(PushSetIdIqProtocolEntity, self).__init__("urn:xmpp:whatsapp:push", _type="set",to="s.whatsapp.net")
        self.id = id

    def toProtocolTreeNode(self):
        node = super(PushSetIdIqProtocolEntity, self).toProtocolTreeNode()        
        node.addChild(ProtocolTreeNode("config",{"id":self.id,"platform":"gcm"}))
        return node
    

