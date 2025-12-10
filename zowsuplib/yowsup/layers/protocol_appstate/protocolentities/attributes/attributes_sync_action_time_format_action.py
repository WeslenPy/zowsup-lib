from zowsuplib.proto import protocol_pb2
import json

class SyncActionTimeFormatActionAttribute(object):
    def __init__(self, isTwentyFourHourFormatEnabled):
        self.isTwentyFourHourFormatEnabled = isTwentyFourHourFormatEnabled
    
    def encode(self):
        pb_obj = protocol_pb2.SyncActionValue.TimeFormatAction()        
        if self.isTwentyFourHourFormatEnabled is not None:
            pb_obj.isTwentyFourHourFormatEnabled = self.isTwentyFourHourFormatEnabled        
        return pb_obj
    
    def indexName(self):
        return "time_format"                
    
    def actionVersion(self):
        return 7
    
    @staticmethod
    def decodeFrom(self,pb_obj):
        isTwentyFourHourFormatEnabled = pb_obj.isTwentyFourHourFormatEnabled if pb_obj.HasField("isTwentyFourHourFormatEnabled") else None

        return SyncActionTimeFormatActionAttribute(
            isTwentyFourHourFormatEnabled=isTwentyFourHourFormatEnabled
        )


