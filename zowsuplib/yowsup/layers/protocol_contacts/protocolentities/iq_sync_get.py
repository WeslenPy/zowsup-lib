from ....structs import ProtocolTreeNode
from ....layers.protocol_iq.protocolentities import IqProtocolEntity
from .iq_sync import SyncIqProtocolEntity

class GetSyncIqProtocolEntity(SyncIqProtocolEntity):

    MODE_FULL = "full"
    MODE_DELTA = "delta"

    CONTEXT_REGISTRATION = "registration"
    CONTEXT_INTERACTIVE = "interactive"

    CONTEXTS = (CONTEXT_REGISTRATION, CONTEXT_INTERACTIVE)
    MODES = (MODE_FULL, MODE_DELTA)


    '''
    <iq type="get" id="{{id}}" xmlns="usync">
        <usync mode="{{full | ?}}"
            context="{{registration | ?}}"
            sid="{{str((int(time.time()) + 11644477200) * 10000000)}}"
            index="{{0 | ?}}"
            last="{{true | false?}}"
        >
            <list>
                <user>
                    <contact>
                        +18500000000
                    </contact>
                </user>
                <user>
                    <contact>
                        +18500000000
                    </contact>
                </user>
            </list>

        </usync>
    </iq>
    '''

    def __init__(self, numbers, mode = MODE_FULL, context = CONTEXT_INTERACTIVE, sid = None, index = 0, last = True):
        super(GetSyncIqProtocolEntity, self).__init__("get", sid = sid, index =  index, last = last)
        self.setGetSyncProps(numbers, mode, context)        

    def setGetSyncProps(self, numbers, mode, context):
        assert type(numbers) is list, "numbers must be a list"
        assert mode in self.__class__.MODES, "mode must be in %s" % self.__class__.MODES
        assert context in self.__class__.CONTEXTS, "context must be in %s" % self.__class__.CONTEXTS

        self.numbers = numbers
        self.mode = mode
        self.context = context

    def __str__(self):
        out  = super(GetSyncIqProtocolEntity, self).__str__()
        out += "Mode: %s\n" % self.mode
        out += "Context: %s\n" % self.context
        out += "numbers: %s\n" % (",".join(self.numbers))
        return out

    def toProtocolTreeNode(self):
        query=ProtocolTreeNode("query",{},None,None)
        
        lid = ProtocolTreeNode("lid",{},None,None)
        query.addChild(lid)
        status=ProtocolTreeNode("status",{},None,None)
        query.addChild(status)
        contact=ProtocolTreeNode("contact",{},None,None)
        query.addChild(contact)        

        '''
        business=ProtocolTreeNode("business",{},None,None)
        vn=ProtocolTreeNode("verified_name",{},None,None)
        business.addChild(vn)
        pro=ProtocolTreeNode("profile",{"v":"116"},None,None)
        business.addChild(pro)
        query.addChild(business)
        '''

        list =ProtocolTreeNode("list",{},None,None)        
        for number in self.numbers:
            if not number.startswith("+"):
                number = "+"+number                                
            contact = ProtocolTreeNode("contact",{}, None,number.encode())
            user = ProtocolTreeNode("user",{},None,None)            
            user.addChild(contact)
            list.addChild(user)

        node = super(GetSyncIqProtocolEntity, self).toProtocolTreeNode()
        syncNode = node.getChild("usync")
        syncNode.setAttribute("mode", self.mode)
        syncNode.setAttribute("context", self.context)
        syncNode.addChild(query)        
        syncNode.addChild(list)

        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        syncNode         = node.getChild("usync")        
        userNodes        = syncNode.getAllChildren()
        numbers = []

        for userNode in userNodes:
            contact = userNode.getChild("contact")
            number = contact.data
            numbers.append(number)            
        
        entity.__class__ = GetSyncIqProtocolEntity        
        entity = SyncIqProtocolEntity.fromProtocolTreeNode(node)

        entity.setGetSyncProps(numbers,
            syncNode.getAttributeValue("mode"),
            syncNode.getAttributeValue("context"),
            )

        return entity


