# Create database tables for web dashboard
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id BIGINT PRIMARY KEY,
    xp_enabled BOOLEAN DEFAULT TRUE,
    xp_multiplier DECIMAL(3,1) DEFAULT 1.0,
    level_up_message BOOLEAN DEFAULT TRUE,
    level_up_channel BIGINT NULL,
    moderation_enabled BOOLEAN DEFAULT TRUE,
    welcome_enabled BOOLEAN DEFAULT FALSE,
    welcome_channel BIGINT NULL,
    welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',
    logs_enabled BOOLEAN DEFAULT FALSE,
    logs_channel BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id)
);

# Add any missing columns to existing tables if needed
ALTER TABLE guild_config 
ADD COLUMN IF NOT EXISTS xp_text_min INT DEFAULT 15,
ADD COLUMN IF NOT EXISTS xp_text_max INT DEFAULT 25,
ADD COLUMN IF NOT EXISTS xp_voice_rate INT DEFAULT 15;
