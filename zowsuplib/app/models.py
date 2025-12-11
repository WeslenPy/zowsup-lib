from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from zowsuplib.app.db import Base


class Account(Base):
    """
    Represents a WhatsApp account (one phone number).

    This is the root entity used to tie together all Axolotl / protocol
    data that previously lived in separate axolotl.db files per account.
    """

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    pushname = Column(String(255), nullable=True)
    env = Column(String(32), nullable=True)  # android, smb_android, ios, smb_ios, ...

    # Status fields
    is_logged_in = Column(Boolean, nullable=False, default=False, index=True)
    master = Column(Boolean, nullable=False, default=False)
    has_restriction = Column(Boolean, nullable=False, default=False, index=True)
    is_initialized = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    # Relationships
    identities = relationship("Identity", back_populates="account", cascade="all, delete-orphan")
    prekeys = relationship("PreKey", back_populates="account", cascade="all, delete-orphan")
    signed_prekeys = relationship("SignedPreKey", back_populates="account", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="account", cascade="all, delete-orphan")
    sender_keys = relationship("SenderKey", back_populates="account", cascade="all, delete-orphan")
    polls = relationship("Poll", back_populates="account", cascade="all, delete-orphan")
    app_state_keys = relationship("AppStateKey", back_populates="account", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    broadcasts = relationship("Broadcast", back_populates="account", cascade="all, delete-orphan")
    trusted_contacts = relationship("TrustedContact", back_populates="account", cascade="all, delete-orphan")
    sent_messages = relationship("SentMessage", back_populates="account", cascade="all, delete-orphan")


class Identity(Base):
    """
    Port of the `identities` table from LiteIdentityKeyStore, with an
    additional foreign key to Account for multi‑account support.
    """

    __tablename__ = "identities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    recipient_id = Column(BigInteger, nullable=False)
    recipient_type = Column(Integer, nullable=False, default=0)
    device_id = Column(Integer, nullable=False, default=0)
    registration_id = Column(Integer, nullable=True)
    public_key = Column(LargeBinary, nullable=True)
    private_key = Column(LargeBinary, nullable=True)
    next_prekey_id = Column(Integer, nullable=True)
    timestamp = Column(BigInteger, nullable=True)

    account = relationship("Account", back_populates="identities")

    __table_args__ = (
        Index("ix_identity_account_recipient_device", "account_id", "recipient_id", "device_id"),
    )


class PreKey(Base):
    """
    Port of the `prekeys` table from LitePreKeyStore.
    """

    __tablename__ = "prekeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    prekey_id = Column(Integer, nullable=False)
    sent_to_server = Column(Boolean, nullable=True)
    record = Column(LargeBinary, nullable=False)

    account = relationship("Account", back_populates="prekeys")

    __table_args__ = (
        UniqueConstraint("account_id", "prekey_id", name="uq_prekeys_account_prekey"),
    )


class SignedPreKey(Base):
    """
    Port of the `signed_prekeys` table from LiteSignedPreKeyStore.
    """

    __tablename__ = "signed_prekeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    prekey_id = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, nullable=True)
    record = Column(LargeBinary, nullable=False)

    account = relationship("Account", back_populates="signed_prekeys")

    __table_args__ = (
        UniqueConstraint("account_id", "prekey_id", name="uq_signed_prekeys_account_prekey"),
    )


class Session(Base):
    """
    Port of the `sessions` table from LiteSessionStore.
    """

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    recipient_id = Column(BigInteger, nullable=False)
    recipient_type = Column(Integer, nullable=False, default=0)
    device_id = Column(Integer, nullable=False)
    record = Column(LargeBinary, nullable=False)
    timestamp = Column(BigInteger, nullable=True)

    account = relationship("Account", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_account_recipient_device", "account_id", "recipient_id", "device_id", unique=True),
    )


class SenderKey(Base):
    """
    Port of the `sender_keys` table from LiteSenderKeyStore.
    """

    __tablename__ = "sender_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    group_id = Column(String(255), nullable=False)
    sender_id = Column(String(255), nullable=False)
    record = Column(LargeBinary, nullable=False)

    account = relationship("Account", back_populates="sender_keys")

    __table_args__ = (
        Index("ix_sender_keys_account_group_sender", "account_id", "group_id", "sender_id", unique=True),
    )


class Poll(Base):
    """
    Port of the `poll` table from LitePollStore.
    """

    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    poll_msg_id = Column(BigInteger, nullable=False)
    enc_key = Column(LargeBinary, nullable=False)
    name = Column(String(255), nullable=True)

    account = relationship("Account", back_populates="polls")
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_polls_account_poll_msg", "account_id", "poll_msg_id", unique=True),
    )


