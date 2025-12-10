class DisappearingModeAttributes(object):

    
    INITIATOR_CHANGED_IN_CHAT = 0
    INITIATOR_INITIATED_BY_ME = 1
    INITIATOR_INITIATED_BY_OTHER = 2
    INITIATOR_BIZ_UPGRADE_FB_HOSTING = 3
    
    TRIGGER_UNKNOWN = 0
    TRIGGER_CHAT_SETTING = 1
    TRIGGER_ACCOUNT_SETTING = 2
    TRIGGER_BULK_CHANGE = 3
    TRIGGER_BIZ_SUPPORTS_FB_HOSTING = 4
    def __init__(self, initiator=None,trigger=None, initiatedByMe=None,initiatorDeviceJid=None):
        self._initiator = initiator
        self._trigger = trigger
        self._initiatedByMe = initiatedByMe
        self._initiatorDeviceJid = initiatorDeviceJid

    def __str__(self):
        attrs = []
        if self.initiator is not None:
            attrs.append(("initiator", self.initiator))
        if self.trigger is not None:
            attrs.append(("trigger", self.trigger))
        if self.initiatedByMe is not None:
            attrs.append(("initiatedByMe", self.initiatedByMe))
        if self.initiatorDeviceJid is not None:
            attrs.append(("initiatorDeviceJid", self.initiatorDeviceJid))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def initiator(self):
        return self._trigger

    @initiator.setter
    def initiator(self, value):
        self._trigger = value

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, value):
        self._trigger = value

    @property
    def initiatedByMe(self):
        return self._initiatedByMe

    @initiatedByMe.setter
    def initiatedByMe(self, value):
        self._initiatedByMe = value

    @property
    def initiatorDeviceJid(self):
        return self._initiatorDeviceJid

    @initiatorDeviceJid.setter
    def initiatorDeviceJid(self, value):
        self._initiatorDeviceJid = value



