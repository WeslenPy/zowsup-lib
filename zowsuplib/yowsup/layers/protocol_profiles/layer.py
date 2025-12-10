from ...layers import  YowProtocolLayer
from .protocolentities import *
from ...layers.protocol_iq.protocolentities import ErrorIqProtocolEntity, ResultIqProtocolEntity
class YowProfilesProtocolLayer(YowProtocolLayer):
    def __init__(self):
        handleMap = {
            "iq": (self.recvIq, self.sendIq)
        }
        super(YowProfilesProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Profiles Layer"

    def sendIq(self, entity):
        if entity.getXmlns() == "w:profile:picture":
            node =     entity.toProtocolTreeNode()    
            self.toLower(node)
        #elif entity.getXmlns() == "privacy":
        #    self._sendIq(entity, self.onPrivacyResult, self.onPrivacyError)
        elif isinstance(entity, GetStatusesIqProtocolEntity):
            self._sendIq(entity)
        elif isinstance(entity, SetStatusIqProtocolEntity):
            self._sendIq(entity)

    def recvIq(self, node):        
        pass




    




