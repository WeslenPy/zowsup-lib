from ..layers import YowParallelLayer
import time, logging, random
from ..layers import YowLayer
from ..layers.noise.layer import YowNoiseLayer
from ..layers.noise.layer_noise_segments import YowNoiseSegmentsLayer
from ..layers.auth                        import YowAuthenticationProtocolLayer
from ..layers.coder                       import YowCoderLayer
from ..layers.logger                      import YowLoggerLayer
from ..layers.network                     import YowNetworkLayer
from ..layers.protocol_messages           import YowMessagesProtocolLayer
from ..layers.protocol_media              import YowMediaProtocolLayer
from ..layers.protocol_acks               import YowAckProtocolLayer
from ..layers.protocol_receipts           import YowReceiptProtocolLayer
from ..layers.protocol_groups             import YowGroupsProtocolLayer
from ..layers.protocol_presence           import YowPresenceProtocolLayer
from ..layers.protocol_ib                 import YowIbProtocolLayer
from ..layers.protocol_notifications      import YowNotificationsProtocolLayer
from ..layers.protocol_iq                 import YowIqProtocolLayer
from ..layers.protocol_contacts           import YowContactsIqProtocolLayer
from ..layers.protocol_chatstate          import YowChatstateProtocolLayer
from ..layers.protocol_privacy            import YowPrivacyProtocolLayer
from ..layers.protocol_profiles           import YowProfilesProtocolLayer
from ..layers.protocol_calls import YowCallsProtocolLayer
from ..common.constants import YowConstants
from ..layers.axolotl import AxolotlSendLayer, AxolotlControlLayer, AxolotlReceivelayer
from ..profile.profile import YowProfile
import inspect
try:
    import Queue
except ImportError:
    import queue as Queue
from loguru import logger

YOWSUP_PROTOCOL_LAYERS_BASIC = (
    YowAuthenticationProtocolLayer, YowMessagesProtocolLayer,
    YowReceiptProtocolLayer, YowAckProtocolLayer, YowPresenceProtocolLayer,
    YowIbProtocolLayer, YowIqProtocolLayer, YowNotificationsProtocolLayer,
    YowContactsIqProtocolLayer, YowChatstateProtocolLayer, YowCallsProtocolLayer

)


class YowStackBuilder(object):
    def __init__(self):
        self.layers = ()
        self._props = {}

    def setProp(self, key, value):
        self._props[key] = value
        return self

    def pushDefaultLayers(self):
        defaultLayers = YowStackBuilder.getDefaultLayers()
        self.layers += defaultLayers
        return self

    def push(self, yowLayer):
        self.layers += (yowLayer,)
        return self

    def pop(self):
        self.layers = self.layers[:-1]
        return self

    def build(self):
        return YowStack(self.layers, reversed = False, props = self._props)

    @staticmethod
    def getDefaultLayers(groups = True, media = True, privacy = True, profiles = True):
        coreLayers = YowStackBuilder.getCoreLayers()
        protocolLayers = YowStackBuilder.getProtocolLayers(groups = groups, media=media, privacy=privacy, profiles=profiles)

        allLayers = coreLayers
        allLayers += (AxolotlControlLayer,)
        allLayers += (YowParallelLayer((AxolotlSendLayer, AxolotlReceivelayer)),)

        allLayers += (YowParallelLayer(protocolLayers),)

        return allLayers

    @staticmethod
    def getDefaultStack(layer = None, axolotl = False, groups = True, media = True, privacy = True, profiles = True):
        """
        :param layer: An optional layer to put on top of default stack
        :param axolotl: E2E encryption enabled/ disabled
        :return: YowStack
        """

        allLayers = YowStackBuilder.getDefaultLayers(axolotl, groups = groups, media=media,privacy=privacy, profiles=profiles)
        if layer:
            allLayers = allLayers + (layer,)


        return YowStack(allLayers, reversed = False)

    @staticmethod
    def getCoreLayers():
        return (
            YowLoggerLayer,
            YowCoderLayer,
            YowNoiseLayer,
            YowNoiseSegmentsLayer,
            YowNetworkLayer
        )[::-1]

    @staticmethod
    def getProtocolLayers(groups = True, media = True, privacy = True, profiles = True):
        layers = YOWSUP_PROTOCOL_LAYERS_BASIC
        if groups:
            layers += (YowGroupsProtocolLayer,)

        if media:
            layers += (YowMediaProtocolLayer, )

        if privacy:
            layers += (YowPrivacyProtocolLayer, )

        if profiles:
            layers += (YowProfilesProtocolLayer, )

        return layers

