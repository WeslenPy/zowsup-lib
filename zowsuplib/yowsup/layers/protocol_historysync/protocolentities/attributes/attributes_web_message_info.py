from zowsuplib.proto import e2e_pb2

from .attributes_message_key import MessageKeyAttribute

class WebMessageInfoAttribute(object):

    def __init__(self,key):
        self.key = key              

    def encode(self):
        pb_obj  = e2e_pb2.WebMessageInfo()

        pb_obj.key.MergeFrom(self.key.encode())          #self.key是一个MessageKeyAttribute

        return pb_obj
    
    @staticmethod
    def decodeFrom(pb_obj):     
        key = MessageKeyAttribute.decodeFrom(pb_obj.key)
        return WebMessageInfoAttribute(key)









        

    
        


