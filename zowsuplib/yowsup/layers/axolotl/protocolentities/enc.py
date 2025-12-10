from ....structs import ProtocolEntity, ProtocolTreeNode
import sys
class EncProtocolEntity(ProtocolEntity):
    TYPE_PKMSG  = "pkmsg"
    TYPE_MSG    = "msg"
    TYPE_SKMSG  = "skmsg"
    TYPE_FRSKMSG= "frskmsg"
    TYPE_MSMSG  = "msmsg"
    TYPES = (TYPE_PKMSG, TYPE_MSG, TYPE_SKMSG,TYPE_FRSKMSG,TYPE_MSMSG)

    def __init__(self, type, version, data, mediaType = None, jid = None,count=None):
        assert type in self.__class__.TYPES, "Unknown message enc type %s" % type
        super(EncProtocolEntity, self).__init__("enc")
        self.type = type
        self.version = int(version)
        self.data = data
        self.mediaType = mediaType
        self.jid = jid
        self.count = count

    def getType(self):
        return self.type

    def getVersion(self):
        return self.version

    def getData(self):
        return self.data

    def getMediaType(self):
        return self.mediaType

    def getJid(self):
        return self.jid
    

    def getCount(self):
        return self.count

    def toProtocolTreeNode(self):
        attribs = {"type": self.type, "v": str(self.version)}
        if self.mediaType:
            attribs["mediatype"] = self.mediaType
        if self.count and self.count!="0":
            attribs["count"] = self.count
        encNode =  ProtocolTreeNode("enc", attribs, data = self.data)        
        if self.jid:
            return ProtocolTreeNode("to", {"jid": self.jid}, [encNode])
        return encNode

    @staticmethod
    def fromProtocolTreeNode(node):
        return EncProtocolEntity(node["type"], node["v"], node.data, node["mediatype"])


