from zowsuplib.proto import protocol_pb2

from .....layers.protocol_appstate.protocolentities.attributes import *

class SyncdKeyIdAttribute(object):
    def __init__(self, id):
        self.id = id
    
    def encode(self):
        pb_obj = protocol_pb2.KeyId()

        if self.id is not None:
            pb_obj.id = self.id        

        return pb_obj
    
    @staticmethod
    def decodeFrom(pb_obj):
        id = pb_obj.id if pb_obj.HasField("id") else None

        return SyncdKeyIdAttribute(
            id=id
        )

