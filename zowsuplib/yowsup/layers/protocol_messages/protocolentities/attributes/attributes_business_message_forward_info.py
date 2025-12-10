class BusinessMessageForwardInfoAttributes(object):
    def __init__(self,
                 business_owner_jid=None,
                ):
    
        self._business_owner_jid = business_owner_jid

    @property
    def business_owner_jid(self):
        return self._business_owner_jid

    @business_owner_jid.setter
    def business_owner_jid(self, value):
        self._business_owner_jid = value       

    

