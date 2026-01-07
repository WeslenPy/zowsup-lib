import os
from pathlib import Path
from .constants import YowConstants
import codecs, sys
import tempfile
import base64
import hashlib
import os.path, mimetypes
import uuid
import random
from zowsuplib.consonance.structs.keypair import KeyPair
import re
from loguru import logger
from zowsuplib.settings.conf import settings
import requests
from urllib.parse import urlparse

from .optionalmodules import PILOptionalModule, FFMpegOptionalModule

class Jid:
    @staticmethod
    def normalize(tos):
        #这里的参数修改为逗号分隔的号码, 用于支持多个收件人

        numbers = tos.split(",")
        ret = []
        for number in numbers:
            if '@' in number:
                ret.append(number)                
                continue
            elif "-" in number or ("." not in number and ":" not in number and len(number) >= 15):
                ret.append("%s@%s" % (number, YowConstants.WHATSAPP_GROUP_SERVER))            
                continue
                        
            ret.append("%s@%s" % (number, YowConstants.WHATSAPP_SERVER))

        #返回的也是处理过的逗号分隔账号信息
        return ','.join(ret)
        

class HexTools:
    decode_hex = codecs.getdecoder("hex_codec")
    @staticmethod
    def decodeHex(hexString):
        result = HexTools.decode_hex(hexString)[0]
        if sys.version_info >= (3,0):
            result = result.decode('latin-1')
        return result

class WATools:

    @staticmethod
    def fullJid(jid):
       jid = Jid.normalize(jid) 
       s = jid.split("@")[1]
       i,t,d = WATools.jidDecode(jid)
       return "%s.%d:%d@%s" % (i,t,d,s)
    
    @staticmethod
    def jidDecode(jid):
        username = jid.split("@")[0]
        nps = re.split(':|\\.',username)
        recipientId = nps[0]

        if len(recipientId) < 14:
            recipientType = int(nps[1]) if len(nps)>=2 else 0
        else:
            recipientType = 1

        deviceId = int(nps[2]) if len(nps)>=3 else 0
        return [recipientId,recipientType,deviceId] 

    @staticmethod
    def generateIdentity():
        return os.urandom(20)

    @classmethod
    def generatePhoneId(cls,env):
        """
        :return:
        :rtype: str
        """                
        if env.deviceEnv.getOSName() in ["iOS","SMB iOS"]:
            return str(cls.generateUUID()).upper()
        else:
            return str(cls.generateUUID())
    
    @classmethod
    def generateDeviceId(cls):
        """
        :return:
        :rtype: bytes
        """        
        return cls.generateUUID().bytes

    @classmethod
    def generateUUID(cls):
        """
        :return:
        :rtype: uuid.UUID
        """
        return uuid.uuid4()

    @classmethod
    def generateKeyPair(cls):
        """
        :return:
        :rtype: KeyPair
        """
        return KeyPair.generate()

    @staticmethod
    def getFileHashForUpload(filePath):
        sha1 = hashlib.sha256()
        f = open(filePath, 'rb')
        try:
            sha1.update(f.read())
        finally:
            f.close()
        b64Hash = base64.b64encode(sha1.digest())
        return b64Hash if type(b64Hash) is str else b64Hash.decode()

    @staticmethod
    def getDataHashForUpload(data):
        sha1 = hashlib.sha256()
        sha1.update(data)
        b64Hash = base64.b64encode(sha1.digest())
        return b64Hash if type(b64Hash) is str else b64Hash.decode()        

