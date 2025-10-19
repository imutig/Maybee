# Mise à jour du système de recherche de tickets

## ✅ Modifications effectuées

### 1. Base de données
- ✅ Colonne `ticket_events_log_channel_id` ajoutée à la table `server_config`
- ✅ Scripts de migration et vérification créés

### 2. Backend (web/main.py)
- ✅ Fonction `search_guild_members()` modifiée pour chercher dans Google Drive
  - Recherche dans tous les tickets stockés sur Google Drive
  - Filtre par nom d'utilisateur ou ID utilisateur
  - Retourne le nombre de tickets par utilisateur
  - Fallback sur la base de données si Google Drive indisponible
  
- ✅ Nouvelle route `/api/guild/{guild_id}/tickets/recent` ajoutée
  - Récupère les 5 tickets les plus récents depuis Google Drive
  - Trie par date de création (décroissant)
  - Fallback sur la base de données si Google Drive indisponible
  - Retourne les infos complètes (user_id, username, dates, file_id, etc.)

### 3. Frontend (web/templates/dashboard.html)
- ✅ Nouvelle section "Tickets Récents" ajoutée après la recherche
  - Affichage des 5 derniers tickets
  - État de chargement avec spinner
  - État vide si aucun ticket
  - Réutilise le composant `ticket-item` existant

### 4. JavaScript (web/static/dashboard.js)
- ✅ Fonction `loadRecentTickets()` créée
  - Appelle l'API `/tickets/recent`
  - Gère les états de chargement et vide
  - Utilise `createTicketItem()` pour l'affichage
  - Se charge automatiquement lors de l'ouverture de l'onglet "Ticket Logs"

### 5. CSS (web/static/style.css)
- ✅ Style `.loading-state` ajouté
  - Spinner animé
  - Centrage vertical et horizontal
  - Animation de rotation

## 🎯 Fonctionnalités

### Recherche de tickets
- Tape un nom d'utilisateur ou ID dans le champ de recherche
- Suggestions en temps réel (autocomplete)
- Affiche tous les tickets de l'utilisateur trouvé
- **Source principale : Google Drive** (où sont stockés les transcripts)

### Tickets récents
- Affichage automatique des 5 derniers tickets créés
- Mise à jour lors de l'ouverture de l'onglet "Ticket Logs"
- Clique sur un ticket pour voir les détails (modal existant)

## 🔧 Configuration requise

### Variables d'environnement (Railway)
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

### Base de données
La colonne `ticket_events_log_channel_id` doit exister dans `server_config`.
✅ Déjà ajoutée via `add_column_fix.py`

## 📝 Tests à effectuer

1. ✅ Vérifier que la colonne existe dans la BDD
2. ⏳ Tester la recherche avec un utilisateur qui a des tickets sur Google Drive
3. ⏳ Vérifier que les 5 tickets récents s'affichent
4. ⏳ Tester le clic sur un ticket récent (ouverture de la modal)
5. ⏳ Vérifier le fallback si Google Drive indisponible

## 🚀 Déploiement

```bash
# Pousser sur Git
git add .
git commit -m "feat: Google Drive search + recent tickets display"
git push origin main

# Railway va automatiquement redéployer
```
