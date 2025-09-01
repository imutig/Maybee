-- Migration: Ensure Disboard System Tables Exist
-- This migration ensures all required tables for the Disboard bump reminder system exist
-- It can be run multiple times safely (uses CREATE TABLE IF NOT EXISTS),

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

-- Ensure bump_role_id column exists (for backward compatibility)
-- This will add the column if it doesn't exist, or do nothing if it already exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'disboard_config' 
     AND COLUMN_NAME = 'bump_role_id') > 0,
    'SELECT "bump_role_id column already exists" as status',
    'ALTER TABLE disboard_config ADD COLUMN bump_role_id BIGINT DEFAULT NULL AFTER reminder_channel_id'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ensure bump_role_id index exists (for backward compatibility)
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'disboard_config' 
     AND INDEX_NAME = 'idx_bump_role_id') > 0,
    'SELECT "bump_role_id index already exists" as status',
    'CREATE INDEX idx_bump_role_id ON disboard_config(bump_role_id)'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Display status of all tables
SELECT 
    'disboard_bumps' as table_name,
    COUNT(*) as row_count,
    'OK' as status
FROM disboard_bumps
UNION ALL
SELECT 
    'disboard_reminders' as table_name,
    COUNT(*) as row_count,
    'OK' as status
FROM disboard_reminders
UNION ALL
SELECT 
    'disboard_config' as table_name,
    COUNT(*) as row_count,
    'OK' as status
FROM disboard_config;

