class TemplateAttributes(object):
    def __init__(self, text, buttons = None):
        
        self._text = text
        self._buttons = buttons        

    def __str__(self):
        attrs = []        
        if self.text is not None:
            attrs.append(("text", self.text))
        if self.buttons is not None:
            attrs.append(("buttons", self.buttons))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def buttons(self):
        return self._buttons

    @buttons.setter
    def buttons(self, value):
        self._buttons = value


