from ...layers import YowLayer, YowLayerEvent, YowProtocolLayer
from .protocolentities import *

from ...layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
import logging


from loguru import logger


class YowNotificationsProtocolLayer(YowProtocolLayer):

    def __init__(self):
        handleMap = {
            "notification": (self.recvNotification, self.sendNotification)
        }
        super(YowNotificationsProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "notification Ib Layer"

    def sendNotification(self, entity):
        if entity.getTag() == "notification":
            self.toLower(entity.toProtocolTreeNode())

    def recvNotification(self, node):

        if node["type"] == "mex":            
            self.toUpper(MexUpdateNotificationProtocolEntity.fromProtocolTreeNode(node))            

        elif node["type"] == "account_sync":
            self.toUpper(AccountSyncNotificationProtocolEntity.fromProtocolTreeNode(node))

        elif node["type"] == "link_code_companion_reg":
            print(node)
            self.toUpper(LinkCodeCompanionRegNotificationProtocolEntity.fromProtocolTreeNode(node))
            
        elif node["type"] == "registration":
            if node.getChild("wa_old_registration"):
                self.toUpper(WaOldCodeNotificationProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("device_logout"):
                self.toUpper(DeviceLogoutNotificationProtocolEntity.fromProtocolTreeNode(node))
            else:
                logger.warning("Unsupported notification subnode in registration node")     
                print(node)

        elif node["type"] == "business":            
            if node.getChild("verified_name"):                    
                n = node.getChild("verified_name")
                #有可能收到别人的，或者自己的
                logger.info(f"BusinessNameUpdateNotificationProtocolEntity: {node}")
                if n.getAttributeValue("jid") is not None:
                    self.toUpper(BusinessNameUpdateNotificationProtocolEntity.fromProtocolTreeNode(node))
                else:
                    print(node)            
            elif node.getChild("remove"):
                self.toUpper(BusinessRemoveNotificationProtocolEntity.fromProtocolTreeNode(node))
            else:
                #business实现不太完整，如果有其他的子节点，打印出来
                logger.warning("Unsupported notification subnode in business node")  
                print(node)

        elif node["type"] == "disappearing_mode":  
            if node.getChild("disappearing_mode"):
                self.toUpper(DisapperingModeNotificationProtocolEntity.fromProtocolTreeNode(node))            

        elif node["type"] == "picture":
            if node.getChild("set"):
                self.toUpper(SetPictureNotificationProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("delete"):
                self.toUpper(DeletePictureNotificationProtocolEntity.fromProtocolTreeNode(node))
            elif node.getChild("set_avatar"):
                #这个好像是新特性，先忽略异常
                pass
            else:
                self.raiseErrorForNode(node)
        elif node["type"] == "status":
            self.toUpper(StatusNotificationProtocolEntity.fromProtocolTreeNode(node))
            
        elif node["type"] in ["contacts", "subject", "w:gp2","devices"]:
            # Implemented in respectively the protocol_contacts,protocol_devices and protocol_groups layer
            pass
            
        elif node["type"] == "privacy_token":        
            logger.info(f"receive a privacy_token from {node['from'].split('@')[0]}")                        
            tokens = node.getChild("tokens")
            if tokens:
                for token in tokens.getAllChildren():
                    if token["type"]=="trusted_contact":
                        db = self.getStack().getProp("profile").axolotl_manager              
                        db._store.updateTrustedContact(node["from"], token.getData())  
                                
        elif node["type"] == "psa":            
            logger.info("receive a psa node,ignoring it ")            
        else:                        
            logger.warning(f"Unsupported notification type: {node['type']} ")            
            print(node)

        ack = OutgoingAckProtocolEntity(node["id"], "notification", node["type"], node["from"], participant=node["participant"])
        self.toLower(ack.toProtocolTreeNode())








