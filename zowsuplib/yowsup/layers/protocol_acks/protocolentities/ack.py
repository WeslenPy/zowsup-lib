from ....structs import ProtocolEntity, ProtocolTreeNode

class AckProtocolEntity(ProtocolEntity):

    '''
    <ack class="{{receipt | message | ?}}" id="{{message_id}}">
    </ack>
    '''

    def __init__(self, _id, _class,_error=None,_type=None):
        super(AckProtocolEntity, self).__init__("ack")
        self._id = _id
        self._class = _class
        self._error = _error
        self._type = _type        

    def getId(self):
        return self._id

    def getClass(self):
        return self._class
    
    def getError(self):
        return self._error
    
    def getType(self):
        return self._type
        
    def toProtocolTreeNode(self):
        attribs = {
            "id"           : self._id,
            "class"        : self._class                    
        }

        if self._type :
            attribs["type"] = self._type

        return self._createProtocolTreeNode(attribs, None, data = None)

    def __str__(self):
        out  = "ACK:\n"
        out += "ID: %s\n" % self._id
        out += "Class: %s\n" % self._class

        if self._type is not None:
            out += "Type: %s\n" % self._type        

        if self._error is not None:
            out += "Error: %s\n" % self._error
            
        return out
        
    @staticmethod
    def fromProtocolTreeNode(node):
        return AckProtocolEntity(
            node.getAttributeValue("id"),
            node.getAttributeValue("class"),
            node.getAttributeValue("error"),
            node.getAttributeValue("type")
            )


