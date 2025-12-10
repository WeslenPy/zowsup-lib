from ....structs import ProtocolTreeNode
from ....layers.protocol_iq.protocolentities import IqProtocolEntity
from .iq_sync import SyncIqProtocolEntity

class DevicesGetSyncIqProtocolEntity(SyncIqProtocolEntity):

    MODE_QUERY = "query"
    CONTEXT_MESSAGE = "message"

    CONTEXTS = (CONTEXT_MESSAGE,)
    MODES = (MODE_QUERY,)


    '''
    <iq type="get" id="{{id}}" xmlns="usync">
        <usync mode="query" last="true" index="0" context="message"        
            sid="xxxxxxxxxxxx"                        
        >
            <query>
                <devices version="2" />
            </query>
            <list>
                <user jid="XXXXXXXXXSADASD" />
            </list>
        </usync>
    </iq>
    '''

    def __init__(self, jids, mode = MODE_QUERY, context = CONTEXT_MESSAGE, sid = None, index = 0, last = True):
        super(DevicesGetSyncIqProtocolEntity, self).__init__("get", sid = sid, index =  index, last = last)
        self.setDevicesGetSyncProps(jids, mode, context)

    def setDevicesGetSyncProps(self, jids, mode, context):
        assert type(jids) is list, "numbers must be a list"
        assert mode in self.__class__.MODES, "mode must be in %s" % self.__class__.MODES
        assert context in self.__class__.CONTEXTS, "context must be in %s" % self.__class__.CONTEXTS

        self.jids = jids
        self.mode = mode
        self.context = context

    def __str__(self):
        out  = super(DevicesGetSyncIqProtocolEntity, self).__str__()
        out += "Mode: %s\n" % self.mode
        out += "Context: %s\n" % self.context
        out += "numbers: %s\n" % (",".join(self.numbers))
        return out

    def toProtocolTreeNode(self):
        query=ProtocolTreeNode("query",{},None,None)
        lid = ProtocolTreeNode("lid",{},None,None)
        query.addChild(lid)        
        devices=ProtocolTreeNode("devices",{"version":"2"},None,None)
        query.addChild(devices)        

        users =ProtocolTreeNode("list",{},None,None)        
        for jid in self.jids:
            user = ProtocolTreeNode("user",{"jid":jid},None,None)                        
            users.addChild(user)
            
        node = super(DevicesGetSyncIqProtocolEntity, self).toProtocolTreeNode()
        syncNode = node.getChild("usync")
        syncNode.setAttribute("mode", self.mode)
        syncNode.setAttribute("context", self.context)
        syncNode.addChild(query)
        syncNode.addChild(users)

        return node


