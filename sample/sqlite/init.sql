PRAGMA foreign_keys = ON;

CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone VARCHAR(32) NOT NULL UNIQUE,
  pushname VARCHAR(255),
  env VARCHAR(32),
  is_logged_in BOOLEAN NOT NULL DEFAULT 0,
  has_restriction BOOLEAN NOT NULL DEFAULT 0,
  is_initialized BOOLEAN NOT NULL DEFAULT 0,
  proxy_host VARCHAR(255),
  proxy_port INTEGER,
  proxy_username VARCHAR(255),
  proxy_password VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_accounts_phone ON accounts(phone);
CREATE INDEX ix_accounts_is_logged_in ON accounts(is_logged_in);
CREATE INDEX ix_accounts_has_restriction ON accounts(has_restriction);
CREATE INDEX ix_accounts_is_initialized ON accounts(is_initialized);

CREATE TABLE identities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  recipient_id BIGINT NOT NULL,
  recipient_type INTEGER NOT NULL DEFAULT 0,
  device_id INTEGER NOT NULL DEFAULT 0,
  registration_id INTEGER,
  public_key BLOB,
  private_key BLOB,
  next_prekey_id INTEGER,
  timestamp BIGINT,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE INDEX ix_identity_account_recipient_device ON identities(account_id, recipient_id, device_id);

CREATE TABLE prekeys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  prekey_id INTEGER NOT NULL,
  sent_to_server BOOLEAN,
  record BLOB NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE(account_id, prekey_id)
);

CREATE TABLE signed_prekeys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  prekey_id INTEGER NOT NULL,
  timestamp BIGINT,
  record BLOB NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE(account_id, prekey_id)
);

CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  recipient_id BIGINT NOT NULL,
  recipient_type INTEGER NOT NULL DEFAULT 0,
  device_id INTEGER NOT NULL,
  record BLOB NOT NULL,
  timestamp BIGINT,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_sessions_account_recipient_device ON sessions(account_id, recipient_id, device_id);

CREATE TABLE sender_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  group_id VARCHAR(255) NOT NULL,
  sender_id VARCHAR(255) NOT NULL,
  record BLOB NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_sender_keys_account_group_sender ON sender_keys(account_id, group_id, sender_id);

CREATE TABLE polls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  poll_msg_id BIGINT NOT NULL,
  enc_key BLOB NOT NULL,
  name VARCHAR(255),
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_polls_account_poll_msg ON polls(account_id, poll_msg_id);

CREATE TABLE poll_options (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  poll_id INTEGER NOT NULL,
  option_name VARCHAR(255) NOT NULL,
  option_sha256 BLOB NOT NULL,
  FOREIGN KEY(poll_id) REFERENCES polls(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_poll_options_poll_sha ON poll_options(poll_id, option_sha256);

CREATE TABLE app_state_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  key_id BLOB NOT NULL,
  key_data BLOB NOT NULL,
  fingerprint BLOB,
  timestamp BIGINT NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_app_state_keys_account_key_id ON app_state_keys(account_id, key_id);

CREATE TABLE contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  name VARCHAR(255),
  jid VARCHAR(255) NOT NULL,
  timestamp BIGINT NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_contacts_account_jid ON contacts(account_id, jid);

CREATE TABLE broadcasts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  sender VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  jids TEXT NOT NULL,
  phash VARCHAR(64) NOT NULL,
  bcid VARCHAR(255) NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_broadcasts_account_bcid ON broadcasts(account_id, bcid);
CREATE UNIQUE INDEX ix_broadcasts_account_phash ON broadcasts(account_id, phash);

CREATE TABLE trusted_contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  jid VARCHAR(255) NOT NULL,
  incoming_tc_token BLOB NOT NULL,
  timestamp BIGINT NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_trusted_contacts_account_jid ON trusted_contacts(account_id, jid);

CREATE TABLE profile_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  name VARCHAR(128) NOT NULL,
  data BLOB NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE(account_id, name)
);

CREATE TABLE sent_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  msg_id VARCHAR(255) NOT NULL,
  recipient VARCHAR(255) NOT NULL,
  message_type VARCHAR(32),
  status VARCHAR(32) NOT NULL DEFAULT 'EXECUTED',
  error_code VARCHAR(64),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE INDEX ix_sent_messages_account_recipient ON sent_messages(account_id, recipient);
CREATE INDEX ix_sent_messages_account_created ON sent_messages(account_id, created_at);
CREATE INDEX ix_sent_messages_msg_id ON sent_messages(msg_id);