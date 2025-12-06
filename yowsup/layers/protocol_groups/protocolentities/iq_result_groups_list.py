from loguru import logger
from ....common import YowConstants
from ....structs import ProtocolEntity, ProtocolTreeNode
from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
from ..structs import Group
class ListGroupsResultIqProtocolEntity(ResultIqProtocolEntity):
    '''
    <iq type="result" from="g.us" id="{{IQ_ID}}">
      <groups>
          <group s_t="{{SUBJECT_TIME}}" creation="{{CREATING_TIME}}" creator="{{OWNER_JID}}" id="{{GROUP_ID}}" s_o="{{SUBJECT_OWNER_JID}}" subject="{{SUBJECT}}">
            <participant jid="{{JID}}" type="admin">
            </participant>
            <participant jid="{{JID}}">
            </participant>
          </group>
          <group s_t="{{SUBJECT_TIME}}" creation="{{CREATING_TIME}}" creator="{{OWNER_JID}}" id="{{GROUP_ID}}" s_o="{{SUBJECT_OWNER_JID}}" subject="{{SUBJECT}}">
            <participant jid="{{JID}}" type="admin">
            </participant>
          </group>
      <groups>
    </iq>
    '''

    def __init__(self, groupsList):
        super(ListGroupsResultIqProtocolEntity, self).__init__(_from = YowConstants.WHATSAPP_GROUP_SERVER)
        self.setProps(groupsList)

    def __str__(self):
        out = super(ListGroupsResultIqProtocolEntity, self).__str__()
        out += "Groups:\n"
        for g in self.groupsList:
            out += "%s\n" % g
        return out

    def getGroups(self):
        return self.groupsList

    def setProps(self, groupsList):
        assert type(groupsList) is list and (len(groupsList) == 0 or groupsList[0].__class__ is Group),\
            "groupList must be a list of Group instances"
        self.groupsList = groupsList


    def toProtocolTreeNode(self):
        node = super(ListGroupsResultIqProtocolEntity, self).toProtocolTreeNode()


        logger.info(f"Groups list: {self.groupsList}")
        groupsNodes = []
        for group in self.groupsList:
            groupNode = ProtocolTreeNode("group", {
                "id":       group.getId(),
                "creator":    group.getCreator(),
                "subject":  group.getSubject(),
                "s_o":      group.getSubjectOwner(),
                "s_t":      str(group.getSubjectTime()),
                "creation": str(group.getCreationTime())
                },
            )
            participants = []
            for jid, _type in group.getParticipants().items():
                pnode = ProtocolTreeNode("participant", {"jid": jid})
                if _type:
                    pnode["type"] = _type
                participants.append(pnode)
            groupNode.addChildren(participants)
            groupsNodes.append(groupNode)

        node.addChild(ProtocolTreeNode("groups", children = groupsNodes))
        return node

    @staticmethod
    def fromProtocolTreeNode(node):        
        entity = ResultIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = ListGroupsResultIqProtocolEntity
        groups = []                       

        logger.info(f"Groups: {node.getChild('groups').getAllChildren()}")
        for groupNode in node.getChild("groups").getAllChildren():
            participants = {}
            participants_phone_map = {}
            
            # Verifica se o grupo usa LID (Linked ID) ou JID normal
            valueName = "jid"
            if groupNode.getAttributeValue("addressing_mode") == "lid":
                valueName = "phone_number"
            
            for p in groupNode.getAllChildren("participant"):
                # Obtém jid (LID) e phone_number (JID normal) se disponível
                lid_jid = p["jid"]
                phone_number = p["phone_number"]
                participant_type = p["type"]
                
                # Se não tiver jid, tenta usar phone_number e converter para LID
                if not lid_jid:
                    if valueName == "phone_number":
                        participant_value = p.get(valueName) or p.get("jid")
                        if participant_value:
                            # Se for phone_number e não tiver @, converte para LID
                            if "@" not in participant_value:
                                lid_jid = Group.phone_to_lid(participant_value)
                            else:
                                # Se já tiver @, é o phone_number, precisa converter para LID
                                if not phone_number:
                                    phone_number = participant_value
                                phone_only = phone_number.split('@')[0]
                                lid_jid = Group.phone_to_lid(phone_only)
                    else:
                        lid_jid = p.get("jid")
                
                # Armazena o mapeamento phone_number -> lid_jid se ambos estiverem disponíveis
                if lid_jid and phone_number:
                    participants_phone_map[phone_number] = lid_jid
                    logger.debug(f"Mapped phone_number {phone_number} -> lid_jid {lid_jid}")
                
                # Armazena o participante usando lid_jid como chave
                if lid_jid:
                    participants[lid_jid] = participant_type
            
            groups.append(
                Group(groupNode["id"], groupNode["creator"], groupNode["subject"], groupNode["s_o"], groupNode["s_t"], groupNode["creation"], participants, participants_phone_map)
            )
        entity.setProps(groups)        
        return entity
