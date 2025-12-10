class AppStateSyncKeyDataAttribute(object):
    def __init__(self, key_data,fingerprint,timestamp):
        self._key_data = key_data
        self._fingerprint = fingerprint
        self._timestamp=timestamp

    @property
    def key_data(self):
        return self._key_data

    @key_data.setter
    def key_data(self, value):
        self._key_data = value       


    @property
    def fingerprint(self):
        return self._fingerprint

    @fingerprint.setter
    def fingerprint(self, value):
        self._fingerprint = value    
        

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value            





