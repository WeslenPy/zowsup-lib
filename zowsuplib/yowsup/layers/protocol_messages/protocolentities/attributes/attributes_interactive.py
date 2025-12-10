class InteractiveAttributes(object):
    def __init__(self, body, header=None,  footer=None, buttons=None):
        
        self._body = body
        self._header = header
        self._footer = footer
        self._buttons = buttons   

    @property
    def body(self):
        return self._body

    @body.setter
    def text(self, value):
        self._body = value

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, value):
        self._header = value


    @property
    def footer(self):
        return self._footer

    @footer.setter
    def footer(self, value):
        self._footer = value

    @property
    def buttons(self):
        return self._buttons

    @buttons.setter
    def buttons(self, value):
        self._buttons = value

