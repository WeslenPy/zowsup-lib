from zowsuplib.conf.constants import GlobalVar
import zlib
import random
from .decoder import ReadDecoder
from loguru import logger
import json

class WriteEncoder:

    def __init__(self, tokenDictionary):
        self.tokenDictionary = tokenDictionary

    def protocolTreeNodeToBytes(self, node):
        """
        Converte um ProtocolTreeNode para bytes.
        Este é o ponto onde o node está completamente montado e pronto para envio.
        """
        try:
            # Log detalhado do node antes de começar a codificação
            self._log_node_structure(node)
        except Exception as e:
            logger.warning(f"[NODE-ENCODING] Erro ao logar estrutura do node: {e}")
        
        outBytes = [0] # flags
        self.writeInternal(node, outBytes)
        
        try:
            # Log após codificação completa
            self._log_encoding_result(node, outBytes)
        except Exception as e:
            logger.warning(f"[NODE-ENCODING] Erro ao logar resultado da codificação: {e}")
                                
        return outBytes
    
    def _log_node_structure(self, node):
        """Loga a estrutura completa do node antes da codificação"""
        try:
            node_structure = {
                "tag": node.tag,
                "attributes_count": len(node.attributes) if node.attributes else 0,
                "attributes": node.attributes or {},
                "has_data": node.data is not None,
                "data_size": len(node.data) if node.data else 0,
                "children_count": len(node.children) if node.children else 0,
                "children": []
            }
            
            # Adiciona informações de cada filho
            if node.children:
                for idx, child in enumerate(node.children):
                    child_info = {
                        "index": idx,
                        "tag": child.tag,
                        "attributes": child.attributes or {},
                        "has_data": child.data is not None,
                        "data_size": len(child.data) if child.data else 0,
                        "children_count": len(child.children) if child.children else 0
                    }
                    node_structure["children"].append(child_info)
            
            logger.debug(
                f"[NODE-ENCODING] Estrutura do node antes de codificar: "
                f"{json.dumps(node_structure, indent=2, default=str)}"
            )
            
        except Exception as e:
            logger.warning(f"[NODE-ENCODING] Erro ao extrair estrutura do node: {e}")
    
    def _log_encoding_result(self, node, encoded_bytes):
        """Loga o resultado da codificação"""
        try:
            total_bytes = len(encoded_bytes) if encoded_bytes else 0
            logger.debug(
                f"[NODE-ENCODING] Codificação concluída | "
                f"tag={node.tag} total_bytes={total_bytes}"
            )
        except Exception as e:
            logger.warning(f"[NODE-ENCODING] Erro ao logar resultado: {e}")

    def writeInternal(self, node, data):
        """
        Escreve o node internamente de forma recursiva.
        Este método monta cada parte do node (tag, atributos, dados, filhos).
        """
        try:
            # Log do início da codificação deste node
            logger.debug(
                f"[NODE-ENCODING] Codificando node interno | "
                f"tag={node.tag} "
                f"attrs_count={len(node.attributes) if node.attributes else 0} "
                f"has_data={node.data is not None} "
                f"has_children={node.hasChildren()}"
            )
        except:
            pass  # Não falha se houver erro no log
        
        x = 1 + \
        (0 if node.attributes is None else len(node.attributes) * 2) + \
        (0 if not node.hasChildren() else 1) + \
        (0 if node.data is None else 1)

        self.writeListStart(x, data)    

        self.writeString(node.tag, data)
        self.writeAttributes(node.attributes, data)

        if node.data is not None:
            try:
                logger.debug(
                    f"[NODE-ENCODING] Escrevendo dados do node | "
                    f"tag={node.tag} data_size={len(node.data)}"
                )
            except:
                pass
            self.writeBytes(node.data, data)

        if node.hasChildren():
            try:
                logger.debug(
                    f"[NODE-ENCODING] Escrevendo filhos do node | "
                    f"tag={node.tag} children_count={len(node.children)}"
                )
            except:
                pass
            self.writeListStart(len(node.children), data);    
            for c in node.children:
                self.writeInternal(c, data)         

    def writeAttributes(self, attributes, data):
        if attributes is not None:
            for key, value in attributes.items():
                self.writeString(key, data)
                self.writeString(value, data, True)


    def writeBytes(self, bytes_, data, packed = False):
        bytes__ = []
        for b in bytes_:
            if type(b) is int:
                bytes__.append(b)
            else:
                bytes__.append(ord(b))


        size = len(bytes__)
        toWrite = bytes__
        if size >= 0x100000:
            data.append(254)
            self.writeInt31(size, data)
        elif size >= 0x100:
            data.append(253)
            self.writeInt20(size, data)
        else:
            r = None
            if packed:
                if size < 128:
                    r = self.tryPackAndWriteHeader(255, bytes__, data)
                    if r is None:
                        r = self.tryPackAndWriteHeader(251, bytes__, data)

            if r is None:
                data.append(252)
                self.writeInt8(size, data)
            else:
                toWrite = r

        data.extend(toWrite)

    def writeInt8(self, v, data):
        data.append(v & 0xFF)


    def writeInt16(self, v, data):
        data.append((v & 0xFF00) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt20(self, v, data):
        data.append((0xF0000 & v) >> 16)
        data.append((0xFF00 & v) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt24(self, v, data):
        data.append((v & 0xFF0000) >> 16)
        data.append((v & 0xFF00) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt31(self, v, data):
        data.append((0x7F000000 & v) >> 24)
        data.append((0xFF0000 & v) >> 16)
        data.append((0xFF00 & v) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt32(self, v, data):
        data.append((0xFF000000 & v) >> 24)
        data.append((0xFF0000 & v) >> 16)
        data.append((0xFF00 & v) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeListStart(self, i, data):
        if i == 0:
            data.append(0)
        elif i < 256:
            data.append(248)
            self.writeInt8(i, data)
        else:
            data.append(249)
            self.writeInt16(i, data)

    def writeToken(self, token, data):
        if token <= 255 and token >=0:
            data.append(token)
        else:
            raise ValueError("Invalid token: %s" % token)


    def writeString(self, tag, data, packed = False): 

        tok = self.tokenDictionary.getIndex(tag)

                
        if tok:
            index, secondary = tok
            if not secondary:

                self.writeToken(index, data)
            else:
                quotient = index // 256
                if quotient == 0:
                    double_byte_token = 236
                elif quotient == 1:
                    double_byte_token = 237
                elif quotient == 2:
                    double_byte_token = 238
                elif quotient == 3:
                    double_byte_token = 239
                else:
                    raise ValueError("Double byte dictionary token out of range")

                self.writeToken(double_byte_token, data)
                self.writeToken(index % 256, data)
        else:            
            at = '@'.encode() if type(tag) == bytes else '@'
            try:                
                atIndex = tag.index(at)
                if atIndex < 1:
                    raise ValueError("atIndex < 1")
                else:
                    server = tag[atIndex+1:]
                    user = tag[0:atIndex]          
                    self.writeJid(user, server, data)
            except ValueError:
                self.writeBytes(self.encodeString(tag), data, packed)
    

    def encodeString(self, string):
        res = []

        if type(string) == bytes:
            for char in string:
                res.append(char)
        else:
            for char in string:
                res.append(ord(char))
        return res

    def writeJid(self, user, server, data):
        if user.find(":") != -1:
            if server=="lid":
                device_no = user.split("@")[0].split(":")[1]
                data.append(247)
                data.append(1)
                data.append(int(device_no))                                
                user = user.split(":")[0]                                   
                self.writeString(user,data,True)            
            else:
                device_no = user.split("@")[0].split(":")[1]
                data.append(247)
                data.append(0)
                data.append(int(device_no))                
                user = user.split(".")[0]
                self.writeString(user,data,True)
        else:
            if server=="lid":                
                data.append(247)
                data.append(1)
                data.append(0)                     
                user = user.split("@")[0]
                self.writeString(user,data,True)
            else:
                data.append(250)
                if user is not None:
                    self.writeString(user, data,True)
                else:
                    self.writeToken(0, data)
                self.writeString(server, data)

            
    def tryPackAndWriteHeader(self, v, headerData, data):
        size = len(headerData)
        if size >= 128:
            return None
        arr = [0] * int((size + 1) / 2)
        for i in range(0, size):
            packByte = self.packByte(v, headerData[i])
            if packByte == -1:
                arr = []
                break
            n2 = int(i / 2)
            arr[n2] |= (packByte << 4 * (1 - i % 2))

        if len(arr) > 0:
            if size % 2 == 1:
                arr[-1] |= 15 #0xF
            data.append(v)
            self.writeInt8(size %2 << 7 | len(arr), data)
            return arr
        return None
    
    def packByte(self, v, n2):
        if v == 251:
            return self.packHex(n2)
        if v == 255:
            return self.packNibble(n2)
        return -1

    def packHex(self, n):
        if n in range(48, 58):
            return n - 48
        if n in range(65, 71):
            return 10 + (n - 65)
        return -1

    def packNibble(self, n):
        if n in (45, 46):
            return 10 + (n - 45)

        if n in range(48, 58):
            return n - 48

        return -1


