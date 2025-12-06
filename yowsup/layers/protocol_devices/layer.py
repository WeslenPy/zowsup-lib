from ...layers import YowProtocolLayer
from .protocolentities import *
import logging

from loguru import logger

class YowDevicesIqProtocolLayer(YowProtocolLayer):
    def __init__(self):
        handleMap = {
            "iq": (self.recvIq, self.sendIq),
            "notification": (self.recvNotification, None)
        }
        super(YowDevicesIqProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Device Iq Layer"

    def recvNotification(self, node):

        if node["type"] == "devices":
            if node.getChild("remove"):
                self.toUpper(RemoveDeviceNotificationProtocolEntity.fromProtocolTreeNode(node))

            elif node.getChild("add"):
                self.toUpper(AddDeviceNotificationProtocolEntity.fromProtocolTreeNode(node))

            elif node.getChild("update"):
                pass
            else :
                logger.warning(f"Unsupported device notification type: {node['type']} ")
                logger.debug(f"Unsupported device notification node: {node}")

    def recvIq(self, node):        
        pass

    def sendIq(self, entity):
        
        pass