class StorageTools:
    NAME_CONFIG = "config.json"

    @staticmethod
    def _extract_phone_from_profile_name(profile_name):
        """
        Attempts to extract the phone / account identifier from a profile_name.

        Common patterns in this project:
          - ACCOUNT_PATH + phone
          - ACCOUNT_PATH + phone + "_" + deviceid
        We normalize to the last path component and take the leading digits.
        """
        base = os.path.basename(str(profile_name))
        # Strip optional "_deviceId" suffix
        if "_" in base:
            base = base.split("_", 1)[0]
        # Match a leading sequence of at least 5 digits (the phone number)
        m = re.match(r"(\d{5,})", base)
        return m.group(1) if m else None

    @staticmethod
    def constructPath(*path):
        path = os.path.join(*path)
        base = str(settings.account_path)
        fullPath = os.path.join(base, path)  #如果path不是绝对路径，那就增加ACCOUNT_PATH前缀
        if not os.path.exists(os.path.dirname(fullPath)):
            os.makedirs(os.path.dirname(fullPath))
        return fullPath

    @staticmethod
    def getStorageForProfile(profile_name):
        if type(profile_name) is not str:
            profile_name = str(profile_name)
        return StorageTools.constructPath(profile_name)

    @staticmethod
    def writeProfileData(profile_name, name, val):
        logger.debug(f"writeProfileData(profile_name={profile_name}, name={name}, val=[omitted])")
        path = os.path.join(StorageTools.getStorageForProfile(profile_name), name)
        logger.debug(f"Writing {path}")

        with open(path, 'w' if type(val) is str else 'wb') as attrFile:
            attrFile.write(val)

    @staticmethod
    def readProfileData(profile_name, name, default=None):
        logger.debug(f"readProfileData(profile_name={profile_name}, name={name})")
        path = StorageTools.getStorageForProfile(profile_name)
        dataFilePath = os.path.join(path, name)
        if os.path.isfile(dataFilePath):
            logger.debug(f"Reading {dataFilePath}")
            with open(dataFilePath, 'rb') as attrFile:
                return attrFile.read()
        else:
            logger.debug(f"{dataFilePath} does not exist")

        return default

    @classmethod
    def writeProfileConfig(cls, profile_name, config):

        """
        Writes profile config exclusively to the unified database (ProfileConfig).

        No config.json or per-account directories are used anymore. The
        profile_name is expected to start with the phone number (or
        phone_deviceid), so we can link it to an Account row.
        """
        phone = cls._extract_phone_from_profile_name(profile_name)

        if not phone:
            logger.error(f"Cannot infer phone from profile_name={profile_name}; config will not be persisted")
            return

        # Lazy import to avoid circular dependencies at module import time
        try:
            from zowsuplib.app.db import SessionLocal
            from zowsuplib.app import models
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error persisting profile config to DB: {e}")
            raise

        db = SessionLocal()
        try:
            account_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
            if account_id is None:
                account = models.Account(phone=phone)
                db.add(account)
                db.flush()
                account_id = account.id

            row = (
                db.query(models.ProfileConfig)
                .filter_by(account_id=account_id, name=cls.NAME_CONFIG)
                .one_or_none()
            )

            data = config.encode() if isinstance(config, str) else config

            if row is None:
                row = models.ProfileConfig(
                    account_id=account_id,
                    name=cls.NAME_CONFIG,
                    data=data,
                )
                db.add(row)
            else:
                row.data = data

            db.commit()
            logger.debug(f"ProfileConfig stored in DB for phone={phone}")
        finally:
            db.close()

    @classmethod
    def readProfileConfig(cls, profile_name, config):
        """
        Reads profile config exclusively from the unified database (ProfileConfig).

        If no matching Account/ProfileConfig is found, returns None. No
        file-based config.json lookup is performed.
        """
        phone = cls._extract_phone_from_profile_name(profile_name)

        if not phone:
            logger.error(f"Cannot infer phone from profile_name={profile_name}; no config available")
            return None

        try:
            from zowsuplib.app.db import SessionLocal
            from zowsuplib.app import models
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error loading profile config from DB: {e}")
            raise

        db = SessionLocal()
        try:
            account_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
            if not account_id:
                return None

            row = (
                db.query(models.ProfileConfig)
                .filter_by(account_id=account_id, name=cls.NAME_CONFIG)
                .one_or_none()
            )
            if row is None:
                return None

            return row.data
        finally:
            db.close()


class ImageTools:
    @staticmethod
    def scaleImage(infile, outfile, imageFormat, width, height):
        with PILOptionalModule() as imp:
            Image = imp("Image")
            im = Image.open(infile)
            #Convert P mode images
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((width, height))
            im.save(outfile, imageFormat)
            return True
        return False

    @staticmethod
    def getImageDimensions(imageFile):
        with PILOptionalModule() as imp:
            Image = imp("Image")
            im = Image.open(imageFile)
            return im.size

    @staticmethod
    def generatePreviewFromImage(image):
        fd, path = tempfile.mkstemp()
        preview = None
        if ImageTools.scaleImage(image, path, "JPEG", YowConstants.PREVIEW_WIDTH, YowConstants.PREVIEW_HEIGHT):
            fileObj = os.fdopen(fd, "rb+")
            fileObj.seek(0)
            preview = fileObj.read()
            fileObj.close()
        os.remove(path)
        return preview

