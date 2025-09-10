-- Migration: Add comprehensive moderation history table
-- This table will store all moderation actions for better tracking and dashboard integration

CREATE TABLE IF NOT EXISTS moderation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    action_type ENUM('warn', 'timeout', 'kick', 'ban', 'unban', 'unmute') NOT NULL,
    reason TEXT,
    duration_minutes INT NULL, -- For timeout actions
    evidence_urls TEXT NULL, -- JSON array of evidence URLs
    channel_id BIGINT NULL, -- Channel where action was taken
    message_id BIGINT NULL, -- Message that triggered the action (if any)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL, -- For temporary actions like timeout/ban
    is_active BOOLEAN DEFAULT TRUE, -- For temporary actions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_user (guild_id, user_id),
    INDEX idx_moderator (moderator_id),
    INDEX idx_action_type (action_type),
    INDEX idx_timestamp (timestamp),
    INDEX idx_expires_at (expires_at),
    INDEX idx_is_active (is_active)
);

-- Migrate existing warnings data to moderation_history
INSERT INTO moderation_history (guild_id, user_id, moderator_id, action_type, reason, timestamp)
SELECT guild_id, user_id, moderator_id, 'warn', reason, timestamp
FROM warnings
WHERE NOT EXISTS (
    SELECT 1 FROM moderation_history mh 
    WHERE mh.guild_id = warnings.guild_id 
    AND mh.user_id = warnings.user_id 
    AND mh.moderator_id = warnings.moderator_id 
    AND mh.action_type = 'warn' 
    AND mh.timestamp = warnings.timestamp
);

-- Migrate existing timeouts data to moderation_history
INSERT INTO moderation_history (guild_id, user_id, moderator_id, action_type, reason, duration_minutes, timestamp)
SELECT guild_id, user_id, moderator_id, 'timeout', reason, duration, timestamp
FROM timeouts
WHERE NOT EXISTS (
    SELECT 1 FROM moderation_history mh 
    WHERE mh.guild_id = timeouts.guild_id 
    AND mh.user_id = timeouts.user_id 
    AND mh.moderator_id = timeouts.moderator_id 
    AND mh.action_type = 'timeout' 
    AND mh.timestamp = timeouts.timestamp
);
