import time
import os
import requests
from pathlib import Path
from zowsuplib.settings.conf import settings
from .....common.tools import ImageTools
from .....layers.protocol_messages.protocolentities.attributes.attributes_downloadablemedia import DownloadableMediaMessageAttributes

class StickerAttributes(object):
    def __init__(self, downloadablemedia_attributes, width, height, png_thumbnail=None,is_animated=False,sticker_sent_ts=None,is_avatar=False,is_ai_sticker=False,is_lottie=False):
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._width = width
        self._height = height
        self._png_thumbnail = png_thumbnail
        self._is_animated = is_animated
        self._sticker_sent_ts =  int(sticker_sent_ts) if sticker_sent_ts is not None else int(time.time() * 1000) # in milliseconds
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

    @staticmethod
    def from_filepath(filepath, mediaType="sticker", resultRequestMediaConnIqProtocolEntity=None,
                     dimensions=None, png_thumbnail=None, is_animated=False, is_avatar=False, 
                     is_ai_sticker=False, is_lottie=False):
        """
        Cria StickerAttributes a partir de um arquivo local.
        
        Args:
            filepath: Caminho do arquivo do sticker
            mediaType: Tipo de mídia (padrão: "sticker")
            resultRequestMediaConnIqProtocolEntity: Entidade de conexão de mídia
            dimensions: Tupla (width, height) - se None, será detectado automaticamente
            png_thumbnail: Thumbnail PNG (bytes) - se None, será gerado automaticamente
            is_animated: Se o sticker é animado
            is_avatar: Se é um sticker de avatar
            is_ai_sticker: Se é um sticker gerado por IA
            is_lottie: Se é um sticker Lottie
        """
        assert os.path.exists(filepath), f"Arquivo não encontrado: {filepath}"
        
        # Obtém dimensões se não fornecidas
        if not dimensions:
            dimensions = ImageTools.getImageDimensions(filepath)
        
        width, height = dimensions if dimensions else (512, 512)  # Default para stickers
        
        # Gera thumbnail PNG se não fornecido (sticker usa PNG, não JPEG)
        if not png_thumbnail:
            # Para stickers, podemos usar o mesmo método de preview mas converter para PNG
            # Por enquanto, deixamos None e o WhatsApp pode gerar
            png_thumbnail = None
        
        return StickerAttributes(
            DownloadableMediaMessageAttributes.from_file(filepath, mediaType, resultRequestMediaConnIqProtocolEntity),
            width, height, png_thumbnail, is_animated, None, is_avatar, is_ai_sticker, is_lottie
        )

    @staticmethod
    def from_url(url, mediaType="sticker", resultRequestMediaConnIqProtocolEntity=None,
                dimensions=None, png_thumbnail=None, is_animated=False, is_avatar=False,
                is_ai_sticker=False, is_lottie=False):
        """
        Cria StickerAttributes a partir de uma URL.
        
        Args:
            url: URL do sticker
            mediaType: Tipo de mídia (padrão: "sticker")
            resultRequestMediaConnIqProtocolEntity: Entidade de conexão de mídia
            dimensions: Tupla (width, height) - se None, será detectado automaticamente
            png_thumbnail: Thumbnail PNG (bytes) - se None, será gerado automaticamente
            is_animated: Se o sticker é animado
            is_avatar: Se é um sticker de avatar
            is_ai_sticker: Se é um sticker gerado por IA
            is_lottie: Se é um sticker Lottie
        """
        # Baixa o arquivo
        down_res = requests.get(url=url)
        filename = url[url.rfind("/") + 1:] if "/" in url else "sticker.webp"
        if not filename or "." not in filename:
            filename = "sticker.webp"
        
        download_dir = Path(settings.download_path)
        filepath = str(download_dir / filename)
        
        with open(filepath, "wb") as file:
            file.write(down_res.content)
        
        # Usa from_filepath para processar
        return StickerAttributes.from_filepath(
            filepath, mediaType, resultRequestMediaConnIqProtocolEntity,
            dimensions, png_thumbnail, is_animated, is_avatar, is_ai_sticker, is_lottie
        )