class MimeTools:
    MIME_FILE = os.path.join(os.path.dirname(__file__), 'mime.types')
    mimetypes.init() # Load default mime.types
    try:
        mimetypes.init([MIME_FILE]) # Append whatsapp mime.types
    except Exception as e:
        logger.warning("Mime types supported can't be read. System mimes will be used. Cause: " +str(e))

    # Mapeamento manual para tipos MIME não reconhecidos automaticamente
    _MANUAL_MIME_TYPES = {
        '.webp': 'image/webp',
        '.webm': 'video/webm',
        '.was': 'application/was',  # WhatsApp Audio Sticker
    }

    @staticmethod
    def getMIME(filepath):
        # Tenta primeiro com mimetypes padrão
        mimeType = mimetypes.guess_type(filepath)[0]
        
        # Se não encontrou, tenta mapeamento manual por extensão
        if mimeType is None:
            filepath_lower = filepath.lower()
            for ext, mime in MimeTools._MANUAL_MIME_TYPES.items():
                if filepath_lower.endswith(ext):
                    mimeType = mime
                    break
        
        # Se ainda não encontrou, tenta adicionar ao mimetypes dinamicamente
        if mimeType is None:
            # Extrai extensão do arquivo
            ext = os.path.splitext(filepath)[1].lower()
            if ext:
                # Adiciona tipos comuns de stickers/imagens
                if ext == '.webp':
                    mimetypes.add_type('image/webp', ext)
                    mimeType = 'image/webp'
                elif ext == '.webm':
                    mimetypes.add_type('video/webm', ext)
                    mimeType = 'video/webm'
        
        if mimeType is None:
            raise Exception("Unsupported/unrecognized file type for: "+filepath);
        return mimeType


class AudioTools:
    @staticmethod
    def getAudioProperties(audioFile):
        """
        Obtém propriedades do áudio (duração em segundos).
        Em caso de erro, retorna valor aleatório genérico entre 1-60 segundos.
        """
        try:
            with FFMpegOptionalModule() as imp:
                ffmpeg = imp()
                probe = ffmpeg.probe(audioFile)
                audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
                if audio_stream and 'duration' in audio_stream:
                    duration = int(float(audio_stream['duration']))
                    return duration
        except Exception as e:
            logger.warning(f"Erro ao obter propriedades do áudio {audioFile}: {e}. Usando valor fallback.")
        
        # Fallback: duração aleatória entre 1-60 segundos (típico para mensagens de áudio)
        fallback_duration = random.randint(1, 60)
        logger.debug(f"Usando duração fallback: {fallback_duration}s")
        return fallback_duration

class VideoTools:
    @staticmethod
    def getVideoProperties(videoFile):
        """
        Obtém propriedades do vídeo (width, height, bitrate, duration, codec_name).
        Em caso de erro, retorna valores genéricos/aleatórios.
        """
        try:
            with FFMpegOptionalModule() as imp:
                ffmpeg = imp()            
                probe = ffmpeg.probe(videoFile)
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                if video_stream:
                    width = int(video_stream.get('width', 640))
                    height = int(video_stream.get('height', 480))
                    bitrate = int(video_stream.get('bit_rate', 1000000))
                    duration = int(float(video_stream.get('duration', 10)))
                    codec_name = video_stream.get('codec_name', 'h264')
                    return width, height, bitrate, duration, codec_name
        except Exception as e:
            logger.warning(f"Erro ao obter propriedades do vídeo {videoFile}: {e}. Usando valores fallback.")
        
        # Fallback: valores genéricos/aleatórios
        # Resoluções comuns: 640x480, 1280x720, 1920x1080
        resolutions = [(640, 480), (1280, 720), (1920, 1080), (854, 480), (1280, 960)]
        width, height = random.choice(resolutions)
        # Bitrate típico: 500k-5M
        bitrate = random.randint(500000, 5000000)
        # Duração típica: 5-120 segundos
        duration = random.randint(5, 120)
        # Codec comum
        codec_name = random.choice(['h264', 'h265', 'vp8', 'vp9', 'mpeg4'])
        
        logger.debug(f"Usando valores fallback: {width}x{height}, bitrate={bitrate}, duration={duration}s, codec={codec_name}")
        return width, height, bitrate, duration, codec_name

    @staticmethod
    def generatePreviewFromVideo(videoFile):
        """
        Gera preview (thumbnail) do vídeo.
        Em caso de erro, retorna None ou preview genérico.
        """
        try:
            with FFMpegOptionalModule() as imp:
                ffmpeg = imp()
                # Usa tempfile para compatibilidade multiplataforma
                temp_dir = tempfile.gettempdir()
                path = os.path.join(temp_dir, str(uuid.uuid4()) + ".jpg")
                
                try:
                    ffmpeg.input(videoFile, ss=0).filter("scale", 100, -1).output(path, vframes=1).run(quiet=True, overwrite_output=True)
                    preview = ImageTools.generatePreviewFromImage(path)
                    if os.path.exists(path):
                        os.remove(path)
                    return preview
                except Exception as e:
                    logger.warning(f"Erro ao gerar preview do vídeo {videoFile}: {e}")
                    if os.path.exists(path):
                        os.remove(path)
        except Exception as e:
            logger.warning(f"Erro ao inicializar FFMpeg para preview do vídeo {videoFile}: {e}. Usando fallback.")
        
        # Fallback: retorna None (sem preview) ou pode tentar gerar preview genérico
        # Por enquanto, retorna None para indicar que não foi possível gerar preview
        logger.debug("Usando fallback: preview não disponível")
        return None


