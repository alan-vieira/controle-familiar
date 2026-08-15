CREATE TABLE IF NOT EXISTS token_blacklist (
    jti VARCHAR(36) PRIMARY KEY,
    revoked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires
    ON token_blacklist(expires_at);