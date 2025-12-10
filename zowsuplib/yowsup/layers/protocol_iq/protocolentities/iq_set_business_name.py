from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
from ....axolotl.factory import AxolotlManagerFactory
from zowsuplib.proto import e2e_pb2
from zowsuplib.axolotl.ecc.curve import Curve
import random

class SetBusinessNameIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None,profile=None,name = "default.chinago"):
        super(SetBusinessNameIqProtocolEntity, self).__init__("w:biz" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.name = name
        self.profile = profile          #传profile 主要是要拿私钥

    def toProtocolTreeNode(self):
        node = super(SetBusinessNameIqProtocolEntity, self).toProtocolTreeNode()        
                                
        
        payload = e2e_pb2.VerifiedNameCertificate()            
        details = e2e_pb2.VerifiedNameCertificate.Details()
        details.serial = random.randint(1,1000000000000000)                   
        details.issuer = "smb:wa"        
        details.verifiedName = self.name  
        payload.details.MergeFrom(details)                                
        db = self.profile.axolotl_manager
        payload.signature = Curve.calculateSignature(db.identity.privateKey,payload.details.SerializeToString())        

        cert = ProtocolTreeNode("verified_name",{"v":"2"},None,payload.SerializeToString())        

        node.addChild(cert)  
               
        return node


