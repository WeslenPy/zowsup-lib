class AppStateSyncKeyShareAttribute(object):
    def __init__(self, keys):
        self._keys = keys

    @property
    def keys(self):
        return self._keys

    @keys.setter
    def keys(self, value):
        self._keys = value




