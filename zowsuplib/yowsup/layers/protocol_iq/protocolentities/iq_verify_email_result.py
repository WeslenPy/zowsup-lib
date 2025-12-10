from ....structs import  ProtocolTreeNode
from .iq import IqProtocolEntity
from ....common import YowConstants
from zowsuplib.proto import wa_struct_pb2
import time


class VerifyEmailResultIqProtocolEntity(IqProtocolEntity):

    def __init__(self,_id=None,waitTime=None,codeMatch=False):
        super(VerifyEmailResultIqProtocolEntity, self).__init__(_id = _id, _type = "result",to=YowConstants.DOMAIN)
        self.waitTime = waitTime 
        self.codeMatch = codeMatch       

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = IqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = VerifyEmailResultIqProtocolEntity
        resultNode = node.getChild("verify_email")  
        if resultNode is not None:
            waitTimeNode = resultNode.getChild("wait_time")    
            codeMatchNode = resultNode.getChild("code_match")     
            entity.waitTime = int(str(waitTimeNode.getData(),"utf-8")) if waitTimeNode is not None else None
            entity.codeMatch =  (True if str(codeMatchNode.getData(),"utf-8")=="true" else False) if codeMatchNode is not None else None
            return entity
        else:
            return None    





        




