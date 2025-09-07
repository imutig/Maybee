-- Migration pour améliorer le système de logs serveur
-- Ajoute les nouveaux champs pour les logs de rôles et canaux

-- Ajouter les nouveaux champs à la table server_logs_config
ALTER TABLE server_logs_config 
ADD COLUMN IF NOT EXISTS log_role_create BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS log_role_delete BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS log_role_update BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS log_channel_update BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS log_voice_state_changes BOOLEAN DEFAULT TRUE;

-- Mettre à jour les configurations existantes pour activer les nouveaux logs
UPDATE server_logs_config 
SET log_role_create = TRUE,
    log_role_delete = TRUE,
    log_role_update = TRUE,
    log_channel_update = TRUE,
    log_voice_state_changes = TRUE
WHERE guild_id IS NOT NULL;
