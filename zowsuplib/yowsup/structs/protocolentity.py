from .protocoltreenode import ProtocolTreeNode
import unittest, time
import random
class ProtocolEntity(object):
    __ID_GEN = 0
    ID_TYPE_ANDROID = 0
    ID_TYPE_IOS = 1

    def __init__(self, tag):
        self.tag = tag

    def getTag(self):
        return self.tag

    def isType(self,  typ):
        return self.tag == typ

    def _createProtocolTreeNode(self, attributes, children = None, data = None):
        return ProtocolTreeNode(self.getTag(), attributes, children, data)


    def _getCurrentTimestamp(self):
        return int(time.time())

    def _generateId(self, short = False,type=ID_TYPE_ANDROID):
        
        if type==ProtocolEntity.ID_TYPE_IOS:
            alp = '0123456789ABCDEF0123456789ABCDEF'                
            id = ''.join(random.sample(alp, 18))
            id = "3A"+id

        if type==ProtocolEntity.ID_TYPE_ANDROID:
            alp = '0123456789ABCDEF0123456789ABCDEF'                
            id = ''.join(random.sample(alp, 32))


        return id
        
        #使用新的id机制
        #ProtocolEntity.__ID_GEN += 1
        #return str(ProtocolEntity.__ID_GEN) if short else str(int(time.time())) + "-" + str(ProtocolEntity.__ID_GEN)


    def toProtocolTreeNode(self):
        pass

    @staticmethod
    def fromProtocolTreeNode(self, protocolTreeNode):
        pass


class ProtocolEntityTest(object):
    def setUp(self):
        self.ProtocolEntity = None
        self.node = None

    # def assertEqual(self, entity, node):
    #     raise AssertionError("Should never execute that")

    def test_generation(self):
        if self.ProtocolEntity is None:
            raise ValueError("Test case not setup!")
        entity = self.ProtocolEntity.fromProtocolTreeNode(self.node)
        try:
            self.assertEqual(entity.toProtocolTreeNode(), self.node)
        except:
            print(entity.toProtocolTreeNode())
            print("\nNOTEQ\n")
            print(self.node)
            raise



