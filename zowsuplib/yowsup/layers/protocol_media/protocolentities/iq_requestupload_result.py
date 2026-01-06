from ....common import YowConstants
from ....layers.protocol_iq.protocolentities import ResultIqProtocolEntity
from ....structs import ProtocolTreeNode
import base64
import urllib.parse
class ResultRequestUploadIqProtocolEntity(ResultIqProtocolEntity):
    def __init__(self, _id, url, ip = None, resumeOffset = 0, duplicate = False):
        super(ResultRequestUploadIqProtocolEntity, self).__init__(_id = _id, _from = "s.whatsapp.net")
        self.setUploadProps(url, ip, resumeOffset, duplicate)

    def setUploadProps(self, url ,ip = None, resumeOffset = 0, duplicate = False):
        self.url = url
        self.ip = ip
        self.resumeOffset = resumeOffset or 0
        self.duplicate = duplicate

    def isDuplicate(self):
        return self.duplicate

    def getUrl(self):
        return self.url

    def getResumeOffset(self):
        return self.resumeOffset

    def getIp(self):
        return self.ip
    
    def getAuth(self):
        """Retorna o token de autenticação do media_conn (novo formato)."""
        return getattr(self, 'auth', None)
    
    def getHosts(self):
        """Retorna lista de hosts disponíveis do media_conn (novo formato)."""
        return getattr(self, 'hosts', [])
    
    def getUploadHost(self):
        """Retorna o primeiro host com suporte a upload (novo formato)."""
        hosts = self.getHosts()
        return hosts[0] if hosts else None
    
    def buildUploadUrl(self, media_type, file_hash, upload_prefix="mms", newsletter=False):
        """
        Constrói a URL completa de upload no novo formato (padrão whatsmeow).
        
        Args:
            media_type: Tipo de mídia ("image", "video", "audio", "document", "ptt")
            file_hash: Hash SHA256 do arquivo (bytes)
            upload_prefix: Prefixo do upload ("mms", "wa-msgr/mms", ou "newsletter")
            newsletter: Se True, usa prefixo "newsletter"
        
        Returns:
            URL completa de upload ou None se não tiver informações necessárias
        """
        # Se não tem auth, provavelmente é formato antigo - retorna URL direta
        auth = self.getAuth()
        if not auth:
            return self.getUrl()
        
        # Mapeia tipo de mídia para mmsType
        mms_type_map = {
            "image": "image",
            "video": "video",
            "audio": "audio",
            "document": "document",
            "ptt": "ptt",
        }
        
        mms_type = mms_type_map.get(media_type, media_type)
        
        # Ajusta para newsletter se necessário
        if newsletter:
            mms_type = f"newsletter-{mms_type}"
            upload_prefix = "newsletter"
        elif upload_prefix == "wa-msgr/mms" and mms_type == "audio":
            # Messenger upload só permite voice messages, não audio files
            mms_type = "ptt"
        
        # Converte hash para base64 URL encoding (sem padding)
        if isinstance(file_hash, bytes):
            token = base64.urlsafe_b64encode(file_hash).decode('utf-8').rstrip('=')
        else:
            # Se já é string, assume que já está em base64
            token = str(file_hash).replace('+', '-').replace('/', '_').rstrip('=')
        
        # Obtém host (primeiro host com upload ou primeiro disponível)
        host = self.getUploadHost()
        if not host:
            hosts = self.getHosts()
            if hosts:
                host = hosts[0]
            else:
                return None
        
        # Constrói URL no formato: https://{host}/{uploadPrefix}/{mmsType}/{token}?auth={auth}&token={token}
        query_params = urllib.parse.urlencode({
            "auth": auth,
            "token": token
        })
        
        url = f"https://{host}/{upload_prefix}/{mms_type}/{token}?{query_params}"
        return url

    def __str__(self):
        out = super(ResultRequestUploadIqProtocolEntity, self).__str__()
        # Defensivo: verifica se url existe antes de acessar
        url = getattr(self, 'url', 'N/A')
        out += "URL: %s\n" % url
        if hasattr(self, 'ip') and self.ip:
            out += "IP: %s\n" % self.ip
        
        # Informações adicionais do novo formato media_conn
        if hasattr(self, 'auth') and self.auth:
            out += "Auth: %s\n" % self.auth
        if hasattr(self, 'ttl') and self.ttl:
            out += "TTL: %s\n" % self.ttl
        if hasattr(self, 'hosts') and self.hosts:
            out += "Hosts: %s\n" % ", ".join(self.hosts[:3])  # Mostra apenas os 3 primeiros
        if hasattr(self, 'ip_token') and self.ip_token:
            out += "IP Token: %s\n" % self.ip_token[:20] + "..."  # Mostra apenas parte do token
        
        return out

    def toProtocolTreeNode(self):
        node = super(ResultRequestUploadIqProtocolEntity, self).toProtocolTreeNode()

        if not self.isDuplicate():
            mediaNode = ProtocolTreeNode("encr_media", {"url": self.url})
            if self.ip:
                mediaNode["ip"] = self.ip

            if self.resumeOffset:
                mediaNode["resume"] = str(self.resumeOffset)
        else:
            mediaNode = ProtocolTreeNode("duplicate", {"url": self.url})

        node.addChild(mediaNode)
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity= ResultIqProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = ResultRequestUploadIqProtocolEntity
        
        # Formato antigo: encr_media ou duplicate
        mediaNode = node.getChild("encr_media")
        if mediaNode:
            url = mediaNode.getAttributeValue("url") or ""
            ip = mediaNode.getAttributeValue("ip")
            resume = mediaNode.getAttributeValue("resume")
            resumeOffset = int(resume) if resume else 0
            entity.setUploadProps(url, ip, resumeOffset)
            return entity
        
        duplicateNode = node.getChild("duplicate")
        if duplicateNode:
            url = duplicateNode.getAttributeValue("url") or ""
            ip = duplicateNode.getAttributeValue("ip")
            entity.setUploadProps(url, ip, duplicate = True)
            return entity
        
        # Novo formato: media_conn com hosts
        mediaConnNode = node.getChild("media_conn")
        if mediaConnNode:
            # Extrai informações do media_conn
            auth = mediaConnNode.getAttributeValue("auth")
            ttl = mediaConnNode.getAttributeValue("ttl")
            auth_ttl = mediaConnNode.getAttributeValue("auth_ttl")
            max_buckets = mediaConnNode.getAttributeValue("max_buckets")
            ip_token = mediaConnNode.getAttributeValue("ip_token")
            
            # Procura o primeiro host com <upload /> para usar como URL/IP
            hosts = mediaConnNode.getAllChildren("host")
            url = None
            ip = None
            
            for host in hosts:
                uploadNode = host.getChild("upload")
                if uploadNode:
                    # Usa o primeiro host com upload
                    hostname = host.getAttributeValue("hostname")
                    ip4 = host.getAttributeValue("ip4")
                    ip6 = host.getAttributeValue("ip6")
                    
                    # Constrói URL usando hostname (ou IP como fallback)
                    if hostname:
                        url = f"https://{hostname}"
                    elif ip4:
                        url = f"https://{ip4}"
                    
                    # Prefere IPv4, fallback para IPv6
                    ip = ip4 or ip6
                    break
            
            # Se não encontrou host com upload, usa o primeiro host disponível
            if not url and hosts:
                first_host = hosts[0]
                hostname = first_host.getAttributeValue("hostname")
                ip4 = first_host.getAttributeValue("ip4")
                if hostname:
                    url = f"https://{hostname}"
                elif ip4:
                    url = f"https://{ip4}"
                ip = ip4 or first_host.getAttributeValue("ip6")
            
            # Armazena informações adicionais do media_conn como atributos
            entity.auth = auth
            entity.ttl = int(ttl) if ttl else 0
            entity.auth_ttl = int(auth_ttl) if auth_ttl else 0
            entity.max_buckets = int(max_buckets) if max_buckets else 0
            entity.ip_token = ip_token
            
            # Armazena lista de hostnames (filtra None)
            entity.hosts = []
            for h in hosts:
                hostname = h.getAttributeValue("hostname")
                if hostname:
                    entity.hosts.append(hostname)
            
            # Armazena informações detalhadas de cada host (opcional, para uso futuro)
            entity.host_details = []
            for h in hosts:
                host_info = {
                    "hostname": h.getAttributeValue("hostname"),
                    "type": h.getAttributeValue("type"),
                    "ip4": h.getAttributeValue("ip4"),
                    "ip6": h.getAttributeValue("ip6"),
                    "fallback_hostname": h.getAttributeValue("fallback_hostname"),
                    "fallback_ip4": h.getAttributeValue("fallback_ip4"),
                    "fallback_ip6": h.getAttributeValue("fallback_ip6"),
                    "has_upload": h.getChild("upload") is not None,
                }
                entity.host_details.append(host_info)
            
            # Inicializa com URL/IP encontrados (ou valores padrão)
            entity.setUploadProps(url or "", ip, 0, False)
            return entity
        
        # Fallback: inicializa com valores padrão se nenhum nó for encontrado
        # Isso evita AttributeError quando __str__ é chamado
        entity.setUploadProps("", None, 0, False)
        return entity


