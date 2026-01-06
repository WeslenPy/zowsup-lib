from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups import GroupsIqProtocolEntity


class SubjectGroupsIqProtocolEntity(GroupsIqProtocolEntity):
    '''
    <iq type="set" id="{{id}}" xmlns="w:g2", to={{group_jid}}">
        <subject>
              {{NEW_VAL}}
        </subject>
    </iq>
    '''
    def __init__(self, jid, subject, _id = None):
        super(SubjectGroupsIqProtocolEntity, self).__init__(to = jid, _id = _id, _type = "set")
        self.setProps(subject)

    def setProps(self, subject):
        self.subject = subject

    def toProtocolTreeNode(self):
        node = super(SubjectGroupsIqProtocolEntity, self).toProtocolTreeNode()
        # ProtocolTreeNode espera bytes, não string
        subject_data = self.subject.encode("utf-8") if isinstance(self.subject, str) else self.subject
        node.addChild(ProtocolTreeNode("subject",{}, None, subject_data))
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = super(SubjectGroupsIqProtocolEntity, SubjectGroupsIqProtocolEntity).fromProtocolTreeNode(node)
        entity.__class__ = SubjectGroupsIqProtocolEntity
        subject_data = node.getChild("subject").getData()
        # Decodifica bytes para string se necessário
        subject = subject_data.decode("utf-8") if isinstance(subject_data, bytes) else subject_data
        entity.setProps(subject)
        return entity


