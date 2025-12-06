from ...config.base import config
from loguru import logger


class Config(config.Config):
    def __init__(
            self,
            phone=None,
            cc=None,
            login=None,
            pushname=None,
            id=None,
            mcc=None,
            mnc=None,
            sim_mcc=None,
            sim_mnc=None,
            client_static_keypair=None,
            server_static_public=None,
            expid=None,
            fdid=None,
            edge_routing_info=None,
            chat_dns_domain=None,
            device=None,
            device_identity=None,
            device_list=None,        

            platform=None,
            os_name = None,
            os_version=None,
            manufacturer=None,
            device_name=None,   
            device_model_type=None,
            c2dm_reg_id=None,
            fcm_creds=None,
            fcm_cat=None         
    ):
        super(Config, self).__init__(1)

        self._phone = str(phone) if phone is not None else None  # type: str
        self._cc = cc  # type: int
        self._login = str(login) if login is not None else None # type: str
        self._pushname = pushname  # type: str
        self._id = id
        self._client_static_keypair = client_static_keypair
        self._server_static_public = server_static_public
        self._expid = expid
        self._fdid = fdid
        self._mcc = mcc
        self._mnc = mnc
        self._sim_mcc = sim_mcc
        self._sim_mnc = sim_mnc
        self._edge_routing_info = edge_routing_info
        self._chat_dns_domain = chat_dns_domain
        self._device = device        
        self._device_identity = device_identity
        self._device_list = device_list

        self._platform = platform
        self._os_name = os_name
        self._os_version=os_version
        self._manufacturer=manufacturer
        self._device_name=device_name
        self._device_model_type = device_model_type

        self._c2dm_reg_id = c2dm_reg_id
        self._fcm_creds = fcm_creds
        self._fcm_cat = fcm_cat

    def __str__(self):
        from ...config.v1.serialize import ConfigSerialize
        from ...config.transforms.dict_json import DictJsonTransform
        return DictJsonTransform().transform(ConfigSerialize(self.__class__).serialize(self))

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, value):
        self._phone = str(value) if value is not None else None

    @property
    def cc(self):
        return self._cc

    @cc.setter
    def cc(self, value):
        self._cc = value

    @property
    def login(self):
        return self._login

    @login.setter
    def login(self, value):
        self._login= value

    @property
    def pushname(self):
        return self._pushname

    @pushname.setter
    def pushname(self, value):
        self._pushname = value

    @property
    def mcc(self):
        return self._mcc

    @mcc.setter
    def mcc(self, value):
        self._mcc = value

    @property
    def mnc(self):
        return self._mnc

    @mnc.setter
    def mnc(self, value):
        self._mnc = value

    @property
    def sim_mcc(self):
        return self._sim_mcc

    @sim_mcc.setter
    def sim_mcc(self, value):
        self._sim_mcc = value

    @property
    def sim_mnc(self):
        return self._sim_mnc

    @sim_mnc.setter
    def sim_mnc(self, value):
        self._sim_mnc = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def client_static_keypair(self):
        return self._client_static_keypair

    @client_static_keypair.setter
    def client_static_keypair(self, value):
        self._client_static_keypair = value

    @property
    def server_static_public(self):
        return self._server_static_public

    @server_static_public.setter
    def server_static_public(self, value):
        self._server_static_public = value

    @property
    def expid(self):
        return self._expid

    @expid.setter
    def expid(self, value):
        self._expid = value

    @property
    def fdid(self):
        return self._fdid

    @fdid.setter
    def fdid(self, value):
        self._fdid = value

    @property
    def edge_routing_info(self):
        return self._edge_routing_info

    @edge_routing_info.setter
    def edge_routing_info(self, value):
        self._edge_routing_info = value

    @property
    def chat_dns_domain(self):
        return self._chat_dns_domain

    @chat_dns_domain.setter
    def chat_dns_domain(self, value):
        self._chat_dns_domain = value

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, value):
        self._device = value        

    @property
    def device_identity(self):
        return self._device_identity

    @device_identity.setter
    def device_identity(self, value):
        self._device_identity = value          

    @property
    def device_list(self):
        return self._device_list

    @device_list.setter
    def device_list(self, value):
        self._device_list = value          


    def get_new_device_index(self):
        if  self._device_list is None:
            new_id =1
        else:
            new_id = max(self._device_list)+1       
        return new_id 
    
    def add_device_to_list(self,value):        
        if self._device_list is None:
            self._device_list = []        
        self._device_list.append(value)        
        return self._device_list
        
    @property
    def platform(self):
        return self._platform

    @platform.setter
    def platform(self, value):
        self._platform = value   

    @property
    def os_name(self):
        return self._os_name

    @os_name.setter
    def os_name(self, value):
        self._os_name = value  

    @property
    def os_version(self):
        return self._os_version

    @os_version.setter
    def os_version(self, value):
        self._os_version = value   

    @property
    def manufacturer(self):
        return self._manufacturer

    @manufacturer.setter
    def manufacturer(self, value):
        self._manufacturer = value   

    @property
    def device_name(self):
        return self._device_name

    @device_name.setter
    def device_name(self, value):
        self._device_name = value   

    @property
    def device_model_type(self):
        return self._device_model_type

    @device_model_type.setter
    def device_model_type(self, value):
        self._device_model_type = value   

    @property
    def os_build_number(self):
        return self._os_build_number

    @os_build_number.setter
    def os_build_number(self, value):
        self._os_build_number = value   

    @property
    def c2dm_reg_id(self):
        return self._c2dm_reg_id

    @c2dm_reg_id.setter
    def c2dm_reg_id(self,value):
        self._c2dm_reg_id = value

    @property
    def fcm_creds(self):
        return self._fcm_creds

    @fcm_creds.setter
    def fcm_creds(self,value):
        self._fcm_creds = value

    @property
    def fcm_cat(self):
        return self._fcm_cat

    @fcm_cat.setter
    def fcm_cat(self,value):
        self._fcm_cat = value