class PollOption(Base):
    """
    Port of the `poll_option` table from LitePollStore.
    """

    __tablename__ = "poll_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True)

    option_name = Column(String(255), nullable=False)
    option_sha256 = Column(LargeBinary, nullable=False)

    poll = relationship("Poll", back_populates="options")

    __table_args__ = (
        Index("ix_poll_options_poll_sha", "poll_id", "option_sha256", unique=True),
    )


class AppStateKey(Base):
    """
    Port of the `app_state_keys` table from LiteAppStateStore.
    """

    __tablename__ = "app_state_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    key_id = Column(LargeBinary, nullable=False)
    key_data = Column(LargeBinary, nullable=False)
    fingerprint = Column(LargeBinary, nullable=True)
    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="app_state_keys")

    __table_args__ = (
        Index("ix_app_state_keys_account_key_id", "account_id", "key_id", unique=True),
    )


class Contact(Base):
    """
    Port of the `contact` table from LiteContactStore.
    """

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=True)
    jid = Column(String(255), nullable=False)
    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="contacts")

    __table_args__ = (
        Index("ix_contacts_account_jid", "account_id", "jid", unique=True),
    )


class Broadcast(Base):
    """
    Port of the `broadcast` table from LiteBroadcastStore.
    """

    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    sender = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    jids = Column(Text, nullable=False)  # Comma‑separated list (kept as is for compatibility)
    phash = Column(String(64), nullable=False)
    bcid = Column(String(255), nullable=False)

    account = relationship("Account", back_populates="broadcasts")

    __table_args__ = (
        Index("ix_broadcasts_account_bcid", "account_id", "bcid", unique=True),
        Index("ix_broadcasts_account_phash", "account_id", "phash", unique=True),
    )


class TrustedContact(Base):
    """
    Port of the `trusted_contact` table from LiteTrustedContactStore.
    """

    __tablename__ = "trusted_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    jid = Column(String(255), nullable=False)
    incoming_tc_token = Column(LargeBinary, nullable=False)
    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="trusted_contacts")

    __table_args__ = (
        Index("ix_trusted_contacts_account_jid", "account_id", "jid", unique=True),
    )


class ProfileConfig(Base):
    """
    Generic per‑account configuration blob.

    This replaces the previous \"config.json\" / \"config\" profile files and
    allows storing arbitrary named blobs (json or key‑val format) per account.
    """

    __tablename__ = "profile_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(128), nullable=False)  # e.g. \"config.json\"
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    account = relationship("Account")

    __table_args__ = (
        UniqueConstraint("account_id", "name", name="uq_profile_configs_account_name"),
    )


class SentMessage(Base):
    """
    Armazena o histórico de mensagens enviadas por cada conta.
    Usado para rastrear quantas mensagens foram enviadas e para quem.
    """

    __tablename__ = "sent_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    msg_id = Column(String(255), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)  # JID do destinatário (número ou grupo)
    message_type = Column(String(32), nullable=True)  # TEXT, IMAGE, VIDEO, AUDIO, DOCUMENT, etc.
    status = Column(String(32), nullable=False, default="EXECUTED")  # EXECUTED, SENT, ERROR
    error_code = Column(String(64), nullable=True)

    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    account = relationship("Account", back_populates="sent_messages")

    __table_args__ = (
        Index("ix_sent_messages_account_recipient", "account_id", "recipient"),
        Index("ix_sent_messages_account_created", "account_id", "created_at"),
    )




