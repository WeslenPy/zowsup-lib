from ....structs import ProtocolEntity, ProtocolTreeNode
class StreamErrorProtocolEntity(ProtocolEntity):
    TYPE_CONFLICT = "conflict"
    '''
     <stream:error>
        <conflict></conflict>
        <text>Replaced by new connection</text>
     </stream:error>
    '''

    TYPE_ACK = "ack"
    '''
     <stream:error>
        <ack></ack>
     </stream:error>
    '''

    TYPE_XML_NOT_WELL_FORMED = "xml-not-well-formed"
    '''
    <stream:error>
        <xml-not-well-formed>
        </xml-not-well-formed>
    </stream:error>
    '''

    TYPE_BAD_MAC = "bad-mac"
    '''
    <stream:error>
        <bad-mac />        
    </stream:error>
    '''    

    

    TYPES = (TYPE_CONFLICT, TYPE_ACK, TYPE_XML_NOT_WELL_FORMED,TYPE_BAD_MAC)

    def __init__(self, data = None,code =None):
        super(StreamErrorProtocolEntity, self).__init__("stream:error")
        data = data or {}        
        self.code = code
        self.setErrorData(data)

    def setErrorData(self, data):
        self.data = data

    def getErrorData(self):
        return self.data

    def getErrorType(self):
        for k in self.data.keys():
            if k in self.__class__.TYPES:
                return k
        

    def __str__(self):
        out  = "Stream Error code:%s type: %s\n" % (self.code,self.getErrorType())
        out += "%s" % self.getErrorData()
        out += "\n"

        return out

    def toProtocolTreeNode(self):
        node = super(StreamErrorProtocolEntity, self).toProtocolTreeNode()
        type = self.getErrorType()
        node.addChild(ProtocolTreeNode(type))
        if type == self.__class__.TYPE_CONFLICT and "text" in self.data:
            node.addChild(ProtocolTreeNode("text", data=self.data["text"]))

        return node


    @staticmethod
    def fromProtocolTreeNode(protocolTreeNode):
        data = {}        
        code = protocolTreeNode.getAttributeValue("code")
        for child in protocolTreeNode.getAllChildren():
            data[child.tag] = child.data
        return StreamErrorProtocolEntity(data,code)


