from __future__ import annotations

from typing import List, Optional
import threading

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import PendingRollbackError, InvalidRequestError

from zowsuplib.axolotl.identitykey import IdentityKey
from zowsuplib.axolotl.identitykeypair import IdentityKeyPair
from zowsuplib.axolotl.ecc.djbec import DjbECPublicKey, DjbECPrivateKey
from zowsuplib.axolotl.util.keyhelper import KeyHelper
from zowsuplib.axolotl.state.axolotlstore import AxolotlStore
from zowsuplib.axolotl.state.prekeyrecord import PreKeyRecord
from zowsuplib.axolotl.state.sessionrecord import SessionRecord
from zowsuplib.axolotl.state.signedprekeyrecord import SignedPreKeyRecord
from zowsuplib.axolotl.invalidkeyidexception import InvalidKeyIdException

from zowsuplib.app.db import SessionLocal
from zowsuplib.app import models


from loguru import logger


def _get_or_create_account(db: Session, phone: str) -> models.Account:
    """
    Ensures there is an Account row for the given phone.
    ✅ OTIMIZAÇÃO: Usa cache para reduzir queries.
    """
    from zowsuplib.app.db import _get_account_id_cached
    
    # ✅ OTIMIZAÇÃO: Usa cache para obter account_id
    account_id = _get_account_id_cached(db, phone, create_if_missing=True)
    
    if account_id is None:
        # Edge case: se create_if_missing=True mas ainda retornou None, cria manualmente
        account = models.Account(phone=phone)
        db.add(account)
        db.flush()
        db.refresh(account)
        from zowsuplib.app.db import _account_id_cache
        _account_id_cache.set(phone, account.id)
        logger.info(f"Created new Account row for phone={phone} (id={account.id})")
        return account
    
    # Busca o objeto Account completo pelo ID (mais eficiente que buscar por phone)
    # Usa one_or_none para tratar caso o account tenha sido deletado
    account = db.query(models.Account).filter_by(id=account_id).one_or_none()
    if account is None:
        # Account foi deletado - limpa cache e recria
        from zowsuplib.app.db import _account_id_cache
        _account_id_cache.invalidate(phone)
        logger.warning(f"Account {account_id} não encontrado para phone={phone}, recriando...")
        account = models.Account(phone=phone)
        db.add(account)
        db.flush()
        db.refresh(account)
        _account_id_cache.set(phone, account.id)
        logger.info(f"Recriado Account row para phone={phone} (id={account.id})")
    
    return account


