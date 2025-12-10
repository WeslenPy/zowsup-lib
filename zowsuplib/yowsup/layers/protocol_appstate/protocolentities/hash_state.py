
from ....structs import ProtocolTreeNode

class HashState:

    def __init__(self, type,version = 0,hash=bytes(128),indexValueMap={}):
        self.type = type
        self.version = version
        self.hash = hash
        self.indexValueMap = indexValueMap
    
    def copy(self):

        return HashState(
            self.type,
            self.version,
            self.hash,
            self.indexValueMap
        )
    
    def equals(self,another):
        if len(self.indexValueMap)!=len(another.indexValueMap):
            return False
        
        for key,value in self.indexValueMap:
            if not (key in another.indexValueMap or another.indexValueMap[key]==value):
                return False

        return True        


    def hash(self):
        return self.hash     

    def toNode(self):
        
        node = ProtocolTreeNode("collection",{
            "name":self.type,
            "version":self.version            
        })

        return node
    


    


