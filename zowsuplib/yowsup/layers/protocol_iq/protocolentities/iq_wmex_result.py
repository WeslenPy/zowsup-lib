from ....structs import  ProtocolTreeNode
from .iq import IqProtocolEntity
from ....common import YowConstants
from zowsuplib.proto import wa_struct_pb2
import json,base64
import zipfile
import tempfile
from pathlib import Path
from zargo.utils.jid import Jid
from zargo.argo_message_decoder import ArgoMessageDecoder
from zowsuplib.common.utils import PathStatic
from loguru import logger

class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            if obj[0]==250 or obj[0]==247:
                return Jid.readJid(obj)
            else:
                return base64.b64encode(obj).decode('utf-8') 
        return json.JSONEncoder.default(self, obj)
    

class WmexResultIqProtocolEntity(IqProtocolEntity):

    idNameMap = {}
    _unzipped_schema_cache = None  # Cache para o caminho do arquivo descompactado
    '''

    <iq from="s.whatsapp.net" type="result" id="3979800857">
    <result>
        JSON-FORMATTED RESULT
    </result>
    </iq>  
    '''

    def __init__(self,_id,result_obj=None,result_type="json"):
        super(WmexResultIqProtocolEntity, self).__init__(_id = _id, _type = "result", _from = YowConstants.DOMAIN)
        self.result_obj = result_obj
        self.result_type = result_type

    def setResultObj(self, result_obj,result_type):
        self.result_obj = result_obj
        self.result_type = result_type

    def __str__(self):
        out = super(WmexResultIqProtocolEntity, self).__str__()
        out += "result_obj: %s\n" % (json.dumps(self.result_obj) if self.result_type=="json" else str(self.result_obj))
        return out

    @staticmethod
    def _get_unzipped_schema_file():
        """
        Descompacta o arquivo argo-wire-type-store.zip e retorna o caminho
        do arquivo .argo descompactado. Usa cache para evitar descompactar
        múltiplas vezes.
        """
        if WmexResultIqProtocolEntity._unzipped_schema_cache is not None:
            cached_path = Path(WmexResultIqProtocolEntity._unzipped_schema_cache)
            if cached_path.exists():
                return str(cached_path.resolve())
        
        # Obtém o caminho do arquivo zip
        zip_path = PathStatic.data_file("argo-wire-type-store.zip")
        zip_file_path = Path(zip_path)
        
        if not zip_file_path.exists():
            raise FileNotFoundError(
                f"Arquivo argo-wire-type-store.zip não encontrado em: {zip_path}"
            )
        
        # Cria diretório temporário para descompactar
        temp_dir = Path(tempfile.gettempdir()) / "zowsuplib_data"
        temp_dir.mkdir(exist_ok=True)
        extracted_file = temp_dir / "argo-wire-type-store.argo"
        
        # Descompacta apenas se o arquivo não existir ou se o zip for mais recente
        if not extracted_file.exists() or zip_file_path.stat().st_mtime > extracted_file.stat().st_mtime:
            try:
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    # Extrai o arquivo .argo do zip
                    zip_ref.extract("argo-wire-type-store.argo", temp_dir)
                logger.debug(f"Arquivo argo-wire-type-store.argo descompactado para: {extracted_file}")
            except zipfile.BadZipFile:
                raise ValueError(f"Arquivo zip corrompido: {zip_path}")
            except KeyError:
                raise ValueError(f"Arquivo argo-wire-type-store.argo não encontrado dentro do zip: {zip_path}")
        
        # Armazena no cache
        WmexResultIqProtocolEntity._unzipped_schema_cache = str(extracted_file.resolve())
        return WmexResultIqProtocolEntity._unzipped_schema_cache

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = IqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = WmexResultIqProtocolEntity
        result = node.getChild("result")                
        if result is not None:      
            format = result.getAttributeValue("format")                    
            if format=="argo":               
                data = result.getData()                                                                         
                id = node.getAttributeValue("id")
                query_name =  WmexResultIqProtocolEntity.idNameMap.pop(id)                
                if query_name is not None:
                    # Descompacta o zip e obtém o caminho do arquivo .argo
                    schema_file = WmexResultIqProtocolEntity._get_unzipped_schema_file()
                    ArgoMessageDecoder.setSchemaFile(schema_file)
                    obj = ArgoMessageDecoder.decodeMessage(query_name,data)                    
                    res = json.dumps(obj,cls=BytesEncoder)                   
                                    
                    entity.setResultObj(json.loads(res),"json")
                else:
                    entity.setResultObj(data,"argo") 
            else:
                jsonstr = str(result.getData(),"utf-8")
                entity.setResultObj(json.loads(jsonstr),"json")
            return entity
        else:            
            return None
        