class AppStateSyncKeyFingerprintAttribute(object):
    def __init__(self, raw_id,current_index,device_indexes):
        self._raw_id = raw_id
        self._current_index = current_index
        self._device_indexes=device_indexes

    @property
    def raw_id(self):
        return self._raw_id

    @raw_id.setter
    def raw_id(self, value):
        self._raw_id = value       


    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        self._current_index = value    
        

    @property
    def device_indexes(self):
        return self._device_indexes

    @device_indexes.setter
    def device_indexes(self, value):
        self._device_indexes = value            





