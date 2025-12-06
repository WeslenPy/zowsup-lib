from loguru import logger


class ExtendedTextAttributes(object):
    def __init__(
            self,
            text, matched_text=None, canonical_url=None, description=None, title=None, jpeg_thumbnail=None, context_info=None,
            text_argb = None,background_argb=None,font=None,preview_type = None,invite_link_group_type_v2=None,doNotPlayInline=None        
    ):
        self._text = text
        self._matched_text = matched_text
        self._canonical_url = canonical_url
        self._description = description
        self._title = title
        self._jpeg_thumbnail = jpeg_thumbnail
        self._context_info = context_info

        self._text_argb = text_argb
        self._background_argb = background_argb
        self._font = font
        self._preview_type = preview_type
        self._invite_link_group_type_v2 = invite_link_group_type_v2
        self._doNotPlayInline=doNotPlayInline



        logger.info(f"ExtendedTextAttributes: {self}")



    def __str__(self):
        attrs = []
        if self.text is not None:
            attrs.append(("text", self.text))
        if self.matched_text is not None:
            attrs.append(("matched_text", self.matched_text))
        if self.canonical_url is not None:
            attrs.append(("canonical_url", self.canonical_url))
        if self.description is not None:
            attrs.append(("description", self.description))
        if self.title is not None:
            attrs.append(("title", self.title))
        if self.jpeg_thumbnail is not None:
            attrs.append(("jpeg_thumbnail", "[binary data]"))
        if self.context_info is not None:
            attrs.append(("context_info", self.context_info))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def doNotPlayInline(self):
        return self._doNotPlayInline

    @doNotPlayInline.setter
    def doNotPlayInline(self, value):
        self._doNotPlayInline = value        

    @property
    def matched_text(self):
        return self._matched_text

    @matched_text.setter
    def matched_text(self, value):
        self._matched_text = value

    @property
    def canonical_url(self):
        return self._canonical_url

    @canonical_url.setter
    def canonical_url(self, value):
        self._canonical_url = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def jpeg_thumbnail(self):
        return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value):
        self._jpeg_thumbnail = value

    @property
    def text_argb(self):
        return self._text_argb

    @text_argb.setter
    def text_argb(self, value):
        self._text_argb = value        

    @property
    def background_argb(self):
        return self._background_argb

    @background_argb.setter
    def background_argb(self, value):
        self._background_argb = value           

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value        

    @property
    def preview_type(self):
        return self._preview_type

    @preview_type.setter
    def preview_type(self, value):
        self._preview_type = value      

    @property
    def invite_link_group_type_v2(self):
        return self._invite_link_group_type_v2

    @invite_link_group_type_v2.setter
    def invite_link_group_type_v2(self, value):
        self._invite_link_group_type_v2 = value                           

    @property
    def context_info(self):
        return self._context_info

    @context_info.setter
    def context_info(self, value):
        self._context_info = value
