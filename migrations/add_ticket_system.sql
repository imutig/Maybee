-- Add ticket system configuration tables

-- Main ticket configuration table
CREATE TABLE IF NOT EXISTS ticket_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id VARCHAR(20) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id)
);

-- Ticket panel configuration table (embed messages with buttons)
CREATE TABLE IF NOT EXISTS ticket_panels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id VARCHAR(20) NOT NULL,
    panel_name VARCHAR(100) NOT NULL,
    channel_id VARCHAR(20),
    message_id VARCHAR(20),
    embed_title VARCHAR(256),
    embed_description TEXT,
    embed_color VARCHAR(7) DEFAULT '#5865F2',
    embed_thumbnail VARCHAR(512),
    embed_image VARCHAR(512),
    embed_footer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id),
    INDEX idx_channel_message (channel_id, message_id)
);

-- Ticket buttons configuration table (multiple buttons per panel)
CREATE TABLE IF NOT EXISTS ticket_buttons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    panel_id INT NOT NULL,
    button_label VARCHAR(80) NOT NULL,
    button_emoji VARCHAR(100),
    button_style ENUM('primary', 'secondary', 'success', 'danger') DEFAULT 'primary',
    category_id VARCHAR(20),
    ticket_name_format VARCHAR(100) DEFAULT 'ticket-{username}',
    ping_roles JSON,
    initial_message TEXT,
    button_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (panel_id) REFERENCES ticket_panels(id) ON DELETE CASCADE,
    INDEX idx_panel_id (panel_id)
);

-- Active tickets tracking table
CREATE TABLE IF NOT EXISTS active_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id VARCHAR(20) NOT NULL,
    channel_id VARCHAR(20) NOT NULL UNIQUE,
    user_id VARCHAR(20) NOT NULL,
    button_id INT,
    panel_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL,
    closed_by VARCHAR(20),
    FOREIGN KEY (button_id) REFERENCES ticket_buttons(id) ON DELETE SET NULL,
    FOREIGN KEY (panel_id) REFERENCES ticket_panels(id) ON DELETE SET NULL,
    INDEX idx_guild_id (guild_id),
    INDEX idx_user_id (user_id),
    INDEX idx_channel_id (channel_id)
);
