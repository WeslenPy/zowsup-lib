from ...layers import YowProtocolLayer
from .protocolentities import *
from ..protocol_iq.protocolentities import CleanDirtyIqProtocolEntity
import logging

from loguru import logger


class YowIbProtocolLayer(YowProtocolLayer):

    def __init__(self):
        handleMap = {
            "ib": (self.recvIb, self.sendIb),
            #"iq": (None, self.sendIb)
        }
        super(YowIbProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Ib Layer"

    def sendIb(self, entity):
        node =     entity.toProtocolTreeNode()    
        self.toLower(node)
        
    def recvIb(self, node):
        if node.getChild("dirty"):
            dirty_node = node.getChild("dirty")
            logger.info(f"auto clean {dirty_node['type']}")
            clean = CleanDirtyIqProtocolEntity(type=dirty_node["type"])
            self.toLower(clean.toProtocolTreeNode())
        elif node.getChild("offline"):
            self.toUpper(OfflineIbProtocolEntity.fromProtocolTreeNode(node))
        elif node.getChild("account"):
            self.toUpper(AccountIbProtocolEntity.fromProtocolTreeNode(node))
        elif node.getChild("edge_routing"):            
            entity = EdgeRoutingIbProtocolEntity.fromProtocolTreeNode(node)
            profile = self.getProp("profile")            
            if profile.config.edge_routing_info!=entity.routing_info:
                profile.config.edge_routing_info = entity.routing_info
                profile.write_config(profile.config)            
                logger.info("edge_routing_info change")                      
        elif node.getChild("attestation"):
            logger.info("ignoring attestation ib node")
        elif node.getChild("fbip"):
            logger.info("ignoring fbip ib node")
        elif node.getChild("notice"):
            logger.info("ignoring notice ib node")
        elif node.getChild("safetynet"):
            logger.info("ignoring safetynet ib node")
        elif node.getChild("gpia"):
            logger.info("ignoring gpia ib node")
        elif node.getChild("offline_preview"):
            logger.info(node)
        else:
            logger.warning(f"Unsupported ib node: \n{node}")
