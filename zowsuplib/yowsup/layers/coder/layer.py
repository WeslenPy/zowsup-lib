from ...layers import YowLayer
from .encoder import WriteEncoder
from .decoder import ReadDecoder
from .tokendictionary import TokenDictionary
import zlib


class YowCoderLayer(YowLayer):

    def __init__(self):
        YowLayer.__init__(self)
        tokenDictionary = TokenDictionary()
        self.writer = WriteEncoder(tokenDictionary)
        self.reader = ReadDecoder(tokenDictionary)
    
    def send(self, data):                
        out = self.writer.protocolTreeNodeToBytes(data)    
        
        self.write(out)

    def receive(self, data):                
        node = self.reader.getProtocolTreeNode(bytearray(data))        
        if node:
            self.toUpper(node)

    def write(self, i):
        if(type(i) in(list, tuple,bytearray)):
            self.toLower(bytearray(i))
        else:
            self.toLower(bytearray([i]))

    def __str__(self):
        return "Coder Layer"


