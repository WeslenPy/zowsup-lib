from ....structs import  ProtocolTreeNode
from .iq import IqProtocolEntity
from ....common import YowConstants
from zowsuplib.proto import wa_struct_pb2
import json
class WmexQueryIqProtocolEntity(IqProtocolEntity):

    '''
    <iq to="s.whatsapp.net" type="get" id="3979800857",xmlns="w:mex">
        <query query_id='xxxxxxxxxx'>
            JSON-FORMATTED RESULT
        </query>
    </iq>  
    '''

    def __init__(self,query_id=None,query_obj=None,_id=None):
        super(WmexQueryIqProtocolEntity, self).__init__("w:mex",_id = _id, _type = "get", to = YowConstants.DOMAIN)
        self.query_id = query_id
        self.query_obj = query_obj

    def __str__(self):
        out = super(WmexQueryIqProtocolEntity, self).__str__()
        out += "query_id: %s\n" % self.query_id
        out += "query_obj: %s\n" % json.dumps(self.query_obj)
        return out

    def toProtocolTreeNode(self):
        node = super(WmexQueryIqProtocolEntity, self).toProtocolTreeNode()        
        query = ProtocolTreeNode("query",{"query_id":self.query_id})
        query.setData(json.dumps(self.query_obj).encode())
        node.addChild(query)                           
        return node               


        

