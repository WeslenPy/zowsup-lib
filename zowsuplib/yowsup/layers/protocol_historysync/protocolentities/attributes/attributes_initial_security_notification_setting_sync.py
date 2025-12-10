class InitialSecurityNotificationSettingSyncAttribute(object):
    def __init__(self, security_notification_enabled=True):
        self._security_notification_enabled = security_notification_enabled

    @property
    def security_notification_enabled(self):
        return self._security_notification_enabled

    @security_notification_enabled.setter
    def security_notification_enabled(self, value):
        self._security_notification_enabled = value




