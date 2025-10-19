-- Add claimed_by column to active_tickets table
-- This column stores the user ID of the person who claimed a verification ticket

ALTER TABLE active_tickets 
ADD COLUMN IF NOT EXISTS claimed_by BIGINT DEFAULT NULL 
AFTER status;

-- Add an index for faster queries on claimed_by
ALTER TABLE active_tickets 
ADD INDEX IF NOT EXISTS idx_claimed_by (claimed_by);
