from zowsuplib.proto import protocol_pb2
import json

class SyncActionPrimaryVersionActionAttribute(object):
    def __init__(self, version):
        self.version = version

    def encode(self):

        pb_obj  = protocol_pb2.SyncActionValue.PrimaryVersionAction()

        if self.version is not None:
            pb_obj.version = self.version        
        return pb_obj     

    def indexName(self):
        return "primary_version"                
    
    def actionVersion(self):
        return 7   
    
    @staticmethod
    def decodeFrom(pb_obj):

        version = pb_obj.version if pb_obj.HasField("version") else None
        
        return SyncActionPrimaryVersionActionAttribute(
            version=version
        ) 

