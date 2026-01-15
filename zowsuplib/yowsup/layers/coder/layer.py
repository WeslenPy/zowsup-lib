from ...layers import YowLayer
from .encoder import WriteEncoder
from .decoder import ReadDecoder
from .tokendictionary import TokenDictionary
import zlib
from loguru import logger
import json


class YowCoderLayer(YowLayer):

    def __init__(self):
        YowLayer.__init__(self)
        tokenDictionary = TokenDictionary()
        self.writer = WriteEncoder(tokenDictionary)
        self.reader = ReadDecoder(tokenDictionary)
    
    def send(self, data):                
        # Log do node completo antes de converter para bytes
        self._log_node_before_encoding(data)
        
        out = self.writer.protocolTreeNodeToBytes(data)    
        
        # Log dos bytes resultantes
        self._log_encoded_bytes(out)
        
        self.write(out)
    
    def _log_node_before_encoding(self, node):
        """Loga o node completo antes de ser codificado para bytes"""
        try:
            account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
            
            # Extrai informações do node
            node_info = {
                "tag": node.tag,
                "attributes": node.attributes or {},
                "has_data": node.data is not None,
                "data_length": len(node.data) if node.data else 0,
                "data_preview": node.data[:64].hex() if node.data and len(node.data) > 0 else None,
                "children_count": len(node.children) if node.children else 0,
                "children_tags": [child.tag for child in node.children] if node.children else []
            }
            
            # Log estruturado
            logger.info(
                f"[NODE-ENCODING] Node montado completamente antes de enviar | "
                f"account={account_id} tag={node.tag} "
                f"attrs={json.dumps(node_info['attributes'])} "
                f"children={node_info['children_count']} "
                f"data_len={node_info['data_length']}"
            )
            
            # Log detalhado do node completo (formato XML-like)
            logger.debug(
                f"[NODE-ENCODING] Node completo antes de codificar:\n{str(node)}"
            )
            
            # Log de cada filho se houver
            if node.children:
                for idx, child in enumerate(node.children):
                    child_info = {
                        "index": idx,
                        "tag": child.tag,
                        "attributes": child.attributes or {},
                        "has_data": child.data is not None,
                        "data_length": len(child.data) if child.data else 0
                    }
                    logger.debug(
                        f"[NODE-ENCODING] Child {idx}: tag={child.tag} "
                        f"attrs={json.dumps(child_info['attributes'])} "
                        f"data_len={child_info['data_length']}"
                    )
                    
        except Exception as e:
            logger.warning(f"[NODE-ENCODING] Erro ao logar node antes de codificar: {e}")
    
    def _log_encoded_bytes(self, encoded_bytes):
        """Loga os bytes resultantes após codificação"""
        try:
            account_id = self.getStack().getProp("botId") or self.getStack().getProp("jid") or "unknown"
            bytes_length = len(encoded_bytes) if encoded_bytes else 0
            bytes_preview = encoded_bytes[:64] if encoded_bytes and len(encoded_bytes) > 0 else []
            bytes_preview_hex = "".join(f"{b:02x}" for b in bytes_preview) if bytes_preview else "empty"
            
            logger.info(
                f"[NODE-ENCODING] Node codificado para bytes | "
                f"account={account_id} bytes_length={bytes_length} "
                f"preview_hex={bytes_preview_hex}..."
            )
            
            # Log completo dos bytes (apenas em debug)
            if encoded_bytes:
                full_hex = "".join(f"{b:02x}" for b in encoded_bytes)
                logger.debug(
                    f"[NODE-ENCODING] Bytes completos (hex): {full_hex}"
                )
                
        except Exception as e:
            logger.warning(f"[NODE-ENCODING] Erro ao logar bytes codificados: {e}")

    def receive(self, data):                
        node = self.reader.getProtocolTreeNode(bytearray(data))        
        if node:
            self.toUpper(node)

    def write(self, i):
        if(type(i) in(list, tuple,bytearray)):
            self.toLower(bytearray(i))
        else:
            self.toLower(bytearray([i]))

    def __str__(self):
        return "Coder Layer"


