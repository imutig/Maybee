-- Migration pour ajouter les colonnes created_by et reason à la table active_tickets
-- Date: 2025-01-08

-- Ajouter la colonne created_by pour stocker l'ID de l'utilisateur qui a créé le ticket
ALTER TABLE active_tickets 
ADD COLUMN created_by BIGINT DEFAULT NULL AFTER user_id;

-- Ajouter la colonne reason pour stocker la raison de création du ticket
ALTER TABLE active_tickets 
ADD COLUMN reason TEXT DEFAULT NULL AFTER created_by;

-- Ajouter un index sur created_by pour les performances
ALTER TABLE active_tickets 
ADD INDEX idx_created_by (created_by);
