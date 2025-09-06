-- Migration pour ajouter le système de logs DM
-- Permet aux utilisateurs de recevoir des notifications DM quand leurs commandes sont utilisées

-- Table pour stocker les préférences de logs DM par utilisateur
CREATE TABLE IF NOT EXISTS dm_logs_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
);

-- Table pour stocker les commandes activées pour les logs DM par utilisateur
CREATE TABLE IF NOT EXISTS dm_logs_commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    command_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_command (user_id, command_name),
    INDEX idx_user_id (user_id),
    INDEX idx_command_name (command_name)
);

-- Table pour stocker l'historique des logs DM envoyés (pour éviter le spam)
CREATE TABLE IF NOT EXISTS dm_logs_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    command_name VARCHAR(100) NOT NULL,
    executor_id BIGINT NOT NULL,
    guild_id BIGINT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_executor_id (executor_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_executed_at (executed_at)
);
