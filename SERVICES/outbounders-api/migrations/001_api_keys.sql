-- Outbounders Agent API v0 — api_keys table
-- The ONLY new table this service introduces. Idempotent.
-- Run: mysql obapp_outbounders < 001_api_keys.sql

CREATE TABLE IF NOT EXISTS api_keys (
    id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    key_hash            CHAR(64)     NOT NULL COMMENT 'sha256 hex of the raw bearer key',
    client_user_id      INT UNSIGNED NOT NULL COMMENT 'main_users.user_id owning this key',
    scopes              VARCHAR(255) NOT NULL DEFAULT 'talent:read,jobs:read' COMMENT 'CSV, e.g. talent:read,jobs:read,jobs:write',
    rate_limit_per_hour INT UNSIGNED NOT NULL DEFAULT 300,
    created             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used           DATETIME     NULL,
    active              TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_api_keys_key_hash (key_hash),
    KEY idx_api_keys_client (client_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Minting a key (example — do NOT run as-is):
--
-- 1. Generate a raw key + its sha256 (the raw key is shown ONCE to the client):
--      python3 -c "import secrets,hashlib; k='ob_'+secrets.token_urlsafe(32); \
--        print('raw key :', k); print('sha256  :', hashlib.sha256(k.encode()).hexdigest())"
--
-- 2. Insert the HASH only (raw key is never stored):
--      -- INSERT INTO api_keys (key_hash, client_user_id, scopes, rate_limit_per_hour)
--      -- VALUES ('<sha256-hex-from-step-1>', 12345, 'talent:read,jobs:read,jobs:write', 300);
--
-- 3. Revoke: UPDATE api_keys SET active=0 WHERE id=<id>;
-- ---------------------------------------------------------------------------
