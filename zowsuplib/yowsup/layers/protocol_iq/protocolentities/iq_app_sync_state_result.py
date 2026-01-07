from ....structs import ProtocolEntity, ProtocolTreeNode
from .iq import IqProtocolEntity
from zowsuplib.proto import protocol_pb2
from zowsuplib.yowsup.layers.protocol_appstate.protocolentities.attributes import SyncdPatchAttribute
from loguru import logger

'''
<iq from="s.whatsapp.net" type="result" id="...">
  <sync>
    <collection name="critical_block" version="1" />
  </sync>
</iq>

Ou em caso de erro 409:
<iq from="s.whatsapp.net" type="result" id="...">
  <sync>
    <collection type="error" name="critical_block">
      <error code="409" text="conflict" />
      <patches>
        <patch>...</patch>
      </patches>
    </collection>
  </sync>
</iq>
'''

class AppSyncStateResultIqProtocolEntity(IqProtocolEntity):
    
    def __init__(self, _id=None, collections=None):
        super(AppSyncStateResultIqProtocolEntity, self).__init__(
            "w:sync:app:state", 
            _id=_id, 
            _type="result",
            _from="s.whatsapp.net"
        )
        self.collections = collections or {}  # {collection_name: {"version": int, "error": {...}, "patches": [...]}}
    
    def hasConflict(self, collection_name: str = None) -> bool:
        """Verifica se há conflito (erro 409) em alguma collection ou em uma específica"""
        if collection_name:
            coll = self.collections.get(collection_name, {})
            return coll.get("error", {}).get("code") == "409"
        return any(coll.get("error", {}).get("code") == "409" for coll in self.collections.values())
    
    def getConflictPatches(self, collection_name: str):
        """Retorna os patches de conflito para uma collection específica"""
        coll = self.collections.get(collection_name, {})
        if coll.get("error", {}).get("code") == "409":
            return coll.get("patches", [])
        return []
    
    def getVersion(self, collection_name: str) -> int:
        """Retorna a versão de uma collection"""
        coll = self.collections.get(collection_name, {})
        return coll.get("version", 0)
    
    @staticmethod
    def fromProtocolTreeNode(node):
        entity = IqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = AppSyncStateResultIqProtocolEntity
        
        collections = {}
        sync_node = node.getChild("sync")
        if sync_node:
            collection_nodes = sync_node.getAllChildren("collection")
            for coll_node in collection_nodes:
                coll_name = coll_node.getAttributeValue("name")
                if not coll_name:
                    continue
                
                coll_info = {}
                
                # Verifica se tem versão (sucesso)
                version_attr = coll_node.getAttributeValue("version")
                if version_attr:
                    coll_info["version"] = int(version_attr)
                
                # Verifica se tem erro (conflito)
                error_node = coll_node.getChild("error")
                if error_node:
                    coll_info["error"] = {
                        "code": error_node.getAttributeValue("code"),
                        "text": error_node.getAttributeValue("text")
                    }
                    
                    # Se for erro 409, extrai os patches
                    if error_node.getAttributeValue("code") == "409":
                        patches = []
                        patches_node = coll_node.getChild("patches")
                        if patches_node:
                            patch_nodes = patches_node.getAllChildren("patch")
                            for patch_node in patch_nodes:
                                patch_data = patch_node.getData()
                                if patch_data:
                                    # Parse do patch (pode ser hex string ou bytes)
                                    if isinstance(patch_data, str):
                                        # Remove "0x" se presente e converte hex para bytes
                                        if patch_data.startswith("0x"):
                                            patch_data = patch_data[2:]
                                        try:
                                            patch_bytes = bytes.fromhex(patch_data)
                                        except ValueError:
                                            # Se não for hex válido, tenta como string direta
                                            patch_bytes = patch_data.encode() if isinstance(patch_data, str) else patch_data
                                    else:
                                        patch_bytes = patch_data
                                    
                                    # Tenta decodificar o patch
                                    try:
                                        pb_obj = protocol_pb2.SyncdPatch()
                                        pb_obj.ParseFromString(patch_bytes)
                                        syncd_patch = SyncdPatchAttribute.decodeFrom(pb_obj)
                                        patches.append(syncd_patch)
                                    except Exception as e:
                                        logger.warning(f"Erro ao decodificar patch: {e}")
                                        # Ainda adiciona os bytes brutos para processamento posterior
                                        patches.append(patch_bytes)
                        coll_info["patches"] = patches
                
                collections[coll_name] = coll_info
        
        entity.collections = collections
        return entity

