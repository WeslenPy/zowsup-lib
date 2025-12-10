from ....structs import ProtocolTreeNode
from .iq_sync import SyncIqProtocolEntity
from ....common import YowConstants

class DevicesResultSyncIqProtocolEntity(SyncIqProtocolEntity):
    '''
    <iq from="6283824958305@s.whatsapp.net" type="result" id="2">
    <usync sid="133187990650000000" index="0" last="true" mode="query" context="message">
        <result>
        <devices />
        </result>
        <list>
        <user jid="6283869786338@s.whatsapp.net">
            <devices>
            <device-list>
                <device id="0" />
                <device id="26" key-index="1" />
                <device id="27" key-index="2" />
                <device id="28" key-index="3" />                                
            </device-list>
            <key-index-list ts="1674309687">
                0x0a1308f1f192f60210b7e0af9e06180222030001021240740ee81523f4179cabfc0cd91348926a020af129f230b20738ddc4382951111d8aefa565475089737133bf47a34b90d613ee609259a47da6813f5adba8430607
            </key-index-list>
            </devices>
        </user>
        </list>
    </usync>
    </iq>
    '''

    def __init__(self,_id, sid, index, last, devicesDict):
        super(DevicesResultSyncIqProtocolEntity, self).__init__("result", _id, sid, index, last)
        self.setDevicesResultSyncProps(devicesDict)

    def setDevicesResultSyncProps(self, devicesDict):
        self.devicesDict = devicesDict

    def collectAllResultJids(self):
        jids = []
        for key in self.devicesDict:
            jids.append(key)
            recipientId = key.split("@")[0]
            listIds = self.devicesDict[key]
            jids.extend("%s.0:%s@%s" % (recipientId,deviceId,YowConstants.WHATSAPP_SERVER) for deviceId in listIds)

        return jids
    
    def __str__(self):
        out  = super(SyncIqProtocolEntity, self).__str__()
        for key in self.devicesDict:
            listDevices = self.devicesDict[key]
            out += "User:%s, Devices: %s\n" % (key,",".join(listDevices))
        return out
    
    @staticmethod
    def fromProtocolTreeNode(node):
        syncNode         = node.getChild("usync")
        resultNode       = syncNode.getChild("result")
        listNode         = syncNode.getChild("list")
        
        devicesDict = {}

        users = listNode.getAllChildren() if listNode else []

        for user in users:
            jid = user.getAttributeValue("jid")
            deviceList = user.getChild("devices").getChild("device-list")
            devicesDict[jid] = []
            devices = deviceList.getAllChildren() if deviceList else []
            for device in devices:
                deviceId = device.getAttributeValue("id")
                if deviceId!="0":
                    devicesDict[jid].append(deviceId)


        entity           = SyncIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = DevicesResultSyncIqProtocolEntity

        entity.setDevicesResultSyncProps(devicesDict)

        return entity


