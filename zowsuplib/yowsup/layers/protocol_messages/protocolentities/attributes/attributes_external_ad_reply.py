class ExternalAdReplyAttributes(object):
    def __init__(self,
                 title=None,
                 body=None,
                 media_type=None,
                 thumbnail_url=None,
                 media_url=None,
                 thumbnail=None,
                 source_type=None,
                 source_id=None,
                 source_url=None,
                 contains_auto_reply=None,
                 render_larger_thumbnail=None,
                 show_ad_attribution=None
                ):
        
        self._title = title
        self._body = body
        self._media_type = media_type
        self._thumbnail_url = thumbnail_url
        self._media_url = media_url
        self._thumbnail = thumbnail
        self._source_type = source_type
        self._source_id = source_id
        self._source_url=source_url
        self._contains_auto_reply = contains_auto_reply
        self._render_larger_thumbnail = render_larger_thumbnail
        self._show_ad_attribution = show_ad_attribution


    def __str__(self):
        attribs = []
        if self._title is not None:
            attribs.append(("title", self.title))
        if self._body is not None:
            attribs.append(("body", self.body))
        if self._media_type is not None:
            attribs.append(("media_type", self.media_type))
        if self._thumbnail_url is not None:
            attribs.append(("thumbnail_url", self.thumbnail_url))
        if self._media_url is not None:
            attribs.append(("media_url", self.media_url))
        if self._thumbnail is not None:
            attribs.append(("thumbnail", "[omitted]"))
        if self._source_type is not None:
            attribs.append(("source_type", self.source_type))  

        if self._source_id is not None:
            attribs.append(("source_id", self.source_id))
        if self._source_url is not None:
            attribs.append(("source_url", self.source_url))      
        if self._contains_auto_reply is not None:
            attribs.append(("contains_auto_reply", str(self.contains_auto_reply)))      

        if self._render_larger_thumbnail is not None:
            attribs.append(("render_larger_thumbnail",str(self.render_larger_thumbnail)))

        if self._show_ad_attribution is not None:
            attribs.append(("show_ad_attribution",str(self.show_ad_attribution)))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attribs)))        


    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value       

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value    

    @property
    def media_type(self):
        return self._media_type

    @media_type.setter
    def media_type(self, value):
        self._media_type = value            

    @property
    def thumbnail_url(self):
        return self._thumbnail_url

    @thumbnail_url.setter
    def thumbnail_url(self, value):
        self._thumbnail_url = value          

    @property
    def media_url(self):
        return self._media_url

    @media_url.setter
    def media_url(self, value):
        self._media_url = value  
        

    @property
    def thumbnail(self):
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, value):
        self._thumbnail = value

    @property
    def source_type(self):
        return self._source_type

    @source_type.setter
    def source_type(self, value):
        self._source_type = value

    @property
    def source_id(self):
        return self._source_id

    @source_id.setter
    def source_id(self, value):
        self._source_id = value


    @property
    def source_url(self):
        return self._source_url

    @source_url.setter
    def source_url(self, value):
        self._source_url = value        

    @property
    def contains_auto_reply(self):
        return self._contains_auto_reply

    @contains_auto_reply.setter
    def contains_auto_reply(self, value):
        self._contains_auto_reply = value

    @property
    def render_larger_thumbnail(self):
        return self._render_larger_thumbnail

    @render_larger_thumbnail.setter
    def render_larger_thumbnail(self, value):
        self._render_larger_thumbnail = value

    @property
    def show_ad_attribution(self):
        return self._show_ad_attribution

    @show_ad_attribution.setter
    def show_ad_attribution(self, value):
        self._show_ad_attribution = value



