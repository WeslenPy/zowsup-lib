from ....common import YowConstants
from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
from ....structs import ProtocolTreeNode


class ResultRequestMediaConnIqProtocolEntity(ResultIqProtocolEntity):
    def __init__(self, _id, hosts,auth = None, ttl = 0):
        super(ResultRequestMediaConnIqProtocolEntity, self).__init__(_id = _id, _from = "s.whatsapp.net")
        self.setMediaConnProps(hosts, auth, ttl)

    def setMediaConnProps(self, hosts ,auth = None, ttl = 0):
        self.hosts = hosts
        self.auth = auth
        self.ttl = ttl or 0        


    def getHosts(self):
        return self.hosts

    def getAuth(self):
        return self.auth

    def getTtl(self):
        return self.ttl

    def __str__(self):
        out = super(ResultRequestMediaConnIqProtocolEntity, self).__str__()
        out += "HOSTS: %s\n" % ",".join(self.hosts)
        if self.auth:
            out += "AUTH: %s\n" % self.auth
        if self.ttl:
            out += "TTL: %s\n" % self.ttl

        return out

    def toProtocolTreeNode(self):
        node = super(ResultRequestMediaConnIqProtocolEntity, self).toProtocolTreeNode()

        mediaNode = ProtocolTreeNode("media_conn", {})
        if self.auth:
            mediaNode["auth"] = self.auth

        if self.ttl:
            mediaNode["ttl"] = str(self.ttl)

        node.addChild(mediaNode)
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity= ResultIqProtocolEntity.fromProtocolTreeNode(node)                
        entity.__class__ = ResultRequestMediaConnIqProtocolEntity
        mediaConnNode = node.getChild("media_conn")    
        if mediaConnNode:
            hosts = mediaConnNode.getAllChildren("host")
            hostArray = []
            for item in hosts:                
                hostArray.append(item["hostname"])            
            entity.setMediaConnProps(hostArray, mediaConnNode["auth"], mediaConnNode["ttl"])
        return entity


