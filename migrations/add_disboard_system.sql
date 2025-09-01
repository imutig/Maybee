-- Migration: Add Disboard Bump Reminder System
-- This migration adds tables for tracking Disboard bumps and reminders

-- Table for tracking Disboard bumps
CREATE TABLE IF NOT EXISTS disboard_bumps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    bumper_id BIGINT NOT NULL,
    bumper_name VARCHAR(255) NOT NULL,
    channel_id BIGINT NOT NULL,
    bump_time TIMESTAMP NOT NULL,
    bumps_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id),
    INDEX idx_bumper_id (bumper_id),
    INDEX idx_bump_time (bump_time),
    INDEX idx_guild_bump_time (guild_id, bump_time)
);

-- Table for tracking bump reminders sent
CREATE TABLE IF NOT EXISTS disboard_reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    reminder_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id),
    INDEX idx_reminder_time (reminder_time),
    INDEX idx_guild_reminder_time (guild_id, reminder_time)
);

-- Table for server-specific Disboard configuration
CREATE TABLE IF NOT EXISTS disboard_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    reminder_channel_id BIGINT DEFAULT NULL,
    bump_role_id BIGINT DEFAULT NULL,
    reminder_enabled BOOLEAN DEFAULT TRUE,
    reminder_interval_hours INT DEFAULT 2,
    bump_confirmation_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id)
);

-- Insert default configuration for existing guilds (optional)
-- This can be run manually if needed
-- INSERT IGNORE INTO disboard_config (guild_id) 
-- SELECT DISTINCT guild_id FROM guild_config;
