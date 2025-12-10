from ....structs import  ProtocolTreeNode
from .iq import IqProtocolEntity
from ....common import YowConstants
from zowsuplib.proto import wa_struct_pb2
import json
class WmexResultIqProtocolEntity(IqProtocolEntity):

    '''

    <iq from="s.whatsapp.net" type="result" id="3979800857">
    <result>
        JSON-FORMATTED RESULT
    </result>
    </iq>  
    '''

    def __init__(self,_id,result_obj=None,result_type="json"):
        super(WmexResultIqProtocolEntity, self).__init__(_id = _id, _type = "result", _from = YowConstants.DOMAIN)
        self.result_obj = result_obj
        self.result_type = result_type

    def setResultObj(self, result_obj,result_type):
        self.result_obj = result_obj
        self.result_type = result_type

    def __str__(self):
        out = super(WmexResultIqProtocolEntity, self).__str__()
        out += "result_obj: %s\n" % (json.dumps(self.result_obj) if self.result_type=="json" else str(self.result_obj))
        return out

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = IqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = WmexResultIqProtocolEntity
        result = node.getChild("result")                
        if result is not None:      
            format = result.getAttributeValue("format")
                    
            if format=="argo":
                entity.setResultObj(result.getData(),"argo")                
            else:
                jsonstr = str(result.getData(),"utf-8")
                entity.setResultObj(json.loads(jsonstr),"json")
            return entity
        else:            
            return None
        

