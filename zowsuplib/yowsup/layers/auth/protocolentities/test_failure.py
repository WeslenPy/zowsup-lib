from ....layers.auth.protocolentities.failure import FailureProtocolEntity
from ....structs import ProtocolTreeNode
from ....structs.protocolentity import ProtocolEntityTest
import unittest


class FailureProtocolEntityTest(ProtocolEntityTest, unittest.TestCase):
    def setUp(self):
        self.ProtocolEntity = FailureProtocolEntity
        self.node = ProtocolTreeNode("failure", {"reason": "not-authorized"})


