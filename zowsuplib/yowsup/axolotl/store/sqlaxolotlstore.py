from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func
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
    """
    account = db.query(models.Account).filter_by(phone=phone).one_or_none()
    if account is None:
        account = models.Account(phone=phone)
        db.add(account)
        db.commit()
        db.refresh(account)
        logger.info(f"Created new Account row for phone={phone} (id={account.id})")
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

    def saveIdentity(self, recipientId, deviceId, identityKey) -> None:
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
        row = models.PreKey(
            account_id=self.account.id,
            prekey_id=preKeyId,
            record=preKeyRecord.serialize(),
        )
        self.db.add(row)
        self.db.commit()

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
        (
            self.db.query(models.PreKey)
            .filter(
                models.PreKey.account_id == self.account.id,
                models.PreKey.prekey_id == preKeyId,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()

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
        (
            self.db.query(models.SignedPreKey)
            .filter(
                models.SignedPreKey.account_id == self.account.id,
                models.SignedPreKey.prekey_id == signedPreKeyId,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()


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
    
    IMPORTANT: This store maintains a session for performance, but it should be
    closed explicitly via close() when the store is no longer needed to prevent
    connection pool exhaustion. The session is automatically recreated if needed.
    """

    def __init__(self, username: str):
        """
        :param username: phone / account identifier (same as AxolotlManager.username)
        """
        self._username = username
        self._db: Optional[Session] = None
        self._account: Optional[models.Account] = None
        self._account_id: Optional[int] = None
        self._closed = False
        
        # Inicializa sessão e account (lazy initialization)
        self._ensure_session()

    def _ensure_session(self):
        """
        Garante que há uma sessão ativa. Cria uma nova se necessário.
        """
        if self._closed:
            raise RuntimeError("SqlAxolotlStore foi fechado. Não é possível reutilizar.")
        
        # Verifica se precisa recriar sessão (None, fechada ou inativa)
        needs_new_session = (
            self._db is None or 
            not hasattr(self._db, 'is_active') or 
            not self._db.is_active
        )
        
        if needs_new_session:
            # Fecha sessão anterior se existir e estiver inativa
            if self._db is not None:
                try:
                    self._db.close()
                except Exception:
                    pass
            
            # Cria nova sessão
            self._db = SessionLocal()
            self._account = _get_or_create_account(self._db, self._username)
            self._account_id = self._account.id
            
            # Recria sub-stores com nova sessão
            self.identityKeyStore = SqlIdentityKeyStore(self._db, self._account)
            self.preKeyStore = SqlPreKeyStore(self._db, self._account)
            self.signedPreKeyStore = SqlSignedPreKeyStore(self._db, self._account)
            self.sessionStore = SqlSessionStore(self._db, self._account)
            self.senderKeyStore = SqlSenderKeyStore(self._db, self._account)
            self.pollStore = SqlPollStore(self._db, self._account)
            self.appStateStore = SqlAppStateStore(self._db, self._account)
            self.contactStore = SqlContactStore(self._db, self._account)
            self.broadcastStore = SqlBroadcastStore(self._db, self._account)
            self.trustedContactStore = SqlTrustedContactStore(self._db, self._account)
    
    def close(self):
        """
        Fecha a sessão do banco de dados explicitamente.
        
        Deve ser chamado quando o store não for mais necessário para liberar
        a conexão do pool. Após fechar, o store não pode ser reutilizado.
        """
        if self._db is not None:
            try:
                self._db.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar sessão do SqlAxolotlStore para {self._username}: {e}")
            finally:
                self._db = None
                self._account = None
                self._account_id = None
                self._closed = True
    
    def __del__(self):
        """
        Cleanup automático quando o objeto é destruído.
        Não confiável, mas ajuda a prevenir vazamentos.
        """
        if self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass

    def __str__(self):
        account_phone = self._account.phone if self._account else self._username
        return "mysql:account=%s" % account_phone

    # Identity store facade
    def getIdentityKeyPair(self):
        self._ensure_session()
        return self.identityKeyStore.getIdentityKeyPair()

    def getLocalRegistrationId(self):
        self._ensure_session()
        return self.identityKeyStore.getLocalRegistrationId()

    def saveIdentity(self, recipientId, deviceId, identityKey):
        self._ensure_session()
        self.identityKeyStore.saveIdentity(recipientId, deviceId, identityKey)

    def isTrustedIdentity(self, recipientId, deviceId, identityKey):
        self._ensure_session()
        return self.identityKeyStore.isTrustedIdentity(recipientId, deviceId, identityKey)

    # Helper for migration/import flows: update local identity row
    def updateLocalIdentityKeys(self, registration_id, public_key, private_key, deviceid: int = 0) -> None:
        """
        Updates the local identity row (recipient_id = -1) with the provided
        registration_id, public_key and private_key.

        This is used by legacy import/export flows that previously updated
        the SQLite 'identities' table directly.
        """
        self._ensure_session()
        
        row = (
            self._db.query(models.Identity)
            .filter(
                models.Identity.account_id == self._account.id,
                models.Identity.recipient_id == -1,
            )
            .one_or_none()
        )
        if row is None:
            row = models.Identity(
                account_id=self._account.id,
                recipient_id=-1,
                recipient_type=0,
                device_id=deviceid,
            )
            self._db.add(row)

        row.registration_id = registration_id
        row.public_key = public_key
        row.private_key = private_key
        row.device_id = deviceid
        self._db.commit()

    # PreKey store facade
    def loadPreKey(self, preKeyId):
        return self.preKeyStore.loadPreKey(preKeyId)

    def loadPreKeys(self):
        return self.preKeyStore.loadPendingPreKeys()

    def storePreKey(self, preKeyId, preKeyRecord):
        self.preKeyStore.storePreKey(preKeyId, preKeyRecord)

    def containsPreKey(self, preKeyId):
        return self.preKeyStore.containsPreKey(preKeyId)

    def removePreKey(self, preKeyId):
        self.preKeyStore.removePreKey(preKeyId)

    def removeAllPreKeys(self):
        self.preKeyStore.clear()

    # Session store facade
    def loadSession(self, account, deviceId):
        return self.sessionStore.loadSession(account, deviceId)

    def getSubDeviceSessions(self, account):
        return self.sessionStore.getSubDeviceSessions(account)

    def storeSession(self, account, deviceId, sessionRecord):
        self.sessionStore.storeSession(account, deviceId, sessionRecord)

    def containsSession(self, account, deviceId):
        return self.sessionStore.containsSession(account, deviceId)

    def deleteSession(self, account, deviceId):
        self.sessionStore.deleteSession(account, deviceId)

    def deleteAllSessions(self, account):
        self.sessionStore.deleteAllSessions(account)

    def getAllAccounts(self, account):
        return self.sessionStore.getAllAccounts(account)

    # Signed prekey facade
    def loadSignedPreKey(self, signedPreKeyId):
        return self.signedPreKeyStore.loadSignedPreKey(signedPreKeyId)

    def loadSignedPreKeys(self):
        return self.signedPreKeyStore.loadSignedPreKeys()

    def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        self.signedPreKeyStore.storeSignedPreKey(signedPreKeyId, signedPreKeyRecord)

    def containsSignedPreKey(self, signedPreKeyId):
        return self.signedPreKeyStore.containsSignedPreKey(signedPreKeyId)

    def removeSignedPreKey(self, signedPreKeyId):
        self.signedPreKeyStore.removeSignedPreKey(signedPreKeyId)

    # Sender key facade
    def loadSenderKey(self, senderKeyName):
        return self.senderKeyStore.loadSenderKey(senderKeyName)

    def storeSenderKey(self, senderKeyName, senderKeyRecord):
        self.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord)

    # App state keys
    def addAppStateKeys(self, keys):
        return self.appStateStore.addAppStateKeys(keys)

    def getOneAppStateKey(self):
        return self.appStateStore.getOneAppStateKey()

    def getAppStateKey(self, key_id):
        return self.appStateStore.getAppStateKey(key_id)

    def removeAppStateKey(self, key_id):
        return self.appStateStore.deleteAppStateKey(key_id)

    # Contacts
    def addContact(self, jid):
        return self.contactStore.addContact(jid, "")

    def removeContact(self, jid):
        return self.contactStore.removeContact(jid)

    def getAllContact(self):
        return self.contactStore.getAllContact()

    def findContact(self, jid):
        return self.contactStore.findContact(jid)

    def isNewContact(self, jid):
        return self.contactStore.isNewContact(jid)

    # Broadcasts
    def addBroadcast(self, jids, senderJid, name=None):
        return self.broadcastStore.addBroadcast(jids, senderJid, name)

    def findParticipantsByBcid(self, bcid):
        return self.broadcastStore.findParticipantsByBcid(bcid)

    # Trusted contacts
    def updateTrustedContact(self, jid, tctoken):
        return self.trustedContactStore.updateTrustedContact(jid, tctoken)

    def getTcToken(self, jid):
        return self.trustedContactStore.getTcToken(jid)




