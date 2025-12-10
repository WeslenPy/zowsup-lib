from zowsuplib.proto import e2e_pb2

from .attributes_past_participant import PastParticipantAttribute

class PastParticipantsAttribute(object):

    def __init__(self,groupJid,pastParticipants):
        self.groupJid = groupJid
        self.pastParticipants = pastParticipants


    def encode(self):
        pb_obj  = e2e_pb2.PastParticipants()
        
        pb_obj.groupJid = self.groupJid

        for item in self.pastParticipants:
            pb_obj.pastParticipants.append(item.encode())
            
        return pb_obj
    
    @staticmethod
    def decodeFrom(pb_obj):
        
        groupJid = pb_obj.groupJid if pb_obj.HasField("groupJid") else None
            
        pastParticipants = []
        for item in pb_obj.pastParticipants:
            pastParticipants.append(PastParticipantAttribute.decodeFrom(item))

        return PastParticipantsAttribute(
            groupJid=groupJid,
            pastParticipants=pastParticipants
        )










        

    
        


