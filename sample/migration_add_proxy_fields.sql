-- Migração para adicionar campos de proxy à tabela accounts
-- Execute este script em bancos de dados existentes para adicionar suporte a proxy

-- SQLite
-- ALTER TABLE accounts ADD COLUMN proxy_host VARCHAR(255);
-- ALTER TABLE accounts ADD COLUMN proxy_port INTEGER;
-- ALTER TABLE accounts ADD COLUMN proxy_username VARCHAR(255);
-- ALTER TABLE accounts ADD COLUMN proxy_password VARCHAR(255);

-- MySQL
-- ALTER TABLE accounts ADD COLUMN proxy_host VARCHAR(255) AFTER is_initialized;
-- ALTER TABLE accounts ADD COLUMN proxy_port INT AFTER proxy_host;
-- ALTER TABLE accounts ADD COLUMN proxy_username VARCHAR(255) AFTER proxy_port;
-- ALTER TABLE accounts ADD COLUMN proxy_password VARCHAR(255) AFTER proxy_username;

-- PostgreSQL (se aplicável)
-- ALTER TABLE accounts ADD COLUMN proxy_host VARCHAR(255);
-- ALTER TABLE accounts ADD COLUMN proxy_port INTEGER;
-- ALTER TABLE accounts ADD COLUMN proxy_username VARCHAR(255);
-- ALTER TABLE accounts ADD COLUMN proxy_password VARCHAR(255);

-- Script de migração genérico
-- Este script pode ser executado em qualquer banco SQLAlchemy-supported

-- SQLite version
ALTER TABLE accounts ADD COLUMN proxy_host VARCHAR(255);
ALTER TABLE accounts ADD COLUMN proxy_port INTEGER;
ALTER TABLE accounts ADD COLUMN proxy_username VARCHAR(255);
ALTER TABLE accounts ADD COLUMN proxy_password VARCHAR(255);

-- MySQL version (uncomment if using MySQL)
-- ALTER TABLE accounts ADD COLUMN proxy_host VARCHAR(255) AFTER is_initialized;
-- ALTER TABLE accounts ADD COLUMN proxy_port INT AFTER proxy_host;
-- ALTER TABLE accounts ADD COLUMN proxy_username VARCHAR(255) AFTER proxy_port;
-- ALTER TABLE accounts ADD COLUMN proxy_password VARCHAR(255) AFTER proxy_username;

-- Verificação
-- SELECT phone, proxy_host, proxy_port, proxy_username FROM accounts WHERE proxy_host IS NOT NULL;
