SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  phone VARCHAR(32) NOT NULL UNIQUE,
  pushname VARCHAR(255),
  env VARCHAR(32),
  is_logged_in TINYINT(1) NOT NULL DEFAULT 0,
  has_restriction TINYINT(1) NOT NULL DEFAULT 0,
  is_initialized TINYINT(1) NOT NULL DEFAULT 0,
  proxy_host VARCHAR(255),
  proxy_port INT,
  proxy_username VARCHAR(255),
  proxy_password VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_accounts_phone ON accounts(phone);
CREATE INDEX ix_accounts_is_logged_in ON accounts(is_logged_in);
CREATE INDEX ix_accounts_has_restriction ON accounts(has_restriction);
CREATE INDEX ix_accounts_is_initialized ON accounts(is_initialized);

CREATE TABLE identities (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  recipient_id BIGINT NOT NULL,
  recipient_type INT NOT NULL DEFAULT 0,
  device_id INT NOT NULL DEFAULT 0,
  registration_id INT NULL,
  public_key LONGBLOB,
  private_key LONGBLOB,
  next_prekey_id INT NULL,
  timestamp BIGINT NULL,
  CONSTRAINT fk_identities_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_identity_account_recipient_device ON identities(account_id, recipient_id, device_id);

CREATE TABLE prekeys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  prekey_id INT NOT NULL,
  sent_to_server TINYINT(1),
  record LONGBLOB NOT NULL,
  CONSTRAINT fk_prekeys_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_prekeys_account_prekey (account_id, prekey_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE signed_prekeys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  prekey_id INT NOT NULL,
  timestamp BIGINT NULL,
  record LONGBLOB NOT NULL,
  CONSTRAINT fk_signed_prekeys_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_signed_prekeys_account_prekey (account_id, prekey_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  recipient_id BIGINT NOT NULL,
  recipient_type INT NOT NULL DEFAULT 0,
  device_id INT NOT NULL,
  record LONGBLOB NOT NULL,
  timestamp BIGINT NULL,
  CONSTRAINT fk_sessions_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_sessions_account_recipient_device ON sessions(account_id, recipient_id, device_id);

CREATE TABLE sender_keys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  group_id VARCHAR(255) NOT NULL,
  sender_id VARCHAR(255) NOT NULL,
  record LONGBLOB NOT NULL,
  CONSTRAINT fk_sender_keys_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_sender_keys_account_group_sender ON sender_keys(account_id, group_id, sender_id);

CREATE TABLE polls (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  poll_msg_id BIGINT NOT NULL,
  enc_key LONGBLOB NOT NULL,
  name VARCHAR(255),
  CONSTRAINT fk_polls_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_polls_account_poll_msg ON polls(account_id, poll_msg_id);

CREATE TABLE poll_options (
  id INT AUTO_INCREMENT PRIMARY KEY,
  poll_id INT NOT NULL,
  option_name VARCHAR(255) NOT NULL,
  option_sha256 VARBINARY(255) NOT NULL,
  CONSTRAINT fk_poll_options_poll FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_poll_options_poll_sha ON poll_options(poll_id, option_sha256);

CREATE TABLE app_state_keys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  key_id VARBINARY(255) NOT NULL,
  key_data LONGBLOB NOT NULL,
  fingerprint LONGBLOB,
  timestamp BIGINT NOT NULL,
  CONSTRAINT fk_app_state_keys_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_app_state_keys_account_key_id ON app_state_keys(account_id, key_id);

CREATE TABLE contacts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  name VARCHAR(255),
  jid VARCHAR(255) NOT NULL,
  timestamp BIGINT NOT NULL,
  CONSTRAINT fk_contacts_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_contacts_account_jid ON contacts(account_id, jid);

CREATE TABLE broadcasts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  sender VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  jids TEXT NOT NULL,
  phash VARCHAR(64) NOT NULL,
  bcid VARCHAR(255) NOT NULL,
  CONSTRAINT fk_broadcasts_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_broadcasts_account_bcid ON broadcasts(account_id, bcid);
CREATE UNIQUE INDEX ix_broadcasts_account_phash ON broadcasts(account_id, phash);

CREATE TABLE trusted_contacts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  jid VARCHAR(255) NOT NULL,
  incoming_tc_token LONGBLOB NOT NULL,
  timestamp BIGINT NOT NULL,
  CONSTRAINT fk_trusted_contacts_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE UNIQUE INDEX ix_trusted_contacts_account_jid ON trusted_contacts(account_id, jid);

CREATE TABLE profile_configs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  name VARCHAR(128) NOT NULL,
  data LONGBLOB NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_profile_configs_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_profile_configs_account_name (account_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sent_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  msg_id VARCHAR(255) NOT NULL,
  recipient VARCHAR(255) NOT NULL,
  message_type VARCHAR(32),
  status VARCHAR(32) NOT NULL DEFAULT 'EXECUTED',
  error_code VARCHAR(64),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_sent_messages_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_sent_messages_account_recipient ON sent_messages(account_id, recipient);
CREATE INDEX ix_sent_messages_account_created ON sent_messages(account_id, created_at);
CREATE INDEX ix_sent_messages_msg_id ON sent_messages(msg_id);

SET FOREIGN_KEY_CHECKS = 1;