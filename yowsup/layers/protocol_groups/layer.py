from ...layers import YowLayer, YowLayerEvent, YowProtocolLayer
from ...layers.protocol_iq.protocolentities import ErrorIqProtocolEntity
from ...layers.protocol_iq.protocolentities.iq_result import ResultIqProtocolEntity
from .protocolentities import *
import logging
from loguru import logger


class YowGroupsProtocolLayer(YowProtocolLayer):

    HANDLE = (
        CreateGroupsIqProtocolEntity,
        InfoGroupsIqProtocolEntity,
        LeaveGroupsIqProtocolEntity,
        ListGroupsIqProtocolEntity,
        SubjectGroupsIqProtocolEntity,
        ParticipantsGroupsIqProtocolEntity,
        AddParticipantsIqProtocolEntity,
        PromoteParticipantsIqProtocolEntity,
        DemoteParticipantsIqProtocolEntity,
        RemoveParticipantsIqProtocolEntity,
        JoinWithCodeGroupsIqProtocolEntity,        
        SetGroupsIqProtocolEntity,
        ApproveParticipantsGroupsIqProtocolEntity,
        GetInviteCodeGroupsIqProtocolEntity
    )

    def __init__(self):
        handleMap = {
            "iq": (self.recvIq, self.sendIq),
            "notification": (self.recvNotification, None)
        }
        super(YowGroupsProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Groups Iq Layer"
    
    def recvIq(self, node):        
        if node["type"] == "result":
            rNode = node.getChild(0)
            if rNode is None:
                # process in protocol_iq
                pass
            elif rNode.tag=="groups":
                #listgroup
                self.toUpper(ListGroupsResultIqProtocolEntity.fromProtocolTreeNode(node))

            elif rNode.tag=="group":
                #groupinfo or creategroup or join 都是这个结构
                if node["from"].endswith("@g.us"):
                    self.toUpper(InfoGroupsResultIqProtocolEntity.fromProtocolTreeNode(node))
                elif node["from"].endswith("g.us"):
                    if rNode["jid"] is not None:
                        self.toUpper(SuccessJoinWithCodeGroupsIqProtocolEntity.fromProtocolTreeNode(node))
                    elif rNode["id"] is not None:
                        self.toUpper(SuccessCreateGroupsIqProtocolEntity.fromProtocolTreeNode(node))
                    else:
                        logger.warning("unknown group result node, please complete the process-branch")
            elif rNode.tag=="add":
                self.toUpper(SuccessAddParticipantsIqProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag=="remove":
                self.toUpper(SuccessRemoveParticipantsIqProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag=="promote":
                self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag=="demote":
                self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag=="leave":
                self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag=="invite":
                self.toUpper(SuccessGetInviteCodeGroupsIqProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag in ["locked","unlocked","announcement","not_announcement","membership_approval_mode","membership_requests_action"]:
                self.toUpper(ResultIqProtocolEntity.fromProtocolTreeNode(node))
    
    def sendIq(self, entity):        
        if entity.getXmlns() == "w:g2":      
            node = entity.toProtocolTreeNode()            
            self.toLower(node)  

    def recvNotification(self, node):     
        if node["type"] == "w:gp2":    
            rNode = node.getChild(0)
            if rNode.tag == "subject":                   
                self.toUpper(SubjectGroupsNotificationProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag == "create":
                if rNode["reason"] is not None:
                    self.toUpper(InviteGroupsNotificationProtocolEntity.fromProtocolTreeNode(node))
                else:
                    self.toUpper(CreateGroupsNotificationProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag =="remove":
                self.toUpper(RemoveGroupsNotificationProtocolEntity.fromProtocolTreeNode(node))
            elif rNode.tag == "add":
                self.toUpper(AddGroupsNotificationProtocolEntity.fromProtocolTreeNode(node))


    # 还剩设置主题和设置描述两个接口还没完善








