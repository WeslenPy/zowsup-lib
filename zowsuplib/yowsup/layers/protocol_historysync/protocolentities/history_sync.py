
from ....layers.protocol_messages.protocolentities.attributes.attributes_downloadablemedia import DownloadableMediaMessageAttributes
from ....layers.protocol_messages.protocolentities import *
from ....layers.protocol_messages.protocolentities.attributes import * 
from ....layers.protocol_historysync.protocolentities.attributes import *
from zowsuplib.common.utils import Utils
class HistorySync(object):

    def __init__(self,media_conn,toJid):
        self.media_conn = media_conn
        self.toJid = toJid
        
    def createSyncMessage(self,history_sync_attrs,toJid,syncType="default"):

        syncBytes = Utils.compress(history_sync_attrs.encode().SerializeToString())
        media_attrs = DownloadableMediaMessageAttributes.from_buffer(syncBytes,"history-sync",self.media_conn)

        if syncType=="default":
            #默认是跟随attr的类型，除非指定
            syncType = history_sync_attrs.syncType

        if toJid is None:
            #默认None是用构造函数的toJid，除非指定
            toJid = self.toJid 
       
        entity = ProtocolMessageProtocolEntity(protocol_attr=ProtocolAttributes(                    
            type = ProtocolAttributes.TYPE_HISTORY_SYNC_NOTIFICATION,
            history_sync_notification=HistorySyncNotificationAttribute(
                mediaSha256 = media_attrs.file_sha256,
                mediaEncryptedSha256 = media_attrs.file_enc_sha256,
                mediaKey = media_attrs.media_key,
                mediaDirectPath = media_attrs.direct_path,
                mediaSize = media_attrs.file_length,
                syncType=syncType
            )    
        ),message_meta_attributes=MessageMetaAttributes(
            recipient=toJid,
            category="peer"
        ))

        #返回这个，外层直接toLower就可以
        return entity
    

    '''
    #快速方法
    '''

    def createNonBlockingDataMessage(self,toJid=None,pastParticipants=[]):
       return self.createSyncMessage(
             history_sync_attrs=HistorySyncAttribute(
                            syncType = HistorySyncAttribute.NON_BLOCKING_DATA,
                            pastParticipants=pastParticipants
                        ),
             toJid = toJid,
             syncType = None
       )

    def createInitialStatusV3Message(self,toJid=None,statusV3Messages=[]):
       return self.createSyncMessage(
             history_sync_attrs=HistorySyncAttribute(
                            syncType = HistorySyncAttribute.INITIAL_STATUS_V3,
                            statusV3Messages=statusV3Messages
                        ),
             toJid = toJid
       )
    
    def createPushNameMessage(self,toJid=None,pushnames=[]):

        return self.createSyncMessage(
             history_sync_attrs=HistorySyncAttribute(
                            syncType = HistorySyncAttribute.PUSH_NAME,
                            pushnames=pushnames
                        ),
             toJid = toJid
       )

    def createRecentMessage(self,toJid=None,conversations=[]):
        return self.createSyncMessage(
             history_sync_attrs=HistorySyncAttribute(
                            syncType = HistorySyncAttribute.RECENT,
                            conversations=conversations
                        ),
             toJid = toJid
       )

    def createInitialBootstrapMessage(self,toJid=None,conversations=[]):
        return self.createSyncMessage(
             history_sync_attrs=HistorySyncAttribute(
                            syncType = HistorySyncAttribute.INITIAL_BOOTSTRAP,
                            conversations=conversations
                        ),
             toJid = toJid
       )



