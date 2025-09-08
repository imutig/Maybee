-- Migration pour créer la table server_config
-- Date: 2025-01-08

CREATE TABLE IF NOT EXISTS server_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    ticket_category_id BIGINT DEFAULT NULL,
    ticket_logs_channel_id BIGINT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id)
);
