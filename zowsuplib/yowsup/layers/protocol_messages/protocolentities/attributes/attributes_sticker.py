import time
class StickerAttributes(object):
    def __init__(self, downloadablemedia_attributes, width, height, png_thumbnail=None,is_animated=False,sticker_sent_ts=None,is_avatar=False,is_ai_sticker=False,is_lottie=False):
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._width = width
        self._height = height
        self._png_thumbnail = png_thumbnail
        self._is_animated = is_animated
        self._sticker_sent_ts =  sticker_sent_ts if sticker_sent_ts is not None else time.time() * 1000 # in milliseconds
        self._is_avatar =  is_avatar
        self._is_ai_sticker = is_ai_sticker
        self._is_lottie = is_lottie


    def __str__(self):
        attrs = []
        if self.width is not None:
            attrs.append(("width", self.width))
        if self.height is not None:
            attrs.append(("height", self.height))
        if self.png_thumbnail is not None:
            attrs.append(("png_thumbnail", self.png_thumbnail))
        if self.is_animated is not None:
            attrs.append(("is_animated", self.is_animated))
        if self.is_avatar is not None:
            attrs.append(("is_avatar", self.is_avatar))
        if self.is_ai_sticker is not None:
            attrs.append(("is_ai_sticker", self.is_ai_sticker))
        if self.is_lottie is not None:
            attrs.append(("is_lottie", self.is_lottie))
        if self.sticker_sent_ts is not None:
            attrs.append(("sticker_sent_ts", self.sticker_sent_ts))
                            
        attrs.append(("downloadable", self.downloadablemedia_attributes))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def downloadablemedia_attributes(self):
        return self._downloadablemedia_attributes

    @downloadablemedia_attributes.setter
    def downloadablemedia_attributes(self, value):
        self._downloadablemedia_attributes = value

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def png_thumbnail(self):
        return self._png_thumbnail

    @png_thumbnail.setter
    def png_thumbnail(self, value):
        self._png_thumbnail = value


    @property
    def is_avatar(self):
        return self._is_avatar

    @is_avatar.setter
    def is_avatar(self, value):
        self._is_avatar = value

    @property
    def is_animated(self):
        return self._is_animated

    @is_animated.setter
    def is_animated(self, value):
        self._is_animated = value     


    @property
    def is_ai_sticker(self):
        return self._is_ai_sticker

    @is_ai_sticker.setter
    def is_ai_sticker(self, value):
        self._is_ai_sticker = value          


    @property
    def is_lottie(self):
        return self._is_lottie

    @is_lottie.setter
    def is_lottie(self, value):
        self._is_lottie = value                      


    @property
    def sticker_sent_ts(self):
        return self._sticker_sent_ts

    @sticker_sent_ts.setter
    def sticker_sent_ts(self, value):
        self._sticker_sent_ts = value         


