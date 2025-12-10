class PollCreationAttributes(object):
    def __init__(self, name, options = None, multi = False,message_secret=None,context_info=None):
        
        self._name = name
        self._options = options        
        self._multi = multi
        self._context_info = context_info        
        self._message_secret = message_secret

    def __str__(self):
        attrs = []        
        if self.name is not None:
            attrs.append(("name", self.name))
        if self.options is not None:
            attrs.append(("options", self.options))
        if self.multi is not None:
            attrs.append(("multi", self.multi))       
        if self.message_secret is not None:
            attrs.append(("message_secret", self.message_secret))                     

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = value


    @property
    def multi(self):
        return self._multi

    @multi.setter
    def multi(self, value):
        self._multi = value

    @property
    def context_info(self):
        return self._context_info

    @context_info.setter
    def context_info(self, value):
        self._context_info = value       


    @property
    def message_secret(self):
        return self._message_secret

    @message_secret.setter
    def message_secret(self, value):
        self._message_secret = value           


