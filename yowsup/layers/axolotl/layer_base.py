from ...layers import YowProtocolLayer
from ...layers.axolotl.protocolentities import *
from ...layers.network.layer import YowNetworkLayer
from ...layers import EventCallback
from ...profile.profile import YowProfile

from ...axolotl import exceptions
from ...layers.axolotl.props import PROP_IDENTITY_AUTOTRUST

import logging
from loguru import logger


class AxolotlBaseLayer(YowProtocolLayer):
    def __init__(self):
        super(AxolotlBaseLayer, self).__init__()
        self._manager = None  # type: AxolotlManager | None
        self.skipEncJids = []

    def send(self, node):
        pass

    def receive(self, node):
        self.processIqRegistry(node)

    @property
    def manager(self):
        """
        :return:
        :rtype: AxolotlManager
        """
        return self._manager

    @EventCallback(YowNetworkLayer.EVENT_STATE_CONNECTED)
    def on_connected(self, yowLayerEvent):
        profile = self.getProp("profile")  # type: YowProfile
        if profile is not None:
            self._manager = profile.axolotl_manager

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def on_disconnected(self, yowLayerEvent):
        self._manager = None
        

    def getKeysFor(self, jids, resultClbk, errorClbk = None, reason=None):
        logger.debug(f"getKeysFor(jids={jids}, resultClbk=[omitted], errorClbk=[omitted], reason={reason})")
        def onSuccess(resultNode, getKeysEntity):                        
            entity = ResultGetKeysIqProtocolEntity.fromProtocolTreeNode(resultNode)
                        
            resultJids = entity.getJids()          
            successJids = []
            errorJids = entity.getErrors() #jid -> exception
            for jid in getKeysEntity.jids:
          
                if jid not in resultJids:
                    self.skipEncJids.append(jid)
                    continue
                username = jid.split('@')[0]
                preKeyBundle = entity.getPreKeyBundleFor(jid)
                try:                    
                    self.manager.create_session(username, preKeyBundle,
                                                autotrust=self.getProp(PROP_IDENTITY_AUTOTRUST, False))
                    successJids.append(jid)
                except exceptions.UntrustedIdentityException as e:
                        errorJids[jid] = e
                        logger.error(e)
                        logger.warning("Ignoring message with untrusted identity")

            resultClbk(successJids, errorJids)

        def onError(errorNode, getKeysEntity):
            print("ERROR ON GETKEY")
            if errorClbk:
                errorClbk(errorNode, getKeysEntity)

        idType = self.getProp("ID_TYPE")
        entity = GetKeysIqProtocolEntity(jids, reason=reason,_id=idType)
        self._sendIq(entity, onSuccess, onError=onError)
