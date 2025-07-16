-- Database schema for MaybeBot
-- Complete database schema with all tables required by the bot

-- Welcome configuration table
CREATE TABLE IF NOT EXISTS welcome_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    welcome_channel BIGINT DEFAULT NULL,
    welcome_message TEXT DEFAULT NULL,
    goodbye_channel BIGINT DEFAULT NULL,
    goodbye_message TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_guild (guild_id)
);

-- Role requests table
CREATE TABLE IF NOT EXISTS role_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    action ENUM('add', 'remove') NOT NULL DEFAULT 'add',
    status ENUM('pending', 'approved', 'denied') NOT NULL DEFAULT 'pending',
    guild_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);

-- Confessions table
CREATE TABLE IF NOT EXISTS confessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(255) NOT NULL,
    confession TEXT NOT NULL,
    guild_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_guild_id (guild_id)
);

-- Confession channels configuration
CREATE TABLE IF NOT EXISTS confession_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Role request channel configuration
CREATE TABLE IF NOT EXISTS role_request_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- XP System data table
CREATE TABLE IF NOT EXISTS xp_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    xp INT NOT NULL DEFAULT 0,
    level INT NOT NULL DEFAULT 1,
    text_xp INT NOT NULL DEFAULT 0,
    voice_xp INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_guild (user_id, guild_id),
    INDEX idx_user_id (user_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_xp (xp),
    INDEX idx_level (level)
);

-- XP System configuration table
CREATE TABLE IF NOT EXISTS xp_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    xp_channel BIGINT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Level roles table - roles awarded at specific levels
CREATE TABLE IF NOT EXISTS level_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    level INT NOT NULL,
    role_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_guild_level (guild_id, level),
    INDEX idx_guild_id (guild_id),
    INDEX idx_level (level)
);

-- Role reactions table - emoji role assignment system
CREATE TABLE IF NOT EXISTS role_reactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    emoji VARCHAR(255) NOT NULL,
    role_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_message_emoji (guild_id, message_id, emoji),
    INDEX idx_guild_id (guild_id),
    INDEX idx_message_id (message_id)
);
