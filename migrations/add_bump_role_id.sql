-- Migration: Add bump_role_id to disboard_config table
-- This migration adds the bump_role_id field to allow configuring which role gets pinged for reminders

-- Add bump_role_id column to disboard_config table
ALTER TABLE disboard_config 
ADD COLUMN bump_role_id BIGINT DEFAULT NULL AFTER reminder_channel_id;

-- Add index for better performance when querying by role
CREATE INDEX idx_bump_role_id ON disboard_config(bump_role_id);
