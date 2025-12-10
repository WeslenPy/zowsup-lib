from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity

'''
    <iq to='s.whatsapp.net' xmlns='w:sync:app:state' type='set' id='0d'>
        <sync data_namespace='3'>
            <collection name='critical_unblock_low' order='0'>
                <patch>
                    EtkBCAAS1AEKIgogq1KjkZ0di/MjsxXUWlhl3kX3QGdMpDDX7vlM7opusQ0SowEKoAGGa8or/ieTjIehj/fR1vsP/dMSTEP9SqeckQ4fDJPi2JrIk8ZdOCHzCP7v4iwfCTyEJyk2bVbeXq+vwumzbPTxoqpuc/wrqMGv91YepCHFvyABBV2mEcnHla3nGZb2BZs8FYWge9dz5J/edB4Mxeiv4nNgWiBGTOrMyJPW6FONvNl8UzaMHsoa8KWbQ5fRCI702IAW0i+t1j5t+4EAX1kvGggKBgAAAABoRSIgHAetpsGu+MQlxtXgu1ziyTrLj9SzYB0ACj4J6P79xJcqICDiRWvAbC/IDW/xy7Ve7uvE3WzauqQfa7Y/2rh+zxL0MggKBgAAAABoRUAA
                </patch>
            </collection>
            <collection name='critical_block' order='1'>
                <patch>
                    EpcBCAASkgEKIgog6ljOH0I5TnwqXIiRJKsnlDYWcQuFbKohxbjYU6I926QSYgpgDY23FQHEzkllChxoPp+rvHs/ijgOHFo43uVjyTMmX1vnXzBO9vGH6T/ZAg7EeQh8QV1t+utJldrMueqt20wzjLE7De2ODIhbwUFnzGTV5YGeD0GjvKsU1/nV2ZTgEw3CGggKBgAAAABoRRKnAQgAEqIBCiIKICsyUbZaTs/L4QCU5YK3Hcxl5rpJMzqrqV5qIV/SkmynEnIKcPQUhIZ2cqk5tDuyW9BkWO4pQu79WFKgRn588FkwTSmbgvmDhci0EsIP89L5Dd8bDJrxSRfl0Wkhr8gk7aGFlj7f6/LJVUAb3FjwniToUuIw12gakgnJyU/O7SctYtJ4QGblc0EXUGl3wcwdq3qss9MaCAoGAAAAAGhFIiA3UluNObBB/ToM1EMLH6eWtRThSZjQZhtZ6fu5xftRZSogvFA3mV2BbKu/tsEdiuTIQ4mG+LUK0lSECKYEYETlgvwyCAoGAAAAAGhFQAA=
                </patch>
            </collection>
        </sync>
    </iq>

'''

class AppSyncStateIqProtocolEntity(IqProtocolEntity):

    def __init__(self, patches=None, _id = None):
        super(AppSyncStateIqProtocolEntity, self).__init__("w:sync:app:state" , _id = _id, _type = "set",to="s.whatsapp.net")
        self.type = type
        self.patches = patches

    def toProtocolTreeNode(self):
        node = super(AppSyncStateIqProtocolEntity, self).toProtocolTreeNode()
        syncnode = ProtocolTreeNode("sync",{"data_namespace":"3"})
        
        if self.patches is not None:
            idx = 0
            for name,patch in self.patches.items():
                collectionNode = ProtocolTreeNode("collection",{"name":name,"order":str(idx)})
                idx +=1
                if patch is not None:
                    patchNode = ProtocolTreeNode("patch",{},None,patch.SerializeToString())
                    collectionNode.addChild(patchNode)                
                syncnode.addChild(collectionNode)        
        node.addChild(syncnode)      
        return node    


