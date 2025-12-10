
from zowsuplib.common.utils import Utils

class MutationKeys(object):
    
    def __init__(self,indexKey,encKey,macKey,snapShotMacKey,patchMacKey):
        self.indexKey = indexKey
        self.encKey = encKey
        self.macKey = macKey
        self.snapShotMacKey = snapShotMacKey
        self.patchMacKey = patchMacKey

    @staticmethod
    def createFromKey(key):

        #从一个key生成5个key，保证sync流程用到的key
        ba = Utils.extract_and_expand(
            key = key,
            info = "WhatsApp Mutation Keys".encode(),
            output_length=160
        )

        return MutationKeys(
            indexKey = ba[0:32],
            encKey = ba[32:64],
            macKey = ba[64:96],
            snapShotMacKey= ba[96:128],        
            patchMacKey=  ba[128:]
        )





        


