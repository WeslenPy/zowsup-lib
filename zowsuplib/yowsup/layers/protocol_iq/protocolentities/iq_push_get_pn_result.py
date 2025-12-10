from ....structs import  ProtocolTreeNode
from .iq import IqProtocolEntity
from ....common import YowConstants
from zowsuplib.proto import wa_struct_pb2
import time


class PushGetPnResultIqProtocolEntity(IqProtocolEntity):


    def __init__(self,_id=None):
        super(PushGetPnResultIqProtocolEntity, self).__init__(_id = _id, _type = "result",to=YowConstants.DOMAIN)
        self.catData = None        

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = IqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = PushGetPnResultIqProtocolEntity

        catNode = node.getChild("cat")         #以出现这个字段为正确返回
        if catNode is not None:      
            entity.catData = catNode.getData()            
            return entity
        else:
            return None        



        




