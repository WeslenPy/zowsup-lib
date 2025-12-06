from loguru import logger

from yowsup.common.tools import Jid


class Group(object):
    TYPE_PARTICIPANT_ADMIN = "admin"
    
    @staticmethod
    def phone_to_lid(phone_number, device_no=0):
        """
        Converte um número de telefone para formato LID.
        
        Args:
            phone_number: Número de telefone (ex: "118498802032872")
            device_no: Número do dispositivo (padrão: 0)
        
        Returns:
            JID no formato LID (ex: "118498802032872:0@lid")
        """
        # Remove @s.whatsapp.net ou @lid se já estiver presente
        phone = phone_number.split('@')[0]
        # Remove :device se já estiver presente
        phone = phone.split(':')[0]
        return f"{phone}:{device_no}@lid"

    def __init__(self, groupId, creatorJid, subject, subjectOwnerJid, subjectTime, creationTime, participants=None, participants_phone_map=None):
        self._groupId           = groupId
        self._creatorJid        = creatorJid
        self._subject           = subject
        self._subjectOwnerJid   = subjectOwnerJid
        self._subjectTime       = int(subjectTime)
        self._creationTime      = int(creationTime)
        self._participants      = participants or {}
        # Mapeamento de phone_number (JID normal) para LID jid
        self._participants_phone_map = participants_phone_map or {}

    def getId(self):
        return self._groupId

    def getCreator(self):
        return self._creatorJid

    def getOwner(self):
        return self.getCreator()

    def getSubject(self):
        return self._subject

    def getSubjectOwner(self):
        return self._subjectOwnerJid

    def getSubjectTime(self):
        return self._subjectTime

    def getCreationTime(self):
        return self._creationTime

    def getGroupAdmins(self, full = True, account_jid = None):
        """
        Retorna lista de admins do grupo ou verifica se uma conta específica é admin.
        
        Args:
            full: Se True, retorna JID completo; se False, retorna apenas o número
            account_jid: (Opcional) JID da conta para verificar se é admin. 
                        Se fornecido, retorna lista de grupos onde a conta é admin.
        
        Returns:
            Se account_jid for fornecido: lista de IDs dos grupos onde a conta é admin
            Caso contrário: lista de JIDs dos admins
        """
        admins = []
        # for jid, _type in self.getParticipants().items():
        #     if _type == self.__class__.TYPE_PARTICIPANT_ADMIN:
        #         admins.append(jid if full else jid.split('@')[0])
        
        # Se account_jid foi fornecido, verifica se está na lista de admins
        if account_jid is not None:
            # Extrai o número de telefone do account_jid
            account_phone = account_jid.split('@')[0].split(':')[0] if '@' in account_jid else account_jid.split(':')[0]
            
            # Gera diferentes formatos possíveis para comparação
            account_formats = [
                account_jid,  # Formato original
                Jid.normalize(account_phone),  # JID normalizado (phone@s.whatsapp.net)
                self.phone_to_lid(account_phone),  # Formato LID (phone:0@lid)
                account_phone,  # Apenas o número
            ]
            
            logger.info(f"Account JID: {account_jid}, Account phone: {account_phone}")
            logger.info(f"Account formats to check: {account_formats}")

            # Verifica diretamente nos participantes se a conta é admin
            for participant_jid, participant_type in self.getParticipants().items():
                if participant_type == self.__class__.TYPE_PARTICIPANT_ADMIN:
                    # Extrai o número do participante para comparação
                    participant_phone = participant_jid.split('@')[0].split(':')[0] if '@' in participant_jid else participant_jid.split(':')[0]
                    
                    # Obtém phone_number do participante se disponível no mapeamento
                    participant_phone_number = self.getPhoneNumberByLid(participant_jid)
                    
                    logger.info(f"Participant: {participant_jid}, Participant phone: {participant_phone}, Phone number: {participant_phone_number}, Type: {participant_type}")
                    
                    # Compara em diferentes formatos (incluindo phone_number se disponível)
                    if (participant_jid in account_formats or 
                        participant_phone == account_phone or
                        participant_jid == self.phone_to_lid(account_phone) or
                        (participant_phone_number and participant_phone_number in account_formats) or
                        (participant_phone_number and account_jid == participant_phone_number)):
                        logger.info(f"Match found! Account is admin of group {self.getId()}")
                        return [self]
            
            logger.info(f"No match found. Account is not admin of group {self.getId()}")
            return []
        
        return admins
        
    def __str__(self):
        return "ID: %s, Subject: %s, Creation: %s, Creator: %s, Subject Owner: %s, Subject Time: %s\nParticipants: %s" %\
                (self.getId(), self.getSubject(), self.getCreationTime(), self.getCreator(),  self.getSubjectOwner(), self.getSubjectTime(), ", ".join(self._participants.keys()))

    def getParticipants(self):
        return self._participants
    
    def getParticipantsPhoneMap(self):
        """
        Retorna o mapeamento de phone_number (JID normal) para LID jid dos participantes.
        
        Returns:
            dict: {phone_number: lid_jid} mapeamento
        """
        return self._participants_phone_map
    
    def getPhoneNumberByLid(self, lid_jid):
        """
        Retorna o phone_number (JID normal) correspondente a um LID jid.
        
        Args:
            lid_jid: JID no formato LID (ex: "118498802032872:0@lid")
        
        Returns:
            phone_number no formato JID normal ou None se não encontrado
        """
        # Procura no mapeamento reverso
        for phone, lid in self._participants_phone_map.items():
            if lid == lid_jid:
                return phone
        return None
    
    def getLidByPhoneNumber(self, phone_number):
        """
        Retorna o LID jid correspondente a um phone_number (JID normal).
        
        Args:
            phone_number: JID no formato normal (ex: "201287239091@s.whatsapp.net")
        
        Returns:
            LID jid ou None se não encontrado
        """
        return self._participants_phone_map.get(phone_number)
