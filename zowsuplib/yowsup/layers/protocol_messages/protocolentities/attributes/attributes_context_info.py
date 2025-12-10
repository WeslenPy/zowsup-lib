class ContextInfoAttributes(object):
    def __init__(self,
                 stanza_id=None,
                 participant=None,
                 quoted_message=None,
                 remote_jid=None,
                 mentioned_jid=None,
                 edit_version=None,
                 revoke_message=None,
                 conversion_delay_seconds=None,
                 forwarding_score=None,
                 is_forwarded=None,
                 expiration=None,
                 ephemeral_setting_timestamp=None,
                 external_ad_reply = None,
                 entry_point_conversion_source = None,
                 entry_point_conversion_app = None,
                 entry_point_conversion_delay_seconds = None,
                 disappearing_mode = None,
                 action_link = None,
                 business_message_forward_info = None
                ):
        
        self._stanza_id = stanza_id
        self._participant = participant
        self._quoted_message = quoted_message
        self._remote_jid = remote_jid
        self._mentioned_jid = mentioned_jid or []
        self._edit_version = edit_version
        self._revoke_message = revoke_message
        self._conversion_delay_seconds = conversion_delay_seconds
        self._forwarding_score=forwarding_score
        self._is_forwarded = is_forwarded
        self._expiration = expiration
        self._ephemeral_setting_timestamp = ephemeral_setting_timestamp
        self._external_ad_reply = external_ad_reply
        self._entry_point_conversion_source = entry_point_conversion_source
        self._entry_point_conversion_app = entry_point_conversion_app
        self._entry_point_conversion_delay_seconds = entry_point_conversion_delay_seconds
        self._disappearing_mode = disappearing_mode
        self._action_link = action_link
        self._business_message_forward_info = business_message_forward_info

    def __str__(self):
        attribs = []
        if self._stanza_id is not None:
            attribs.append(("stanza_id", self.stanza_id))
        if self._participant is not None:
            attribs.append(("participant", self.participant))
        if self.quoted_message is not None:
            attribs.append(("quoted_message", self.quoted_message))
        if self._remote_jid is not None:
            attribs.append(("remote_jid", self.remote_jid))
        if self.mentioned_jid is not None and len(self.mentioned_jid):
            attribs.append(("mentioned_jid", self.mentioned_jid))
        if self.edit_version is not None:
            attribs.append(("edit_version", self.edit_version))
        if self.revoke_message is not None:
            attribs.append(("revoke_message", self.revoke_message))  

        if self.entry_point_conversion_source is not None:
            attribs.append(("entry_point_conversion_source", self.entry_point_conversion_source))
        if self.entry_point_conversion_app is not None:
            attribs.append(("entry_point_conversion_app", self.entry_point_conversion_app))      
        if self.entry_point_conversion_delay_seconds is not None:
            attribs.append(("entry_point_conversion_delay_seconds", str(self.entry_point_conversion_delay_seconds)))      

        if self.is_forwarded is not None:
            attribs.append(("is_forwarded",str(self.is_forwarded)))

        if self.external_ad_reply is not None:
            attribs.append(("external_ad_reply",str(self.external_ad_reply)))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attribs)))
    

    @property
    def disappearing_mode(self):
        return self._disappearing_mode

    @disappearing_mode.setter
    def disappearing_mode(self, value):
        self._disappearing_mode = value       

    @property
    def conversion_delay_seconds(self):
        return self._conversion_delay_seconds

    @conversion_delay_seconds.setter
    def conversion_delay_seconds(self, value):
        self._conversion_delay_seconds = value    

    @property
    def expiration(self):
        return self._expiration

    @expiration.setter
    def expiration(self, value):
        self._expiration = value            

    @property
    def ephemeral_setting_timestamp(self):
        return self._ephemeral_setting_timestamp

    @ephemeral_setting_timestamp.setter
    def ephemeral_setting_timestamp(self, value):
        self._ephemeral_setting_timestamp = value          

    @property
    def external_ad_reply(self):
        return self._external_ad_reply

    @external_ad_reply.setter
    def external_ad_reply(self, value):
        self._external_ad_reply = value  

    @property
    def business_message_forward_info(self):
        return self._business_message_forward_info

    @business_message_forward_info.setter
    def business_message_forward_info(self, value):
        self._business_message_forward_info = value  

        

    @property
    def entry_point_conversion_source(self):
        return self._entry_point_conversion_source

    @entry_point_conversion_source.setter
    def entry_point_conversion_source(self, value):
        self._entry_point_conversion_source = value

    @property
    def entry_point_conversion_app(self):
        return self._entry_point_conversion_app

    @entry_point_conversion_app.setter
    def entry_point_conversion_app(self, value):
        self._entry_point_conversion_app = value

    @property
    def entry_point_conversion_delay_seconds(self):
        return self._entry_point_conversion_delay_seconds

    @entry_point_conversion_delay_seconds.setter
    def entry_point_conversion_delay_seconds(self, value):
        self._entry_point_conversion_delay_seconds = value


    @property
    def action_link(self):
        return self._action_link

    @action_link.setter
    def action_link(self, value):
        self._action_link = value        

    @property
    def stanza_id(self):
        return self._stanza_id

    @stanza_id.setter
    def stanza_id(self, value):
        self._stanza_id = value

    @property
    def participant(self):
        return self._participant

    @participant.setter
    def participant(self, value):
        self._participant = value

    @property
    def quoted_message(self):
        return self._quoted_message

    @quoted_message.setter
    def quoted_message(self, value):
        self._quoted_message = value

    @property
    def remote_jid(self):
        return self._remote_jid

    @remote_jid.setter
    def remote_jid(self, value):
        self._remote_jid = value

    @property
    def mentioned_jid(self):
        return self._mentioned_jid

    @mentioned_jid.setter
    def mentioned_jid(self, value):
        self._mentioned_jid = value

    @property
    def edit_version(self):
        return self._edit_version

    @edit_version.setter
    def edit_version(self, value):
        self._edit_version = value

    @property
    def revoke_message(self):
        return self._revoke_message

    @revoke_message.setter
    def revoke_message(self, value):
        self._revoke_message = value


    @property
    def is_forwarded(self):
        return self._is_forwarded

    @is_forwarded.setter
    def is_forwarded(self, value):
        self._is_forwarded = value

    @property
    def forwarding_score(self):
        return self._forwarding_score

    @forwarding_score.setter
    def forwarding_score(self, value):
        self._forwarding_score = value        


