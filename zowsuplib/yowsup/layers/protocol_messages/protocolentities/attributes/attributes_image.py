from .....common.tools import ImageTools, DownloadTools
from .....layers.protocol_messages.protocolentities.attributes.attributes_downloadablemedia \
    import DownloadableMediaMessageAttributes
import os
import requests
from pathlib import Path
from zowsuplib.settings.conf import settings
from loguru import logger


class ImageAttributes(object):
    def __init__(self, downloadablemedia_attributes, width, height, caption=None, jpeg_thumbnail=None):
        self._downloadablemedia_attributes = downloadablemedia_attributes  # type: DownloadableMediaMessageAttributes
        self._width = width
        self._height = height
        self._caption = caption
        self._jpeg_thumbnail = jpeg_thumbnail        

    def __str__(self):
        attrs = []
        if self.width is not None:
            attrs.append(("width", self.width))
        if self.height is not None:
            attrs.append(("height", self.height))
        if self.caption is not None:
            attrs.append(("caption", self.caption))
        if self.jpeg_thumbnail is not None:
            attrs.append(("jpeg_thumbnail", "[binary data]"))
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
    def caption(self):
        return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = value if value else ''

    @property
    def jpeg_thumbnail(self):
        return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, value):
        self._jpeg_thumbnail = value if value else b''

    @staticmethod
    def from_filepath(filepath,mediaType=None,resultRequestMediaConnIqProtocolEntity=None, 
        dimensions=None, caption=None, jpeg_thumbnail=None):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo de imagem não encontrado: {filepath}")
        if not jpeg_thumbnail:
            jpeg_thumbnail = ImageTools.generatePreviewFromImage(filepath)
        dimensions = dimensions or ImageTools.getImageDimensions(filepath)
        width, height = dimensions if dimensions else (None, None)
        if not width or not height:
            raise ValueError("Could not determine image dimensions, install pillow or pass dimensions")

        return ImageAttributes(
            DownloadableMediaMessageAttributes.from_file(filepath,mediaType,resultRequestMediaConnIqProtocolEntity), width, height, caption, jpeg_thumbnail
        )

    @staticmethod
    def from_url(url,mediaType=None,resultRequestMediaConnIqProtocolEntity=None, 
        dimensions=None, caption=None, jpeg_thumbnail=None):

        # Usa a função auxiliar para download seguro
        filepath = DownloadTools.download_file_from_url(url, default_extension=".jpg", prefix="image")

        if not jpeg_thumbnail:
            jpeg_thumbnail = ImageTools.generatePreviewFromImage(filepath)
        dimensions = dimensions or ImageTools.getImageDimensions(filepath)
        width, height = dimensions if dimensions else (None, None)
        if not width or not height:
            raise ValueError("Could not determine image dimensions, install pillow or pass dimensions")

        return ImageAttributes(
            DownloadableMediaMessageAttributes.from_file(filepath,mediaType,resultRequestMediaConnIqProtocolEntity), width, height, caption, jpeg_thumbnail
        )        


