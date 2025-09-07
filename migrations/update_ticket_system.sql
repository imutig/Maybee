-- Migration pour améliorer le système de tickets
-- Ajoute les nouveaux champs pour le système de logs et de fermeture amélioré

-- Ajouter les nouveaux champs à la table active_tickets
ALTER TABLE active_tickets 
ADD COLUMN IF NOT EXISTS status ENUM('open', 'closed', 'deleted') DEFAULT 'open',
ADD COLUMN IF NOT EXISTS closed_by BIGINT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP NULL,
ADD COLUMN IF NOT EXISTS reopened_by BIGINT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS reopened_at TIMESTAMP NULL;

-- Créer un index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_active_tickets_status ON active_tickets(status);
CREATE INDEX IF NOT EXISTS idx_active_tickets_user_guild ON active_tickets(user_id, guild_id);

-- Mettre à jour les tickets existants pour avoir le statut 'open'
UPDATE active_tickets SET status = 'open' WHERE status IS NULL;
