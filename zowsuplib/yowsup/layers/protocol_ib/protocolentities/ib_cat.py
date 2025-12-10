from ....structs import ProtocolEntity, ProtocolTreeNode
from .ib import IbProtocolEntity
import base64

class CatIbProtocolEntity(IbProtocolEntity):
    '''
    <ib>
        <cat>
          XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        </cat>
    </ib>
    '''
    def __init__(self, catdata):
        super(CatIbProtocolEntity, self).__init__()
        self.catdata = catdata
            
    def toProtocolTreeNode(self):
        node = super(CatIbProtocolEntity, self).toProtocolTreeNode()
        catNode = ProtocolTreeNode("cat",data=self.catdata)
        node.addChild(catNode)
        return node

    def __str__(self):
        out = super(CatIbProtocolEntity, self).__str__()
        out += "ib-cat: %s\n" % base64.b64encode(self.catdata)
        return out


