class ProductAttributes(object):

    def __init__(self, product_image, product_id, title,description,business_owner_jid,context_info=None):
        self._product_image = product_image
        self._product_id = product_id
        self._title = title
        self._description = description
        self._business_owner_jid=business_owner_jid        
        self._context_info = context_info

    def __str__(self):
        attrs = []
        if self._product_image is not None:
            attrs.append(("product_image", self.product_image))
        if self._product_id is not None:
            attrs.append(("product_id", self.product_id))
        if self._title is not None:
            attrs.append(("title", self.title))   
        if self._description is not None:
            attrs.append(("description", self.description))   

        if self._business_owner_jid is not None:
            attrs.append(("business_owner_jid", self.business_owner_jid))              

        if self._context_info is not None:
            attrs.append(("context_info", self._context_info))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def product_image(self):
        return self._product_image

    @product_image.setter
    def product_image(self, value):
        self._product_image = value

    @property
    def product_id(self):
        return self._product_id

    @product_id.setter
    def product_id(self, value):
        self._product_id = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value


    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def business_owner_jid(self):
        return self._business_owner_jid

    @business_owner_jid.setter
    def business_owner_jid(self, value):
        self._business_owner_jid = value

