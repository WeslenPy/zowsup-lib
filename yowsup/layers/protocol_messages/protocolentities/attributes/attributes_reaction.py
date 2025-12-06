from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from proto import e2e_pb2

class ReactionAttributes(object):
    def __init__(self, msgid, remote_jid, from_me,text,sender_timestamp_ms,participant=None):

        self._msgid = msgid
        self._remote_jid = remote_jid        
        self._from_me = from_me
        self._text = text
        self._sender_timestamp_ms = sender_timestamp_ms
        self._participant = participant        

    def __str__(self):
        attrs = []        
        if self.msgid is not None:
            attrs.append(("msgid", self.msgid))
        if self.remote_jid is not None:
            attrs.append(("remote_jid",self.remote_jid))
        if self.from_me is not None:
            attrs.append(("from_me",self.from_me))
        if self.text is not None:
            attrs.append(("text",self.text))
        if self.sender_timestamp_ms is not None:
            attrs.append(("sender_timestamp_ms",self.sender_timestamp_ms))
        if self.participant is not None:
            attrs.append(("participant",self.participant))
                 
        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def msgid(self):
        return self._msgid

    @msgid.setter
    def msgid(self, value):
        self._msgid = value

    @property
    def remote_jid(self):
        return self._remote_jid

    @remote_jid.setter
    def remote_jid(self, value):
        self._remote_jid = value


    @property
    def from_me(self):
        return self._from_me

    @from_me.setter
    def from_me(self, value):
        self._from_me = value


    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value


    @property
    def sender_timestamp_ms(self):
        return self._sender_timestamp_ms

    @sender_timestamp_ms.setter
    def sender_timestamp_ms(self, value):
        self._sender_timestamp_ms = value

    @property
    def participant(self):
        return self._participant

    @participant.setter
    def participant(self, value):
        self._participant = value


