from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq_groups import GroupsIqProtocolEntity


class DescriptionGroupsIqProtocolEntity(GroupsIqProtocolEntity):
    '''
    <iq type="set" id="{{id}}" xmlns="w:g2", to={{group_jid}}">
        <description id="{{new_id}}" prev="{{previous_id}}" delete="{{true if empty}}">
            <body>{{description_bytes}}</body>
        </description>
    </iq>
    '''
    def __init__(self, jid, description, new_id=None, previous_id=None, _id=None):
        super(DescriptionGroupsIqProtocolEntity, self).__init__(to=jid, _id=_id, _type="set")
        self.setProps(description, new_id, previous_id)

    def setProps(self, description, new_id=None, previous_id=None):
        self.description = description
        self.new_id = new_id
        self.previous_id = previous_id

    def toProtocolTreeNode(self):
        node = super(DescriptionGroupsIqProtocolEntity, self).toProtocolTreeNode()
        
        # Atributos do nó description
        attrs = {}
        if self.new_id:
            attrs["id"] = self.new_id
        if self.previous_id:
            attrs["prev"] = self.previous_id
        
        # Se a descrição estiver vazia, marca para deletar
        is_delete = not self.description or len(self.description.strip()) == 0
        if is_delete:
            attrs["delete"] = "true"
        
        # Conteúdo: nó body com a descrição (ou None se for deletar)
        content = None
        if not is_delete:
            # ProtocolTreeNode espera bytes, não string
            description_data = self.description.encode("utf-8") if isinstance(self.description, str) else self.description
            body_node = ProtocolTreeNode("body", {}, None, description_data)
            content = [body_node]
        
        node.addChild(ProtocolTreeNode("description", attrs, content))
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = super(DescriptionGroupsIqProtocolEntity, DescriptionGroupsIqProtocolEntity).fromProtocolTreeNode(node)
        entity.__class__ = DescriptionGroupsIqProtocolEntity
        
        desc_node = node.getChild("description")
        if desc_node:
            # Obtém atributos
            new_id = desc_node.getAttributeValue("id")
            previous_id = desc_node.getAttributeValue("prev")
            
            # Obtém o conteúdo do body
            body_node = desc_node.getChild("body")
            description = ""
            if body_node:
                description_data = body_node.getData()
                # Decodifica bytes para string se necessário
                description = description_data.decode("utf-8") if isinstance(description_data, bytes) else description_data
            
            entity.setProps(description, new_id, previous_id)
        else:
            entity.setProps("", None, None)
        
        return entity


