from zowsuplib.proto import protocol_pb2

class SyncActionNuxActionAttribute(object):
    def __init__(self, acknowledged):
        self.acknowledged = acknowledged

    def encode(self):
        pb_obj = protocol_pb2.SyncActionValue.NuxAction()        
        if self.acknowledged is not None:
            pb_obj.acknowledged = self.acknowledged
        
        return pb_obj

    
    def indexName(self):
        return "nux"                
    
    def actionVersion(self):
        return 7
    
    @staticmethod
    def decodeFrom(self,pb_obj):
        acknowledged = pb_obj.acknowledged if pb_obj.HasField("acknowledged") else None

        return SyncActionNuxActionAttribute(acknowledged=acknowledged)


