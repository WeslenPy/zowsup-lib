from zowsuplib.proto import protocol_pb2

from .....layers.protocol_appstate.protocolentities.attributes import *

class SyncdIndexAttribute(object):
    def __init__(self, blob):
        self.blob = blob

    def encode(self):
        pb_obj = protocol_pb2.SyncdIndex()

        if self.blob is not None:
            pb_obj.blob = self.blob        

        return pb_obj
    
    @staticmethod
    def decodeFrom(pb_obj):
        blob = pb_obj.blob if pb_obj.HasField("blob") else None

        return SyncdIndexAttribute(
            blob=blob
        )

