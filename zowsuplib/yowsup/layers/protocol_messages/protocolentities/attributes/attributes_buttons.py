class ButtonsAttributes(object):
    def __init__(self, buttons, content, footer,context_info=None):
        self._buttons = buttons
        self._content = content
        self._footer = footer        
        self._context_info = context_info

    def __str__(self):
        attrs = []
        if self._buttons is not None:
            attrs.append(("buttons", self.buttons))
        if self.content is not None:
            attrs.append(("content", self.content))
        if self.footer is not None:
            attrs.append(("footer", self.footer))            
                                    
        if self._context_info is not None:
            attrs.append(("context_info", self._context_info))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def buttons(self):
        return self._buttons

    @buttons.setter
    def buttons(self, value):
        self._buttons = value

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @property
    def footer(self):
        return self._footer

    @footer.setter
    def footer(self, value):
        self._footer = value