class YowStack(object):
    __stack = []
    __stackInstances = []
    __detachedQueue = Queue.Queue()
    def __init__(self, stackClassesArr = None, reversed = True, props = None):
        stackClassesArr = stackClassesArr or ()
        self.__stack = stackClassesArr[::-1] if reversed else stackClassesArr
        self.__stackInstances = []
        self._props = props or {}

        self.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[random.randint(0,len(YowConstants.ENDPOINTS)-1)])
        self._construct()


    def getLayerInterface(self, YowLayerClass):
        for inst in self.__stackInstances:
            if inst.__class__ == YowLayerClass:
                return inst.getLayerInterface()
            elif inst.__class__ == YowParallelLayer:
                res = inst.getLayerInterface(YowLayerClass)
                if res:
                    return res


    def send(self, data):
        self.__stackInstances[-1].send(data)

    def receive(self, data):
        self.__stackInstances[0].receive(data)

    def setCredentials(self, credentials):
        logger.warning("setCredentials is deprecated and any passed-in keypair is ignored, "
                       "use setProfile(YowProfile) instead")
        profile_name, keypair = credentials
        self.setProfile(YowProfile(profile_name))

    def setProfile(self, profile):
        # type: (str | YowProfile) -> None
        """
        :param profile: profile to use.
        :return:
        """
        logger.debug(f"setProfile({profile})")
        self.setProp("profile", profile if isinstance(profile, YowProfile) else YowProfile(profile))

    def addLayer(self, layerClass):
        self.__stack.push(layerClass)

    def addPostConstructLayer(self, layer):
        self.__stackInstances[-1].setLayers(layer, self.__stackInstances[-2])
        layer.setLayers(None, self.__stackInstances[-1])
        self.__stackInstances.append(layer)

    def setProp(self, key, value):
        self._props[key] = value

    def getProp(self, key, default = None):
        return self._props[key] if key in self._props else default

    def emitEvent(self, yowLayerEvent):
        if not self.__stackInstances[0].onEvent(yowLayerEvent):
            self.__stackInstances[0].emitEvent(yowLayerEvent)

    def broadcastEvent(self, yowLayerEvent):
        if not self.__stackInstances[-1].onEvent(yowLayerEvent):
            self.__stackInstances[-1].broadcastEvent(yowLayerEvent)

    def execDetached(self, fn):
        self.__class__.__detachedQueue.put(fn)

    def loop(self, *args, **kwargs):
        while True:
            try:
                callback = self.__class__.__detachedQueue.get(False) #doesn't block
                callback()
            except Queue.Empty:
                break
                pass
            time.sleep(0.1)

    def _construct(self):
        logger.debug("Initializing stack")
        for s in self.__stack:
            if type(s) is tuple:
                logger.warn("Implicit declaration of parallel layers in a tuple is deprecated, pass a YowParallelLayer instead")
                inst = YowParallelLayer(s)
            else:
                if inspect.isclass(s):
                    if issubclass(s, YowLayer):
                        inst = s()
                    else:
                        raise ValueError("Stack must contain only subclasses of YowLayer")
                elif issubclass(s.__class__, YowLayer):
                        inst = s
                else:
                    raise ValueError("Stack must contain only subclasses of YowLayer")
                #inst = s()
            logger.debug(f"Constructed {inst}")
            inst.setStack(self)
            self.__stackInstances.append(inst)

        for i in range(0, len(self.__stackInstances)):
            upperLayer = self.__stackInstances[i + 1] if (i + 1) < len(self.__stackInstances) else None
            lowerLayer = self.__stackInstances[i - 1] if i > 0 else None
            self.__stackInstances[i].setLayers(upperLayer, lowerLayer)

    def getLayer(self, layerIndex):
        return self.__stackInstances[layerIndex]