class SqlIdentityKeyStore:
    """
    Identity store backed by SQLAlchemy / MySQL.
    Mirrors the behaviour of LiteIdentityKeyStore but bound to an Account.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

        # Lazily ensure local identity exists
        if self.getLocalRegistrationId() is None or self.getIdentityKeyPair() is None:
            identity = KeyHelper.generateIdentityKeyPair()
            registration_id = KeyHelper.generateRegistrationId(True)
            self._storeLocalData(registration_id, identity)

    def _query_local_row(self) -> Optional[models.Identity]:
        return (
            self.db.query(models.Identity)
            .filter(
                models.Identity.account_id == self.account.id,
                models.Identity.recipient_id == -1,
            )
            .one_or_none()
        )

    def getIdentityKeyPair(self) -> Optional[IdentityKeyPair]:
        row = self._query_local_row()
        if not row or not row.public_key or not row.private_key:
            return None

        public_key_bytes = row.public_key
        private_key_bytes = row.private_key
        # Original LiteIdentityKeyStore strips first byte (0x05) for public key
        return IdentityKeyPair(
            IdentityKey(DjbECPublicKey(public_key_bytes[1:])),
            DjbECPrivateKey(private_key_bytes),
        )

    def getLocalRegistrationId(self) -> Optional[int]:
        row = self._query_local_row()
        return row.registration_id if row else None

    def _storeLocalData(self, registrationId, identityKeyPair, deviceid: int = 0) -> None:
        try:
            row = self._query_local_row()
            if row is None:
                row = models.Identity(
                    account_id=self.account.id,
                    recipient_id=-1,
                    recipient_type=0,
                    device_id=deviceid,
                )
                self.db.add(row)

            row.registration_id = registrationId
            pub_key = identityKeyPair.getPublicKey().getPublicKey().serialize()
            priv_key = identityKeyPair.getPrivateKey().serialize()
            row.public_key = pub_key
            row.private_key = priv_key
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao armazenar dados locais de identidade: {e}", exc_info=True)
            raise

    def saveIdentity(self, recipientId, deviceId, identityKey) -> None:
        try:
            # Delete existing
            (
                self.db.query(models.Identity)
                .filter(
                    models.Identity.account_id == self.account.id,
                    models.Identity.recipient_id == recipientId,
                    models.Identity.device_id == deviceId,
                )
                .delete(synchronize_session=False)
            )
            pub_key = identityKey.getPublicKey().serialize()
            row = models.Identity(
                account_id=self.account.id,
                recipient_id=recipientId,
                recipient_type=0,
                device_id=deviceId,
                public_key=pub_key,
            )
            self.db.add(row)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Erro ao salvar Identity para recipientId={recipientId} deviceId={deviceId}: {e}",
                exc_info=True
            )
            raise

    def isTrustedIdentity(self, recipient, deviceid, identityKey) -> bool:
        public_key = (
            self.db.query(models.Identity.public_key)
            .filter(
                models.Identity.account_id == self.account.id,
                models.Identity.recipient_id == recipient,
                models.Identity.device_id == deviceid,
            )
            .scalar()
        )
        if not public_key:
            return True

        pub_key = identityKey.getPublicKey().serialize()
        return public_key == pub_key


class SqlPreKeyStore:
    """
    PreKey store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def loadPreKey(self, preKeyId: int) -> PreKeyRecord:
        record = (
            self.db.query(models.PreKey.record)
            .filter(
                models.PreKey.account_id == self.account.id,
                models.PreKey.prekey_id == preKeyId,
            )
            .scalar()
        )
        if not record:
            raise InvalidKeyIdException("No such prekeyrecord!")
        return PreKeyRecord(serialized=record)

    def loadUnsentPendingPreKeys(self) -> List[PreKeyRecord]:
        rows = (
            self.db.query(models.PreKey.record)
            .filter(
                models.PreKey.account_id == self.account.id,
                (models.PreKey.sent_to_server.is_(None))
                | (models.PreKey.sent_to_server.is_(False)),
            )
            .all()
        )
        return [PreKeyRecord(serialized=r[0]) for r in rows]

    def setAsSent(self, prekeyIds: List[int]) -> None:
        if not prekeyIds:
            return
        try:
            (
                self.db.query(models.PreKey)
                .filter(
                    models.PreKey.account_id == self.account.id,
                    models.PreKey.prekey_id.in_(prekeyIds),
                )
                .update(
                    {models.PreKey.sent_to_server: True},
                    synchronize_session=False,
                )
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao marcar PreKeys como enviados: {e}", exc_info=True)
            raise

    def loadPendingPreKeys(self) -> List[PreKeyRecord]:
        try:
            rows = self.db.query(models.PreKey.record).filter(models.PreKey.account_id == self.account.id).all()
            return [PreKeyRecord(serialized=r[0]) for r in rows]
        except (PendingRollbackError, InvalidRequestError) as e:
            logger.warning(f"Erro de transação inválida em loadPendingPreKeys, fazendo rollback: {e}")
            try:
                self.db.rollback()
                # Tenta novamente após rollback
                rows = self.db.query(models.PreKey.record).filter(models.PreKey.account_id == self.account.id).all()
                return [PreKeyRecord(serialized=r[0]) for r in rows]
            except Exception as retry_error:
                logger.error(f"Erro ao tentar novamente após rollback em loadPendingPreKeys: {retry_error}")
                # Retorna lista vazia em caso de erro persistente
                return []
        except Exception as e:
            logger.error(f"Erro inesperado em loadPendingPreKeys: {e}")
            # Tenta rollback mesmo para outros erros
            try:
                self.db.rollback()
            except:
                pass
            return []

    def storePreKey(self, preKeyId: int, preKeyRecord: PreKeyRecord) -> None:
        try:
            row = models.PreKey(
                account_id=self.account.id,
                prekey_id=preKeyId,
                record=preKeyRecord.serialize(),
            )
            self.db.add(row)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao armazenar PreKey {preKeyId}: {e}", exc_info=True)
            raise

    def containsPreKey(self, preKeyId: int) -> bool:
        q = (
            self.db.query(models.PreKey.id)
            .filter(
                models.PreKey.account_id == self.account.id,
                models.PreKey.prekey_id == preKeyId,
            )
            .exists()
        )
        return self.db.query(q).scalar()

    def removePreKey(self, preKeyId: int) -> None:
        try:
            (
                self.db.query(models.PreKey)
                .filter(
                    models.PreKey.account_id == self.account.id,
                    models.PreKey.prekey_id == preKeyId,
                )
                .delete(synchronize_session=False)
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover PreKey {preKeyId}: {e}", exc_info=True)
            raise

    def loadMaxPreKeyId(self) -> int:
        max_id = (
            self.db.query(func.max(models.PreKey.prekey_id))
            .filter(models.PreKey.account_id == self.account.id)
            .scalar()
        )
        return int(max_id or 0)

    def clear(self) -> None:
        (
            self.db.query(models.PreKey)
            .filter(models.PreKey.account_id == self.account.id)
            .delete(synchronize_session=False)
        )
        self.db.commit()


class SqlSignedPreKeyStore:
    """
    Signed prekey store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def loadSignedPreKey(self, signedPreKeyId: int) -> SignedPreKeyRecord:
        record = (
            self.db.query(models.SignedPreKey.record)
            .filter(
                models.SignedPreKey.account_id == self.account.id,
                models.SignedPreKey.prekey_id == signedPreKeyId,
            )
            .scalar()
        )
        if not record:
            raise InvalidKeyIdException("No such signedprekeyrecord! %s " % signedPreKeyId)
        return SignedPreKeyRecord(serialized=record)

    def loadSignedPreKeys(self) -> List[SignedPreKeyRecord]:
        rows = (
            self.db.query(models.SignedPreKey.record)
            .filter(models.SignedPreKey.account_id == self.account.id)
            .order_by(models.SignedPreKey.prekey_id.asc())
            .all()
        )
        return [SignedPreKeyRecord(serialized=r[0]) for r in rows]

    def storeSignedPreKey(self, signedPreKeyId: int, signedPreKeyRecord: SignedPreKeyRecord) -> None:
        try:
            # Delete existing
            (
                self.db.query(models.SignedPreKey)
                .filter(
                    models.SignedPreKey.account_id == self.account.id,
                    models.SignedPreKey.prekey_id == signedPreKeyId,
                )
                .delete(synchronize_session=False)
            )
            row = models.SignedPreKey(
                account_id=self.account.id,
                prekey_id=signedPreKeyId,
                timestamp=signedPreKeyRecord.getTimestamp(),
                record=signedPreKeyRecord.serialize(),
            )
            self.db.add(row)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao armazenar SignedPreKey {signedPreKeyId}: {e}", exc_info=True)
            raise

    def containsSignedPreKey(self, signedPreKeyId: int) -> bool:
        q = (
            self.db.query(models.SignedPreKey.id)
            .filter(
                models.SignedPreKey.account_id == self.account.id,
                models.SignedPreKey.prekey_id == signedPreKeyId,
            )
            .exists()
        )
        return self.db.query(q).scalar()

    def removeSignedPreKey(self, signedPreKeyId: int) -> None:
        try:
            (
                self.db.query(models.SignedPreKey)
                .filter(
                    models.SignedPreKey.account_id == self.account.id,
                    models.SignedPreKey.prekey_id == signedPreKeyId,
                )
                .delete(synchronize_session=False)
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover SignedPreKey {signedPreKeyId}: {e}", exc_info=True)
            raise


class SqlSessionStore:
    """
    Session store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def loadSession(self, account: int, deviceId: int) -> SessionRecord:
        record = (
            self.db.query(models.Session.record)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == account,
                models.Session.device_id == deviceId,
            )
            .scalar()
        )
        if record:
            return SessionRecord(serialized=record)
        return SessionRecord()

    def getSubDeviceSessions(self, recipient: int) -> List[int]:
        rows = (
            self.db.query(models.Session.device_id)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
            .all()
        )
        return [r[0] for r in rows]

    def storeSession(self, recipient: int, deviceId: int, sessionRecord: SessionRecord) -> None:
        try:
            # Delete existing first
            (
                self.db.query(models.Session)
                .filter(
                    models.Session.account_id == self.account.id,
                    models.Session.recipient_id == recipient,
                    models.Session.device_id == deviceId,
                )
                .delete(synchronize_session=False)
            )

            row = models.Session(
                account_id=self.account.id,
                recipient_id=recipient,
                device_id=deviceId,
                record=sessionRecord.serialize(),
            )
            self.db.add(row)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Erro ao armazenar Session para recipient={recipient} deviceId={deviceId}: {e}",
                exc_info=True
            )
            raise

    def containsSession(self, recipient: int, deviceId: int) -> bool:
        q = (
            self.db.query(models.Session.id)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
                models.Session.device_id == deviceId,
            )
            .exists()
        )
        return self.db.query(q).scalar()

    def deleteSession(self, recipient: int, deviceId: int) -> None:
        (
            self.db.query(models.Session)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
                models.Session.device_id == deviceId,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()

    def deleteAllSessions(self, recipient: int) -> None:
        (
            self.db.query(models.Session)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()

    def getAllAccounts(self, recipient: int) -> List[str]:
        rows = (
            self.db.query(
                models.Session.recipient_id,
                models.Session.recipient_type,
                models.Session.device_id,
            )
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
            .all()
        )
        return ["%d.%d:%d" % (r[0], r[1], r[2]) for r in rows]


class SqlSenderKeyStore:
    """
    SenderKey store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def storeSenderKey(self, senderKeyName, senderKeyRecord) -> None:
        # senderKeyName.getGroupId(), senderKeyName.getSender().getName()
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        serialized = senderKeyRecord.serialize()

        row = (
            self.db.query(models.SenderKey)
            .filter(
                models.SenderKey.account_id == self.account.id,
                models.SenderKey.group_id == group_id,
                models.SenderKey.sender_id == sender_id,
            )
            .one_or_none()
        )
        if row is None:
            row = models.SenderKey(
                account_id=self.account.id,
                group_id=group_id,
                sender_id=sender_id,
                record=serialized,
            )
            self.db.add(row)
        else:
            row.record = serialized
        self.db.commit()

    def loadSenderKey(self, senderKeyName):
        from zowsuplib.axolotl.groups.state.senderkeyrecord import SenderKeyRecord

        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        record = (
            self.db.query(models.SenderKey.record)
            .filter(
                models.SenderKey.account_id == self.account.id,
                models.SenderKey.group_id == group_id,
                models.SenderKey.sender_id == sender_id,
            )
            .scalar()
        )
        if not record:
            return SenderKeyRecord()
        return SenderKeyRecord(serialized=record)


class SqlPollStore:
    """
    Poll store backed by SQLAlchemy.
    Exposed via SqlAxolotlStore.pollStore for compatibility with existing code.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def deletePoll(self, poll_msg_id: int) -> None:
        poll = (
            self.db.query(models.Poll)
            .filter(
                models.Poll.account_id == self.account.id,
                models.Poll.poll_msg_id == poll_msg_id,
            )
            .one_or_none()
        )
        if poll:
            self.db.delete(poll)
            self.db.commit()

    def storePoll(self, poll_msg_id: int, name: str, enc_key: bytes, options: List[str]) -> None:
        poll = models.Poll(
            account_id=self.account.id,
            poll_msg_id=poll_msg_id,
            enc_key=enc_key,
            name=name,
        )
        self.db.add(poll)
        self.db.flush()  # so poll.id is available

        import hashlib

        for item in options:
            opt_hash = hashlib.sha256(item.encode()).digest()
            opt = models.PollOption(
                poll_id=poll.id,
                option_name=item,
                option_sha256=opt_hash,
            )
            self.db.add(opt)

        self.db.commit()

    def decryptOptions(self, poll_msg_id: int, option_sha256_list: List[bytes]) -> List[str]:
        options: List[str] = []
        poll = (
            self.db.query(models.Poll)
            .filter(
                models.Poll.account_id == self.account.id,
                models.Poll.poll_msg_id == poll_msg_id,
            )
            .one_or_none()
        )
        if not poll:
            return ["ITEM ERROR"] * len(option_sha256_list)

        for sha256_item in option_sha256_list:
            opt = (
                self.db.query(models.PollOption)
                .filter(
                    models.PollOption.poll_id == poll.id,
                    models.PollOption.option_sha256 == sha256_item,
                )
                .one_or_none()
            )
            if opt:
                options.append(opt.option_name)
            else:
                options.append("ITEM ERROR")
        return options

    def getPollEncKey(self, poll_msg_id: int) -> Optional[bytes]:
        poll = (
            self.db.query(models.Poll)
            .filter(
                models.Poll.account_id == self.account.id,
                models.Poll.poll_msg_id == poll_msg_id,
            )
            .one_or_none()
        )
        return poll.enc_key if poll else None


class SqlAppStateStore:
    """
    AppState key store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def addAppStateKeys(self, keys) -> None:
        import time
        from zowsuplib.yowsup.layers.protocol_historysync.protocolentities.attributes import (
            AppStateSyncKeyAttribute,
        )

        now = int(time.time())
        for key in keys:
            row = models.AppStateKey(
                account_id=self.account.id,
                key_id=key.key_id.key_id,
                key_data=key.key_data.key_data,
                fingerprint=None,
                timestamp=now,
            )
            self.db.add(row)
        self.db.commit()

    def getOneAppStateKey(self):
        from zowsuplib.yowsup.layers.protocol_historysync.protocolentities.attributes import (
            AppStateSyncKeyAttribute,
            AppStateSyncKeyIdAttribute,
            AppStateSyncKeyDataAttribute,
        )

        row = (
            self.db.query(models.AppStateKey)
            .filter(models.AppStateKey.account_id == self.account.id)
            .order_by(models.AppStateKey.timestamp.desc())
            .first()
        )
        if not row:
            return None
        return AppStateSyncKeyAttribute(
            key_id=AppStateSyncKeyIdAttribute(key_id=row.key_id),
            key_data=AppStateSyncKeyDataAttribute(
                key_data=row.key_data,
                fingerprint=row.fingerprint,
                timestamp=row.timestamp,
            ),
        )

    def getAppStateKey(self, key_id: bytes):
        from zowsuplib.yowsup.layers.protocol_historysync.protocolentities.attributes import (
            AppStateSyncKeyAttribute,
            AppStateSyncKeyIdAttribute,
            AppStateSyncKeyDataAttribute,
        )

        row = (
            self.db.query(models.AppStateKey)
            .filter(
                models.AppStateKey.account_id == self.account.id,
                models.AppStateKey.key_id == key_id,
            )
            .one_or_none()
        )
        if not row:
            return None
        return AppStateSyncKeyAttribute(
            key_id=AppStateSyncKeyIdAttribute(key_id=row.key_id),
            key_data=AppStateSyncKeyDataAttribute(
                key_data=row.key_data,
                fingerprint=row.fingerprint,
                timestamp=row.timestamp,
            ),
        )

    def deleteAppStateKey(self, key_id: bytes) -> None:
        (
            self.db.query(models.AppStateKey)
            .filter(
                models.AppStateKey.account_id == self.account.id,
                models.AppStateKey.key_id == key_id,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()


class SqlContactStore:
    """
    Contact store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def addContact(self, jid: str, name: Optional[str] = None):
        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return None
        if name is None:
            name = ""
        if not self.findContact(jid):
            import time

            row = models.Contact(
                account_id=self.account.id,
                jid=jid,
                name=name,
                timestamp=int(time.time()),
            )
            self.db.add(row)
            self.db.commit()
            return jid
        return None

    def findContact(self, jid: str):
        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return None
        row = (
            self.db.query(models.Contact)
            .filter(
                models.Contact.account_id == self.account.id,
                models.Contact.jid == jid,
            )
            .one_or_none()
        )
        return bool(row)

    def isNewContact(self, jid: str) -> bool:
        if jid.endswith("@s.whatsapp.net") or jid.endswith("@c.us"):
            return not self.findContact(jid)
        return False

    def removeContact(self, jid: str) -> bool:
        (
            self.db.query(models.Contact)
            .filter(
                models.Contact.account_id == self.account.id,
                models.Contact.jid == jid,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return True

    def getAllContact(self):
        rows = (
            self.db.query(models.Contact.jid)
            .filter(models.Contact.account_id == self.account.id)
            .all()
        )
        return [r[0] for r in rows]


class SqlBroadcastStore:
    """
    Broadcast store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def phash(self, jids):
        import hashlib
        import base64

        jids = sorted(jids)
        h = hashlib.sha256()
        for jid in jids:
            h.update(jid.encode())
        return "2:" + base64.b64encode(h.digest()[:6]).decode()

    def addBroadcast(self, jids, senderJid, name=None):
        from zowsuplib.yowsup.common.tools import WATools

        if isinstance(jids, str):
            jids = jids.split(",")

        newJid = [WATools.fullJid(j) for j in jids]
        newJid.append(WATools.fullJid(senderJid))

        phash = self.phash(newJid)
        if name is None:
            name = ""

        # Try to reuse existing broadcast by phash
        bcast = (
            self.db.query(models.Broadcast)
            .filter(
                models.Broadcast.account_id == self.account.id,
                models.Broadcast.phash == phash,
            )
            .one_or_none()
        )
        if bcast:
            return bcast.bcid, bcast.phash

        import time

        bcid = "%d@broadcast" % time.time()
        bcast = models.Broadcast(
            account_id=self.account.id,
            sender=WATools.fullJid(senderJid),
            name=name,
            jids=",".join(newJid),
            phash=phash,
            bcid=bcid,
        )
        self.db.add(bcast)
        self.db.commit()
        return bcid, phash

    def findParticipantsByBcid(self, bcid: str):
        bcast = (
            self.db.query(models.Broadcast)
            .filter(
                models.Broadcast.account_id == self.account.id,
                models.Broadcast.bcid == bcid,
            )
            .one_or_none()
        )
        if not bcast:
            return None
        # Return list of jids excluding sender
        jids = [item for item in bcast.jids.split(",") if item != bcast.sender]
        return jids


class SqlTrustedContactStore:
    """
    Trusted contact store backed by SQLAlchemy.
    """

    def __init__(self, db: Session, account: models.Account):
        self.db = db
        self.account = account

    def updateTrustedContact(self, jid: str, tctoken: Optional[bytes] = None) -> bool:
        import time

        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return False
        if tctoken is None:
            return False

        (
            self.db.query(models.TrustedContact)
            .filter(
                models.TrustedContact.account_id == self.account.id,
                models.TrustedContact.jid == jid,
            )
            .delete(synchronize_session=False)
        )
        row = models.TrustedContact(
            account_id=self.account.id,
            jid=jid,
            incoming_tc_token=tctoken,
            timestamp=int(time.time()),
        )
        self.db.add(row)
        self.db.commit()
        return True

    def getTcToken(self, jid: str) -> Optional[bytes]:
        row = (
            self.db.query(models.TrustedContact)
            .filter(
                models.TrustedContact.account_id == self.account.id,
                models.TrustedContact.jid == jid,
            )
            .one_or_none()
        )
        return row.incoming_tc_token if row else None

    def removeTrustedContact(self, jid: str) -> bool:
        (
            self.db.query(models.TrustedContact)
            .filter(
                models.TrustedContact.account_id == self.account.id,
                models.TrustedContact.jid == jid,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return True


class SqlAxolotlStore(AxolotlStore):
    """
    Axolotl store implementation backed by MySQL/SQLAlchemy.

    It wraps the per‑table stores above and exposes the same public surface
    as LiteAxolotlStore so that AxolotlManager and the rest of the stack
    can work unchanged.
    
    IMPORTANT: This store uses thread-local sessions for thread-safe isolation.
    Each thread gets its own session, preventing concurrent operation errors.
    The session is automatically managed via thread-local storage.
    """

    def __init__(self, username: str):
        """
        :param username: phone / account identifier (same as AxolotlManager.username)
        """
        self._username = username
        self._account_id: Optional[int] = None
        self._closed = False
        # NÃO armazena sessão aqui - usa thread-local
        # Sub-stores serão criados com sessão thread-local quando necessário
        self._sub_stores_initialized = False
        # Lock para proteger inicialização de sub-stores (evita race conditions)
        self._init_lock = threading.RLock()

    def _get_session(self) -> Session:
        """
        Obtém sessão thread-local para a thread atual.
        Thread-safe: cada thread tem sua própria sessão isolada.
        
        Valida que a sessão não está sendo compartilhada entre contas diferentes.
        
        Returns:
            Session: Sessão isolada para a thread atual
        """
        if self._closed:
            raise RuntimeError("SqlAxolotlStore foi fechado. Não é possível reutilizar.")
        
        from zowsuplib.app.db import get_thread_local_session
        session = get_thread_local_session()
        
        # Validação de isolamento: garante que a sessão é thread-local
        # Cada thread deve ter sua própria sessão isolada
        thread_id = threading.current_thread().ident
        if not hasattr(session, '_thread_id'):
            session._thread_id = thread_id
        elif session._thread_id != thread_id:
            logger.warning(
                f"[ISOLATION] Possível compartilhamento de sessão detectado | "
                f"username={self._username} expected_thread={session._thread_id} "
                f"current_thread={thread_id}"
            )
        
        return session
    
    def _get_account(self, db: Session) -> models.Account:
        """
        Obtém ou cria account para a sessão atual.
        Usa cache para evitar queries repetidas.
        
        Valida que o account corresponde ao username correto para garantir isolamento.
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            models.Account: Account associado ao username
            
        Raises:
            RuntimeError: Se não for possível obter ou criar o account
        """
        if self._account_id is None:
            account = _get_or_create_account(db, self._username)
            self._account_id = account.id
            # Validação de isolamento: garante que o account corresponde ao username
            if account.phone != self._username:
                logger.error(
                    f"[ISOLATION] Account ID {account.id} não corresponde ao username {self._username} | "
                    f"account.phone={account.phone}"
                )
                raise RuntimeError(f"Account mismatch: expected {self._username}, got {account.phone}")
            return account
        
        # Busca account pelo ID (mais eficiente que buscar por phone)
        # Usa one_or_none para tratar caso o account tenha sido deletado
        account = db.query(models.Account).filter_by(id=self._account_id).one_or_none()
        
        # Se não encontrou, limpa cache e recria
        if account is None:
            logger.warning(
                f"Account {self._account_id} não encontrado para username={self._username}, "
                f"limpando cache e recriando..."
            )
            self._account_id = None
            account = _get_or_create_account(db, self._username)
            self._account_id = account.id
        
        # Validação de isolamento: garante que o account corresponde ao username
        if account.phone != self._username:
            logger.error(
                f"[ISOLATION] Account ID {account.id} não corresponde ao username {self._username} | "
                f"account.phone={account.phone}"
            )
            # Limpa cache e recria para corrigir
            self._account_id = None
            account = _get_or_create_account(db, self._username)
            self._account_id = account.id
        
        return account
    
    def _ensure_sub_stores(self, db: Session, account: models.Account):
        """
        Cria sub-stores se ainda não foram inicializados.
        Cada sub-store recebe a sessão thread-local atual.
        Thread-safe: usa lock para evitar race conditions.
        
        Args:
            db: Sessão thread-local atual
            account: Account associado
        """
        with self._init_lock:
            if self._sub_stores_initialized:
                # Atualiza referências de db e account nos sub-stores existentes
                # Isso é necessário porque o account pode estar detached da sessão anterior
                self._update_sub_stores_db_and_account(db, account)
                return
            
            # Cria sub-stores pela primeira vez
            self.identityKeyStore = SqlIdentityKeyStore(db, account)
            self.preKeyStore = SqlPreKeyStore(db, account)
            self.signedPreKeyStore = SqlSignedPreKeyStore(db, account)
            self.sessionStore = SqlSessionStore(db, account)
            self.senderKeyStore = SqlSenderKeyStore(db, account)
            self.pollStore = SqlPollStore(db, account)
            self.appStateStore = SqlAppStateStore(db, account)
            self.contactStore = SqlContactStore(db, account)
            self.broadcastStore = SqlBroadcastStore(db, account)
            self.trustedContactStore = SqlTrustedContactStore(db, account)
            
            self._sub_stores_initialized = True
    
    def _update_sub_stores_db_and_account(self, db: Session, account: models.Account):
        """
        Atualiza referências de db e account nos sub-stores.
        Isso é necessário para evitar DetachedInstanceError quando a sessão muda.
        Garante que o account está vinculado à sessão atual usando merge.
        
        Args:
            db: Nova sessão thread-local
            account: Account vinculado à nova sessão
        """
        # Garante que o account está vinculado à sessão atual
        # Isso evita DetachedInstanceError quando o account veio de outra sessão
        try:
            # Tenta fazer merge do account na sessão atual
            # Se o account já estiver na sessão, merge retorna o mesmo objeto
            account = db.merge(account)
        except Exception as e:
            # Se merge falhar, tenta recarregar o account da sessão atual
            logger.warning(f"Erro ao fazer merge do account na sessão: {e}, tentando recarregar...")
            try:
                account = db.query(models.Account).filter_by(id=account.id).one()
            except Exception as reload_error:
                logger.error(f"Erro ao recarregar account: {reload_error}")
                # Se tudo falhar, tenta buscar por username
                account = _get_or_create_account(db, self._username)
                self._account_id = account.id
        
        stores = [
            self.identityKeyStore,
            self.preKeyStore,
            self.signedPreKeyStore,
            self.sessionStore,
            self.senderKeyStore,
            self.pollStore,
            self.appStateStore,
            self.contactStore,
            self.broadcastStore,
            self.trustedContactStore,
        ]
        
        for store in stores:
            if store is not None:
                if hasattr(store, 'db'):
                    store.db = db
                if hasattr(store, 'account'):
                    store.account = account
    
    def _update_sub_stores_db(self, db: Session):
        """
        Atualiza apenas a referência de db nos sub-stores (account não mudou).
        DEPRECATED: Use _update_sub_stores_db_and_account em vez disso.
        
        Args:
            db: Nova sessão thread-local
        """
        stores = [
            self.identityKeyStore,
            self.preKeyStore,
            self.signedPreKeyStore,
            self.sessionStore,
            self.senderKeyStore,
            self.pollStore,
            self.appStateStore,
            self.contactStore,
            self.broadcastStore,
            self.trustedContactStore,
        ]
        
        for store in stores:
            if store is not None and hasattr(store, 'db'):
                store.db = db
    
    def close(self):
        """
        Marca o store como fechado.
        Não fecha sessões thread-local (elas são gerenciadas automaticamente).
        """
        self._closed = True
        self._account_id = None
        self._sub_stores_initialized = False
        # Não fecha sessões aqui - elas são gerenciadas por thread via thread-local storage
    
    def __del__(self):
        """
        Cleanup automático quando o objeto é destruído.
        Não precisa fechar sessões thread-local aqui.
        """
        self._closed = True

    def __str__(self):
        return "mysql:account=%s" % self._username

    # Identity store facade
    def getIdentityKeyPair(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.identityKeyStore.getIdentityKeyPair()

    def getLocalRegistrationId(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.identityKeyStore.getLocalRegistrationId()

    def saveIdentity(self, recipientId, deviceId, identityKey):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.identityKeyStore.saveIdentity(recipientId, deviceId, identityKey)

    def isTrustedIdentity(self, recipientId, deviceId, identityKey):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.identityKeyStore.isTrustedIdentity(recipientId, deviceId, identityKey)

    # Helper for migration/import flows: update local identity row
    def updateLocalIdentityKeys(self, registration_id, public_key, private_key, deviceid: int = 0) -> None:
        """
        Updates the local identity row (recipient_id = -1) with the provided
        registration_id, public_key and private_key.

        This is used by legacy import/export flows that previously updated
        the SQLite 'identities' table directly.
        """
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        
        try:
            row = (
                db.query(models.Identity)
                .filter(
                    models.Identity.account_id == account.id,
                    models.Identity.recipient_id == -1,
                )
                .one_or_none()
            )
            if row is None:
                row = models.Identity(
                    account_id=account.id,
                    recipient_id=-1,
                    recipient_type=0,
                    device_id=deviceid,
                )
                db.add(row)

            row.registration_id = registration_id
            row.public_key = public_key
            row.private_key = private_key
            row.device_id = deviceid
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao atualizar chaves de identidade locais: {e}", exc_info=True)
            raise

    # PreKey store facade
    def loadPreKey(self, preKeyId):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.preKeyStore.loadPreKey(preKeyId)

    def loadPreKeys(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.preKeyStore.loadPendingPreKeys()

    def storePreKey(self, preKeyId, preKeyRecord):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.preKeyStore.storePreKey(preKeyId, preKeyRecord)

    def containsPreKey(self, preKeyId):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.preKeyStore.containsPreKey(preKeyId)

    def removePreKey(self, preKeyId):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.preKeyStore.removePreKey(preKeyId)

    def removeAllPreKeys(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.preKeyStore.clear()

    # Session store facade
    def loadSession(self, account, deviceId):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        return self.sessionStore.loadSession(account, deviceId)

    def getSubDeviceSessions(self, account):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        return self.sessionStore.getSubDeviceSessions(account)

    def storeSession(self, account, deviceId, sessionRecord):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        self.sessionStore.storeSession(account, deviceId, sessionRecord)

    def containsSession(self, account, deviceId):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        return self.sessionStore.containsSession(account, deviceId)

    def deleteSession(self, account, deviceId):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        self.sessionStore.deleteSession(account, deviceId)

    def deleteAllSessions(self, account):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        self.sessionStore.deleteAllSessions(account)

    def getAllAccounts(self, account):
        db = self._get_session()
        account_obj = self._get_account(db)
        self._ensure_sub_stores(db, account_obj)
        return self.sessionStore.getAllAccounts(account)

    # Signed prekey facade
    def loadSignedPreKey(self, signedPreKeyId):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.signedPreKeyStore.loadSignedPreKey(signedPreKeyId)

    def loadSignedPreKeys(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.signedPreKeyStore.loadSignedPreKeys()

    def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.signedPreKeyStore.storeSignedPreKey(signedPreKeyId, signedPreKeyRecord)

    def containsSignedPreKey(self, signedPreKeyId):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.signedPreKeyStore.containsSignedPreKey(signedPreKeyId)

    def removeSignedPreKey(self, signedPreKeyId):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.signedPreKeyStore.removeSignedPreKey(signedPreKeyId)

    # Sender key facade
    def loadSenderKey(self, senderKeyName):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.senderKeyStore.loadSenderKey(senderKeyName)

    def storeSenderKey(self, senderKeyName, senderKeyRecord):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        self.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord)

    # App state keys
    def addAppStateKeys(self, keys):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.appStateStore.addAppStateKeys(keys)

    def getOneAppStateKey(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.appStateStore.getOneAppStateKey()

    def getAppStateKey(self, key_id):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.appStateStore.getAppStateKey(key_id)

    def removeAppStateKey(self, key_id):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.appStateStore.deleteAppStateKey(key_id)

    # Contacts
    def addContact(self, jid):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.contactStore.addContact(jid, "")

    def removeContact(self, jid):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.contactStore.removeContact(jid)

    def getAllContact(self):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.contactStore.getAllContact()

    def findContact(self, jid):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.contactStore.findContact(jid)

    def isNewContact(self, jid):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.contactStore.isNewContact(jid)

    # Broadcasts
    def addBroadcast(self, jids, senderJid, name=None):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.broadcastStore.addBroadcast(jids, senderJid, name)

    def findParticipantsByBcid(self, bcid):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.broadcastStore.findParticipantsByBcid(bcid)

    # Trusted contacts
    def updateTrustedContact(self, jid, tctoken):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.trustedContactStore.updateTrustedContact(jid, tctoken)

    def getTcToken(self, jid):
        db = self._get_session()
        account = self._get_account(db)
        self._ensure_sub_stores(db, account)
        return self.trustedContactStore.getTcToken(jid)




