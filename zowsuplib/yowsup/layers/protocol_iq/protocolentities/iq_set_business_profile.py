from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
class SetBusinessProfileIqProtocolEntity(IqProtocolEntity):

    def __init__(self, _id = None,address = "default.chinago2", description = "",categoriesIds=['1223524174334504']):
        super(SetBusinessProfileIqProtocolEntity, self).__init__("w:biz" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.address = address
        self.description = description
        self.categoriesIds = categoriesIds


    def toProtocolTreeNode(self):
        node = super(SetBusinessProfileIqProtocolEntity, self).toProtocolTreeNode()        

        
                        
        profile = ProtocolTreeNode("business_profile",{"v":"884"})

        #profile.addChild(ProtocolTreeNode("verified_name",{"v":"2"},None,"Terry Watkins2".encode("utf-8")))
        profile.addChild(ProtocolTreeNode("address",{},None,self.address.encode("utf-8")))
        profile.addChild(ProtocolTreeNode("description",{},None,self.description.encode("utf-8")))

        cats = ProtocolTreeNode("categories",{})        

        for catid in self.categoriesIds:
            cats.addChild(ProtocolTreeNode("category",{"id":catid}))

        
            
        profile.addChild(cats)
        node.addChild(profile)  
               
        return node


