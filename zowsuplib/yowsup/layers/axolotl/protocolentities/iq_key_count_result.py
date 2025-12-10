from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
from ....common import YowConstants

class ResultKeyCountIqProtocolEntity(ResultIqProtocolEntity):

    '''
    <iq from="s.whatsapp.net" type="result" id="3979800857">
        <count value="812" />
    </iq>  
    '''

    def __init__(self,_id,count):
        super(ResultKeyCountIqProtocolEntity, self).__init__(_id = _id, _type = "result", _from = YowConstants.DOMAIN)
        self.count = int(count)


    def __str__(self):
        out = super(ResultKeyCountIqProtocolEntity, self).__str__()
        out += "count: %d\n" % self.count
        return out

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = ResultIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = ResultKeyCountIqProtocolEntity
        result = node.getChild("count")                
        if result is not None:      
            value = result.getAttributeValue("value")
            entity.value = int(value)
            return entity
        else:            
            return None
        

