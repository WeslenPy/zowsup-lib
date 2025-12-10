from .iq_picture import PictureIqProtocolEntity

class ResultSetPictureIqProtocolEntity(PictureIqProtocolEntity):
    '''
    <iq type="result" from="s.whatsapp.net" id="{{id}}">
        <picture id="{{another_id}}"/>                
    </iq>
    '''
    def __init__(self, pictureId , _id = None):
        super(ResultSetPictureIqProtocolEntity, self).__init__(_id = _id, type = "result")
        self.setResultProps( pictureId)

    def setResultProps(self,  pictureId):
        self.pictureId = pictureId

    def getPictureId(self):
        return self.pictureId
    
    @staticmethod
    def fromProtocolTreeNode(node):
        entity = PictureIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = ResultSetPictureIqProtocolEntity
        pictureNode = node.getChild("picture")
        entity.setResultProps(pictureNode.getAttributeValue("id"))
        
        return entity

