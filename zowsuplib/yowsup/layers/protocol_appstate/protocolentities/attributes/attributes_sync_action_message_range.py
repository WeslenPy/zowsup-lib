class SyncActionMessageRangeAttribute(object):
    def __init__(self, lastMessageTimestamp, lastSystemMessageTimestamp,messages):
        self.lastMessageTimestamp = lastMessageTimestamp
        self.lastSystemMessageTimestamp= lastSystemMessageTimestamp
        self.messages = messages        





