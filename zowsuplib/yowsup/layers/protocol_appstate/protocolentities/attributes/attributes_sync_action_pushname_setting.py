from zowsuplib.proto import protocol_pb2
import json
class SyncActionPushnameSettingAttribute(object):
    def __init__(self, name):
        self.name = name

    def encode(self):
        pb_obj = protocol_pb2.SyncActionValue.PushNameSetting()        
        if self.name is not None:
            pb_obj.name = self.name
        
        return pb_obj
    

    def indexName(self):
        return "setting_pushName"
    
    def actionVersion(self):
        return 7    
    
    @staticmethod
    def decodeFrom(self,pb_obj):
        name = pb_obj.name if pb_obj.HasField("name") else None

        return SyncActionPushnameSettingAttribute(name=name)
    





