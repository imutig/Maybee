-- Migration: Add welcome and goodbye title fields
-- Date: 2025-07-19

-- Add welcome_title column if it doesn't exist
ALTER TABLE welcome_config 
ADD COLUMN IF NOT EXISTS welcome_title VARCHAR(256) DEFAULT '👋 New member!' 
AFTER welcome_channel;

-- Add goodbye_title column if it doesn't exist  
ALTER TABLE welcome_config 
ADD COLUMN IF NOT EXISTS goodbye_title VARCHAR(256) DEFAULT '👋 Departure' 
AFTER goodbye_channel;