class DownloadTools:
    """
    Ferramentas auxiliares para download seguro de arquivos de URLs.
    """
    
    @staticmethod
    def download_file_from_url(url: str, default_extension: str = None, prefix: str = "download") -> str:
        """
        Faz download de um arquivo de uma URL e salva em um diretório seguro.
        
        Args:
            url: URL do arquivo a ser baixado
            default_extension: Extensão padrão se não conseguir detectar da URL (ex: ".ogg", ".mp4")
            prefix: Prefixo para o nome do arquivo se não conseguir extrair da URL
        
        Returns:
            Caminho completo do arquivo baixado
        
        Raises:
            Exception: Se houver erro ao baixar ou salvar o arquivo
        """
        try:
            # Faz o download do arquivo
            down_res = requests.get(url, timeout=30)
            down_res.raise_for_status()
            
            # Extrai o filename da URL de forma segura
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            
            # Tenta extrair o filename do path da URL
            if url_path:
                # Remove a barra inicial se existir
                url_path = url_path.lstrip('/')
                # Pega a última parte do path (filename)
                filename = os.path.basename(url_path) if url_path else None
            else:
                filename = None
            
            # Se não conseguiu extrair um filename válido da URL, gera um baseado no hash
            if not filename or len(filename) == 0 or len(filename) > 200:
                # Gera um hash da URL para criar um filename único
                url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]
                ext = default_extension or ".tmp"
                filename = f"{prefix}_{url_hash}{ext}"
            else:
                # Sanitiza o filename: remove caracteres inválidos e limita tamanho
                # Remove caracteres inválidos para Windows/Linux
                invalid_chars = '<>:"|?*\\'
                for char in invalid_chars:
                    filename = filename.replace(char, '_')
                
                # Limita o tamanho do filename (Windows tem limite de 255 caracteres)
                if len(filename) > 200:
                    name, ext = os.path.splitext(filename)
                    filename = name[:190] + (ext or default_extension or "")
                
                # Se não tiver extensão e foi fornecida uma padrão, adiciona
                if default_extension and not os.path.splitext(filename)[1]:
                    filename += default_extension
            
            # Determina o diretório de download
            # Tenta usar o diretório configurado, mas se não existir ou não tiver permissão, usa temp
            download_dir = None
            try:
                download_dir = Path(settings.download_path)
                # Cria o diretório se não existir
                download_dir.mkdir(parents=True, exist_ok=True)
                # Testa se tem permissão de escrita
                test_file = download_dir / ".test_write"
                try:
                    test_file.touch()
                    test_file.unlink()
                except (PermissionError, OSError):
                    # Sem permissão, usa temp
                    download_dir = None
            except (PermissionError, OSError, Exception) as e:
                logger.warning(f"Não foi possível usar diretório de download configurado: {e}, usando diretório temporário")
                download_dir = None
            
            # Se não conseguiu usar o diretório configurado, usa temp
            if download_dir is None:
                download_dir = Path(tempfile.gettempdir()) / "zowsuplib_downloads"
                download_dir.mkdir(parents=True, exist_ok=True)
            
            # Monta o caminho completo do arquivo
            filepath = download_dir / filename
            
            # Se o arquivo já existir, adiciona um sufixo numérico
            counter = 1
            original_filepath = filepath
            while filepath.exists():
                name, ext = os.path.splitext(original_filepath)
                filepath = Path(f"{name}_{counter}{ext}")
                counter += 1
                if counter > 1000:  # Limite de segurança
                    raise Exception("Muitos arquivos com o mesmo nome no diretório")
            
            # Salva o arquivo
            filepath_str = str(filepath)
            with open(filepath_str, "wb") as file:
                file.write(down_res.content)
            
            logger.debug(f"Arquivo baixado de URL e salvo em: {filepath_str}")
            return filepath_str
            
        except requests.RequestException as e:
            logger.error(f"Erro ao baixar arquivo da URL {url}: {e}")
            raise Exception(f"Erro ao baixar arquivo: {str(e)}")
        except (PermissionError, OSError) as e:
            logger.error(f"Erro de permissão ao salvar arquivo: {e}")
            raise Exception(f"Erro de permissão ao salvar arquivo: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar arquivo da URL {url}: {e}", exc_info=True)
            raise



