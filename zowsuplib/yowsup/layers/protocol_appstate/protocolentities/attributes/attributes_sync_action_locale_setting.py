from zowsuplib.proto import protocol_pb2
import json
class SyncActionLocaleSettingAttribute(object):
    def __init__(self, locale):
        self.locale = locale
    
    def encode(self):
        pb_obj = protocol_pb2.SyncActionValue.LocaleSetting()        
        if self.locale is not None:
            pb_obj.locale = self.locale        
        return pb_obj
    
    def indexName(self):
        return "setting_locale"                
    
    def actionVersion(self):
        return 7
    
    @staticmethod
    def decodeFrom(self,pb_obj):
        locale = pb_obj.locale if pb_obj.HasField("locale") else None
        return SyncActionLocaleSettingAttribute(locale=locale)










