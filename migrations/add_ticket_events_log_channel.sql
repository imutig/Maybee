-- Add ticket_events_log_channel_id column to server_config table
-- This column stores the channel ID where ticket events (create, claim, close, etc.) should be logged

-- For MySQL/MariaDB, we need to check if column exists first
-- Using a procedure to handle IF NOT EXISTS logic

DELIMITER $$

CREATE PROCEDURE AddTicketEventsLogChannel()
BEGIN
    DECLARE column_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO column_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'server_config'
    AND COLUMN_NAME = 'ticket_events_log_channel_id';
    
    IF column_exists = 0 THEN
        ALTER TABLE server_config 
        ADD COLUMN ticket_events_log_channel_id BIGINT DEFAULT NULL 
        AFTER ticket_logs_channel_id;
    END IF;
END$$

DELIMITER ;

CALL AddTicketEventsLogChannel();
DROP PROCEDURE AddTicketEventsLogChannel;
