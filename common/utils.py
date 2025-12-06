# coding=UTF-8
import sys,os
from pathlib import Path
from conf.constants import SysVar,GlobalVar

import re
import json
import urllib
import random
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hmac
from math import ceil
from Crypto.Util.Padding import pad,unpad
import struct
from app.device_env import DeviceEnv
from proto import wa_struct_pb2
from axolotl.ecc.curve import Curve
import zlib

import base64,time
from loguru import logger

class Utils:

    _OUTPUT = []

    @staticmethod
    def generateMultiDeviceParams(ref,companion_auth_pub,companion_identity_pub,adv_secret,profile):

        p1 = wa_struct_pb2.ADVDeviceIdentity()
        p1.raw_id = random.randint(1500000000,1700000000)
        p1.key_index = profile.config.get_new_device_index()      #自动按照最大的index+1
        p1.timestamp = int(time.time())

        db = profile.axolotl_manager

        p2 = wa_struct_pb2.ADVSignedDeviceIdentity()
        p2.details = p1.SerializeToString()
        p2.account_signature_key = db.identity.publicKey.serialize()[1:]
        p2.account_signature = Curve.calculateSignature(db.identity.privateKey,b"\x06\x00"+p2.details+companion_identity_pub)

        p3 = wa_struct_pb2.ADVSignedDeviceIdentityHMAC()
        p3.details = p2.SerializeToString()
        p3.hmac = hmac.new(key=adv_secret, msg=p3.details, digestmod=hashlib.sha256).digest()

        q1 = wa_struct_pb2.ADVKeyIndexList()
        q1.raw_id = p1.raw_id
        q1.timestamp = p1.timestamp
        if profile.config.device_list:
            q1.valid_indexes.extend(profile.config.device_list)

        q2 = wa_struct_pb2.ADVSignedKeyIndexList()
        q2.details = q1.SerializeToString()
        q2.account_signature = Curve.calculateSignature(db.identity.privateKey,b"\x06\x02"+p2.details)

        return ref,companion_auth_pub,p3.SerializeToString(),q2.SerializeToString()    
    
    def generateMultiDeviceParamsFromQrCode(qr_str,profile):

        qr_parts = qr_str.split(",")  #四个部份
        ref = qr_parts[0].encode()
        companion_auth_pub = base64.b64decode(qr_parts[1])
        companion_identity_pub = base64.b64decode(qr_parts[2])
        adv_secret = base64.b64decode(qr_parts[3])
        print(len(adv_secret))

        return Utils.generateMultiDeviceParams(ref,companion_auth_pub,companion_identity_pub,adv_secret,profile)    

    def link_code_encrypt(link_code_key,data):
        try:
            salt = get_random_bytes(32)
            random_iv = get_random_bytes(16)
            key = hashlib.pbkdf2_hmac(
                hash_name='sha256',
                password=link_code_key.encode(),
                salt=salt,
                iterations=131072,
                dklen=32,
            )                      
            cipher = AES.new(key, AES.MODE_CTR,initial_value=random_iv,nonce=b'')            
            ciphered = cipher.encrypt(data)
            return salt + random_iv + ciphered
        except Exception as e:
            raise RuntimeError("Cannot encrypt") from e
        
    
        
    def link_code_decrypt(link_code_key,encrypted_data):
        try:
            salt = encrypted_data[:32]
            key = hashlib.pbkdf2_hmac(
                hash_name='sha256',
                password=link_code_key.encode(),
                salt=salt,
                iterations=131072,
                dklen=32,
            )          
            iv = encrypted_data[32:48]
            payload = encrypted_data[48:80]            
            cipher = AES.new(key, AES.MODE_CTR,initial_value=iv,nonce=b'')          
            return cipher.decrypt(payload)            
        except Exception as e:
            raise RuntimeError("Cannot decrypt") from e
            #pass    

    def compress(uncompressed: bytes) -> bytes:
        compressor = zlib.compressobj()
        compressed_data = compressor.compress(uncompressed)
        compressed_data += compressor.flush()
        return compressed_data

    def decompress(compressed: bytes) -> bytes:
        # 解压缩数据
        decompressor = zlib.decompressobj()
        decompressed_data = decompressor.decompress(compressed)
        decompressed_data += decompressor.flush()
        return decompressed_data          
    
    def extract_and_expand(key: bytes, info: bytes = b"", output_length: int = 32,salt=None) -> bytes:         
        return Utils.expand(hmac.new(salt if salt is not None else bytes(32) , key, hashlib.sha256).digest(), info, output_length)
    
    def expand(prk: bytes, info: bytes, output_size: int) -> bytes:
        HASH_OUTPUT_SIZE = 32  # SHA-256 produces a 32-byte output                
        iterations = ceil(output_size / HASH_OUTPUT_SIZE)
        mixin = b""
        results = bytearray()
        
        for index in range(1, iterations + 1):
            mac = hmac.new(prk, mixin, hashlib.sha256)
            if info:
                mac.update(info)
            mac.update(bytes([index]))
            step_result = mac.digest()
            step_size = min(output_size, len(step_result))
            results.extend(step_result[:step_size])
            mixin = step_result
            output_size -= step_size
        
        return bytes(results)
    
    
    def encryptAndPrefix(buffer,key):                
        iv = get_random_bytes(AES.block_size)              
        cipher = AES.new(key, AES.MODE_CBC,iv= iv)           
        buffer_padded = pad(buffer, AES.block_size)
        ciphered = cipher.encrypt(buffer_padded)    
        return iv+ciphered    
    
    @staticmethod
    def generateMac(opbyte,data,keyId,key):        
        keyData = opbyte+keyId
        last = struct.pack(">Q",len(keyData))                
        total = keyData+data+last        
        mac = hmac.new(key, total, hashlib.sha512).digest()                
        return mac[0:32]
    
    def generateSnapshotMac(ltHash,version,patchType,key):
        total = ltHash+struct.pack(">Q", version)+patchType.encode()
        mac = hmac.new(key, total, hashlib.sha256).digest()
        return mac
    

    def generatePatchMac(snapShotMac,valueMacs,version,patchType,key):
        total = snapShotMac
        for item in valueMacs:
            total+=item
        total+=struct.pack(">Q", version)+patchType.encode()
        mac = hmac.new(key, total, hashlib.sha256).digest()
        return mac        



        
    def assureDir(path):                
        if not os.path.exists(path):
            os.makedirs(path)

    def getOption(options,name,default=None):
        if name in options:
            return options[name]
        else:
            return default
            
    def getTypesByEnvName(name):
        #regType,osType
        if name == "smb_android":
            return 2,1
        if name == "smb_ios":
            return 2,2
        if name == "android":
            return 1,1
        if name== "ios":
            return 1,2
            
        return 0,0
    
    def cmdLineParser(args):
        options = {}
        params = []
        if len(args)==1:
            return params,options 
        i = 1
        while i<len(args):
            if args[i].startswith("--"):                
                if i+1>=len(args) or args[i+1].startswith("--") :
                    options[args[i][2:]] = True
                    i+=1
                else:
                    options[args[i][2:]] = args[i+1]
                    i+=2
            else:
                params.append(args[i])
                i+=1
        return params,options

    def init_log(level: str = "INFO", name: str | None = None):
        """
        Inicializa o sistema de logs usando loguru, com saída em stdout e arquivo.

        - level: nível mínimo de log (ex.: "DEBUG", "INFO", "WARNING")
        - name: nome do arquivo de log dentro de SysVar.LOG_PATH (default: "default.log")
        """

        from loguru import logger as _logger

        if name is None:
            name = "default.log"

        log_dir = Path(SysVar.LOG_PATH)
        Utils.assureDir(log_dir)

        # Remove handlers existentes para evitar duplicação
        _logger.remove()

        # Console
        _logger.add(
            sys.stdout,
            level="DEBUG",
            # format="{time:YYYY-MM-DD HH:mm:ss,SSS} {level} {name}: {message}",
        )

        # Arquivo
        _logger.add(
            name,
            level=level,
            encoding="utf-8",
            rotation="50 MB",
            retention="7 days",
        )
        
    def genMccMncList():

        td_re = re.compile('<td>(.*)</td>')
        
        with urllib.request.urlopen('http://mcc-mnc.com/') as f:
            html = f.read().decode('utf-8')

        tbody_start = False
        mcc_mnc_list = []

        i=0
        for line in html.split('\n'):        
            if '<tbody>' in line:
                tbody_start = True
                logger.info("start")
            elif '</tbody>' in line:
                break
            elif tbody_start:
                td_search = td_re.search(line)     

                if td_search is None:
                    continue       
                                        
                if i==0:
                    current_item = {}
                    current_item['mcc'] = td_search[1]
                    i+=1
                    continue
                if i==1:
                    current_item['mnc'] = td_search[1]
                    i+=1
                    continue
                if i==2:
                    current_item['iso'] = td_search[1]
                    i+=1
                    continue            
                if i==3:
                    current_item['country'] = td_search[1]
                    i+=1
                    continue            
                if i==4:
                    current_item['countryCode'] = td_search[1]
                    i+=1
                    continue            
                if i==5:
                    current_item['network'] = td_search[1]
                    mcc_mnc_list.append(current_item)
                    i=0
                    continue      
        with open("mcc_mnc.json", 'w', encoding='utf8') as f2:
            f2.write(json.dumps(mcc_mnc_list, indent=2))           
        
    def getMccMnc(countryCode):
        """
        Retorna um par mcc/mnc plausível para o código de país informado.

        A fonte é o arquivo data/mcc_mnc.json (pré-gerado). Caso não haja
        entradas para o countryCode, retorna "000"/"000".
        """
        try:
            with open("data/mcc_mnc.json", 'r', encoding='utf8') as f:
                items = json.loads(f.read())
        except Exception as e:
            logger.error(f"Erro ao carregar data/mcc_mnc.json: {e}")
            return {"mcc": "000", "mnc": "000"}

        candidates = [
            item for item in items
            if item.get("countryCode") == countryCode
               and item.get("mcc")
               and item.get("mnc")
        ]

        if not candidates:
            return {"mcc": "000", "mnc": "000"}

        choice = random.choice(candidates)
        return {"mcc": choice["mcc"], "mnc": choice["mnc"]}

    def getMobileCC(mobile):
        with open("data/mcc_mnc.json", 'r', encoding='utf8') as f:            
            list =json.loads(f.read())
        map = {}
        for item in list:
            if item["countryCode"]!="":
                map[item["countryCode"]] = 1
        
        for k in map:
            if mobile.startswith(k):                                                
                return k


    def getLGLC(countryCode):        

        for item in GlobalVar.COUNTRYCODE:
            if item[1] == countryCode:
                return item[3],item[4]

        logger.info("LGLC not Found, set US as default")
        return "en","US"        


    def exit(code):                
        sys.exit(code)
    
    def getDeviceEnvByInfo(info):

        if info is not None and "regType" in info:
            if "osType" not in info:
                info["osType"]=2

            if info["regType"]==1:
                if info["osType"]==1:
                    return DeviceEnv("android",random=True)
                if info["osType"]==2:
                    return DeviceEnv("ios",random=True)                
            else:
                if info["osType"]==1:
                    return DeviceEnv("smb_android",random=True)
                if info["osType"]==2:
                    return DeviceEnv("smb_ios",random=True)        
                

          

            
    
    
    


        
        




