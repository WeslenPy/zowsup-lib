from .....layers.protocol_messages.protocolentities.attributes.attributes_message_key import MessageKeyAttributes


class ProtocolAttributes(object):
    TYPE_REVOKE = 0
    TYPE_EPHEMERAL_SETTING = 3
    TYPE_EPHEMERAL_SYNC_RESPONSE = 4
    TYPE_HISTORY_SYNC_NOTIFICATION = 5
    TYPE_APP_STATE_SYNC_KEY_SHARE = 6
    TYPE_APP_STATE_SYNC_KEY_REQUEST = 7
    TYPE_MSG_FANOUT_BACKFILL_REQUEST = 8
    TYPE_INITIAL_SECURITY_NOTIFICATION_SETTING_SYNC = 9
    TYPE_APP_STATE_FATAL_EXCEPTION_NOTIFICATION = 10
    TYPE_SHARE_PHONE_NUMBER = 11
    TYPE_MESSAGE_EDIT = 14
    TYPE_PEER_DATA_OPERATION_REQUEST_MESSAGE = 16
    TYPE_PEER_DATA_OPERATION_REQUEST_RESPONSE_MESSAGE = 17
    TYPE_REQUEST_WELCOME_MESSAGE = 18
    TYPE_BOT_FEEDBACK_MESSAGE = 19
    TYPE_MEDIA_NOTIFY_MESSAGE = 20    

    TYPES = {
        TYPE_REVOKE: "REVOKE", 
        TYPE_EPHEMERAL_SETTING:"EPHEMERAL_SETTING",
        TYPE_EPHEMERAL_SYNC_RESPONSE:"EPHEMERAL_SYNC_RESPONSE",        
        TYPE_HISTORY_SYNC_NOTIFICATION :"HISTORY_SYNC_NOTIFICATION",
        TYPE_APP_STATE_SYNC_KEY_SHARE :"APP_STATE_SYNC_KEY_SHARE",
        TYPE_APP_STATE_SYNC_KEY_REQUEST:"APP_STATE_SYNC_KEY_REQUEST",
        TYPE_MSG_FANOUT_BACKFILL_REQUEST:"MSG_FANOUT_BACKFILL_REQUEST",            
        TYPE_INITIAL_SECURITY_NOTIFICATION_SETTING_SYNC :"INITIAL_SECURITY_NOTIFICATION_SETTING_SYNC",
        TYPE_APP_STATE_FATAL_EXCEPTION_NOTIFICATION :"APP_STATE_FATAL_EXCEPTION_NOTIFICATION",
        TYPE_SHARE_PHONE_NUMBER:"SHARE_PHONE_NUMBER",
        TYPE_MESSAGE_EDIT:"MESSAGE_EDIT",
        TYPE_PEER_DATA_OPERATION_REQUEST_MESSAGE:"PEER_DATA_OPERATION_REQUEST_MESSAGE",
        TYPE_REQUEST_WELCOME_MESSAGE:"REQUEST_WELCOME_MESSAGE",
        TYPE_BOT_FEEDBACK_MESSAGE:"BOT_FEEDBACK_MESSAGE",
        TYPE_MEDIA_NOTIFY_MESSAGE:"MEDIA_NOTIFY_MESSAGE"
    }

    def __init__(self, 
                 key=None, 
                 type=None,
                 ephemeral_expiration=None,
                 ephemeral_setting_timestamp=None,
                 history_sync_notification=None,
                 app_state_sync_key_share=None,
                 app_state_sync_key_request=None,
                 initial_security_notification_setting_sync=None,
                 app_state_fatal_exception_notification=None,
                 disappearing_mode=None,
                 edited_message=None,
                 timestamp_ms=None,
                 peer_data_operation_request_message=None,
                 peer_data_operation_request_response_message=None,
                 bot_feedback_message=None,
                 request_welcome_message_metadata=None,
                 media_notify_message=None
                ):
        self._key = key
        self._type = type
        self._initial_security_notification_setting_sync = initial_security_notification_setting_sync
        self._ephemeral_expiration=ephemeral_expiration
        self._ephemeral_setting_timestamp=ephemeral_setting_timestamp
        self._history_sync_notification=history_sync_notification
        self._app_state_sync_key_share=app_state_sync_key_share
        self._app_state_sync_key_request=app_state_sync_key_request
        self._app_state_fatal_exception_notification=app_state_fatal_exception_notification
        self._disappearing_mode=disappearing_mode
        self._edited_message=edited_message
        self._timestamp_ms=timestamp_ms
        self._peer_data_operation_request_message=peer_data_operation_request_message
        self._peer_data_operation_request_response_message=peer_data_operation_request_response_message
        self._bot_feedback_message=bot_feedback_message
        self._request_welcome_message_metadata=request_welcome_message_metadata
        self._media_notify_message=media_notify_message

    def __str__(self):
        print(self.initial_security_notification_setting_sync)
        return "[type=%s, key=%s]" % (self.TYPES[self.type], self.key)

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        assert isinstance(value, MessageKeyAttributes), type(value)
        self._key = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        assert value in self.TYPES, "Unknown type: %s" % value
        self._type = value

    @property
    def initial_security_notification_setting_sync(self):
        return self._initial_security_notification_setting_sync

    @initial_security_notification_setting_sync.setter
    def initial_security_notification_setting_sync(self, value):        
        self._initial_security_notification_setting_sync = value

    @property
    def ephemeral_expiration(self):
        return self._ephemeral_expiration

    @ephemeral_expiration.setter
    def ephemeral_expiration(self, value):        
        self._ephemeral_expirationc = value

    @property
    def history_sync_notification(self):
        return self._history_sync_notification

    @history_sync_notification.setter
    def history_sync_notification(self, value):        
        self._history_sync_notification = value    

    @property
    def app_state_sync_key_share(self):
        return self._app_state_sync_key_share

    @app_state_sync_key_share.setter
    def app_state_sync_key_share(self, value):        
        self._app_state_sync_key_share = value    

    @property
    def app_state_sync_key_request(self):
        return self._app_state_sync_key_request

    @app_state_sync_key_request.setter
    def app_state_sync_key_request(self, value):        
        self._app_state_sync_key_request = value   

    @property
    def app_state_fatal_exception_notification(self):
        return self._app_state_fatal_exception_notification

    @app_state_fatal_exception_notification.setter
    def app_state_fatal_exception_notification(self, value):        
        self._app_state_fatal_exception_notification = value   

    @property
    def disappearing_mode(self):
        return self._disappearing_mode

    @disappearing_mode.setter
    def disappearing_mode(self, value):        
        self._disappearing_mode = value   

    @property
    def edited_message(self):
        return self._edited_message

    @edited_message.setter
    def edited_message(self, value):        
        self._edited_message = value   

    @property
    def timestamp_ms(self):
        return self._timestamp_ms

    @timestamp_ms.setter
    def timestamp_ms(self, value):        
        self._timestamp_ms = value      

    @property
    def peer_data_operation_request_message(self):
        return self._peer_data_operation_request_message

    @peer_data_operation_request_message.setter
    def peer_data_operation_request_message(self, value):        
        self._peer_data_operation_request_message = value  

    @property
    def bot_feedback_message(self):
        return self._bot_feedback_message

    @bot_feedback_message.setter
    def bot_feedback_message(self, value):        
        self._bot_feedback_message = value  

    @property
    def invoker_jid(self):
        return self._invoker_jid

    @invoker_jid.setter
    def invoker_jid(self, value):        
        self._invoker_jid = value  

    @property
    def request_welcome_message_metadata(self):
        return self._request_welcome_message_metadata

    @request_welcome_message_metadata.setter
    def request_welcome_message_metadata(self, value):        
        self._request_welcome_message_metadata = value  

    @property
    def media_notify_message(self):
        return self._media_notify_message

    @media_notify_message.setter
    def media_notify_message(self, value):        
        self._media_notify_message = value                                                                                          



