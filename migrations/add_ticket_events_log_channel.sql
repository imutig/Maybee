-- Add ticket_events_log_channel_id column to server_config table
-- This column stores the channel ID where ticket events (create, claim, close, etc.) should be logged

ALTER TABLE server_config 
ADD COLUMN IF NOT EXISTS ticket_events_log_channel_id BIGINT DEFAULT NULL 
AFTER ticket_logs_channel_id;
