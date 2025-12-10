class AppStateSyncKeyIdAttribute(object):
    def __init__(self, key_id):
        self._key_id = key_id


    @property
    def key_id(self):
        return self._key_id

    @key_id.setter
    def key_id(self, value):
        self._keys_id = value




