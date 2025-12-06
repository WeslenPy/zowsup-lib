from loguru import logger
from ....structs import ProtocolEntity
from ....layers.protocol_receipts.protocolentities  import OutgoingReceiptProtocolEntity
from ....layers.protocol_messages.protocolentities.attributes.attributes_message_meta import MessageMetaAttributes
from copy import deepcopy


class MessageProtocolEntity(ProtocolEntity):

    MESSAGE_TYPE_TEXT = "text"
    MESSAGE_TYPE_MEDIA = "media"

    def __init__(self, messageType, messageMetaAttributes):
        """
        :type messageType: str
        :type messageMetaAttributes: MessageMetaAttributes
        """
        super(MessageProtocolEntity, self).__init__("message")
        assert type(messageMetaAttributes) is MessageMetaAttributes

        self._type = messageType        

        if messageMetaAttributes.id is None:
            messageMetaAttributes.id = ProtocolEntity.ID_TYPE_ANDROID


        if messageMetaAttributes.id==ProtocolEntity.ID_TYPE_ANDROID or messageMetaAttributes.id==ProtocolEntity.ID_TYPE_IOS :
            self._id = self._generateId(type=messageMetaAttributes.id)      
        else:
            self._id = messageMetaAttributes.id

        self._from = messageMetaAttributes.sender
        self._from_pn = messageMetaAttributes.sender_pn or messageMetaAttributes.from_pn
        self.to = messageMetaAttributes.recipient
        self.timestamp = messageMetaAttributes.timestamp or self._getCurrentTimestamp()
        self.notify = messageMetaAttributes.notify
        self.offline = messageMetaAttributes.offline
        self.retry = messageMetaAttributes.retry
        self.participant= messageMetaAttributes.participant
        self.fromme = messageMetaAttributes.fromMe   
        self.category = messageMetaAttributes.category     
        self.phash = messageMetaAttributes.phash
        self.edit = messageMetaAttributes.edit

    def getFromMe(self):
        return self.fromme        

    def getType(self):
        return self._type

    def getId(self):
        return self._id

    def getTimestamp(self):
        return self.timestamp

    def getFrom(self, full = True):
        return self._from if full else self._from.split('@')[0]

    def getFromPn(self, full = True):
        if self._from_pn is None:
            return None
        return self._from_pn if full else self._from_pn.split('@')[0]

    def isBroadcast(self):
        return False

    def getTo(self, full = True):
        return self.to if full else self.to.split('@')[0]

    def getParticipant(self, full = True):
        if self.participant is None:
            return None
                
        return self.participant if full else self.participant.split('@')[0]

    def getAuthor(self, full = True):
        return self.getParticipant(full) if self.isGroupMessage() else self.getFrom(full)

    def getNotify(self):
        return self.notify
    
    def getCategory(self):
        return self.category

    def getNotify(self):
        return self.notify    

    def toProtocolTreeNode(self):
        attribs = {
            "type"      : self._type,
            "id"        : self._id            
        }


        logger.info(f"[MessageProtocolEntity] toProtocolTreeNode chamado - attribs: {attribs}")

        if self.category is not None:
            attribs["category"] = self.category

        if self.participant:
            attribs["participant"] = self.participant

        if self.isOutgoing():
            attribs["to"] = self.to
            #attribs["phash"] = "2:AIlF5031"            
            if (attribs["to"].endswith("@broadcast") or attribs["to"].endswith("g.us")) and self.phash is not None:      
                          
                attribs["phash"] = self.phash
            if self.category is not None:
                attribs["category"] = self.category
        else:
            attribs["from"] = self._from
            attribs["from_pn"] = self._from_pn
            attribs["t"] = str(self.timestamp)
            if self.offline is not None:
               attribs["offline"] = "1" if self.offline else "0"
            if self.notify:
                attribs["notify"] = self.notify
            if self.retry:
                attribs["retry"] = str(self.retry)

        if self.edit:
            attribs["edit"] = self.edit
        xNode = None
        #if self.isOutgoing():
        #    serverNode = ProtocolTreeNode("server", {})
        #    xNode = ProtocolTreeNode("x", {"xmlns": "jabber:x:event"}, [serverNode])


        return self._createProtocolTreeNode(attribs, children = [xNode] if xNode else None, data = None)

    def isOutgoing(self):
        return self._from is None

    def isGroupMessage(self):
        if self.isOutgoing():
            return "-" in self.to
        return self.participant != None

    def __str__(self):
        out  = "Message:\n"
        out += "ID: %s\n" % self._id
        out += "To: %s\n" % self.to  if self.isOutgoing() else "From: %s\n" % self._from
        out += "Type:  %s\n" % self._type
        out += "Timestamp: %s\n" % self.timestamp
        if self.participant:
            out += "Participant: %s\n" % self.participant
        return out

    def ack(self, read=False):
        return OutgoingReceiptProtocolEntity(self.getId(), self.getFrom(), read, participant=self.getParticipant())

    def forward(self, to, _id = None):
        OutgoingMessage = deepcopy(self)
        OutgoingMessage.to = to
        OutgoingMessage._from = None
        OutgoingMessage._id = self._generateId() if _id is None else _id
        return OutgoingMessage

    @staticmethod
    def fromProtocolTreeNode(node,proto=None):

        gen_message_meta = MessageMetaAttributes.from_message_protocoltreenode(node,proto)
        logger.info(f"[MessageProtocolEntity] fromProtocolTreeNode chamado - gen_message_meta: {gen_message_meta}")

        node_message= MessageProtocolEntity(
            node["type"],
            gen_message_meta
        )

        logger.info(f"[MessageProtocolEntity] fromProtocolTreeNode chamado - node_message: {node_message}")
        return node_message