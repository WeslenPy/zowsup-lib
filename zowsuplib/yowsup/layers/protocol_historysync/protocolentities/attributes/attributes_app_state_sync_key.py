class AppStateSyncKeyAttribute(object):
    def __init__(self, key_id,key_data):
        self._key_id = key_id
        self._key_data = key_data

    @property
    def key_id(self):
        return self._key_id

    @key_id.setter
    def key_id(self, value):
        self._keys_id = value

    @property
    def key_data(self):
        return self._key_data

    @key_data.setter
    def key_data(self, value):
        self._key_data = value        




