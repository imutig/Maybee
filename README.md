# MaybeBot

🎮 **MaybeBot** est un bot Discord multifon## 📦 Technologies & Architecture

- **Python 3.11+** avec support asyncio
- **discord.py 2.3+** pour l'API Discord
- **Base de données MySQL** avec aiomysql pour la persistance
- **Système modulaire** avec cogs pour une maintenance facile
- **Variables d'environnement** pour la sécurité
- **Interface utilisateur** avec boutons et modales Discord

## 🗄️ Structure de la Base de Données

Le bot utilise une architecture MySQL complète avec les tables suivantes:

| Table | Description |
|-------|-------------|
| `welcome_config` | Configuration des messages de bienvenue/au revoir |
| `role_requests` | Demandes de rôles avec statuts |
| `role_request_config` | Configuration des canaux de demandes |
| `confessions` | Stockage des confessions anonymes |
| `confession_config` | Configuration des canaux de confessions |
| `xp_data` | Données XP et niveaux des utilisateurs |
| `xp_config` | Configuration du système XP |
| `level_roles` | Rôles attribués par niveau |
| `role_reactions` | Système de rôles par réaction | modulaire, conçu avec `discord.py` (v2) et `discord.app_commands`. Il propose plusieurs fonctions avancées avec un système de base de données MySQL pour des performances optimales. Bot développé par iMutig.

## ✨ Fonctionnalités principales

### 📈 **Système d'XP / Niveaux**
- Gain d'XP par message (anti-spam intégré avec cooldown de 10 secondes)
- Gain d'XP vocal automatique toutes les 10 minutes
- Commande `/level` pour voir son niveau et son montant d'XP
- Classement `/topxp` par serveur (vocal, texte et total)
- Configuration de rôles débloqués à certains niveaux avec `/configlevel`
- Système d'annonces de niveau avec canal configurable
- Commande `/levelroles` pour voir les rôles par niveau

### 🎭 **Système de Rôles**
- **Demandes de rôles**: `/role add` et `/role remove` pour demander des rôles
- **Système d'approbation**: Interface avec boutons pour les administrateurs
- **Configuration flexible**: `/configrolechannel` pour définir le canal des demandes
- **Statistiques**: `/rolestats` pour voir les demandes approuvées/refusées
- **Persistance**: Les boutons fonctionnent même après redémarrage du bot

### 🔄 **Système de Rôles par Réaction**
- Configuration interactive avec `/rolereact`
- Attribution automatique de rôles via réactions emoji
- Support multi-rôles par message
- Stockage en base de données pour la persistance

### 💬 **Système de Confessions**
- Confessions anonymes avec `/confession`
- Configuration du canal avec `/configconfession`
- Statistiques des confessions avec `/confessionstats`
- Historique complet en base de données

### 👋 **Système de Bienvenue**
- Messages de bienvenue et d'au revoir personnalisables
- Configuration avec `/configwelcome` et `/configgoodbye`
- Variables dynamiques: `{memberName}`, `{memberMention}`, `{serverName}`
- Embeds colorés avec avatars

### 🎫 **Système de Tickets**
- Création de tickets avec interface interactive
- Catégories automatiques
- Permissions personnalisées par ticket
- Fermeture automatique avec délai

### ⚙️ **Commandes Utilitaires**
- `/ping` - Latence du bot
- `/avatar` - Afficher l'avatar d'un utilisateur
- `/roll` - Dé virtuel (1-100)
- `/scan` - Informations détaillées sur un membre
- `/clear` - Suppression de messages (modérateurs)
- `/rename` - Renommer un membre
- `/embed` - Créer des embeds personnalisés
- `/meeting` - Organiser des réunions
- `/career` - Décisions de carrière (promotions, sanctions)

## 📦 Technologies

- Python 3.10+
- discord.py 2.3+
- Base de données MySQL (gestion de l’XP, des rôles, et des configs)
- Système modulaire avec `cogs`

## 🔐 Configuration & Sécurité

Le bot utilise des variables d'environnement pour protéger les informations sensibles.

### Configuration requise

1. **Créez un fichier `.env`** à la racine du projet
2. **Ajoutez les variables suivantes**:

```env
# Token Discord Bot
DISCORD_TOKEN=your_discord_bot_token_here

# Configuration MySQL
DB_HOST=localhost
DB_USER=your_db_username
DB_PASS=your_db_password
DB_NAME=your_db_name
```

### Prérequis MySQL

1. **Serveur MySQL** (local ou distant)
2. **Base de données créée** (le bot créera les tables automatiquement)
3. **Utilisateur MySQL** avec privilèges CREATE, SELECT, INSERT, UPDATE, DELETE

## 🚀 Installation & Démarrage

### 1. Clonage et dépendances

```bash
git clone https://github.com/imutig/MaybeBot.git
cd MaybeBot
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copiez le fichier d'exemple
cp .env.example .env

# Éditez le fichier .env avec vos informations
nano .env
```

### 3. Lancement

```bash
python main.py
```

Le bot va automatiquement:
- ✅ Se connecter à Discord
- ✅ Initialiser la base de données
- ✅ Créer toutes les tables nécessaires
- ✅ Charger tous les modules (cogs)
- ✅ Synchroniser les commandes slash

## 🗄️ Migration des données YAML vers MySQL

**Important**: Ce bot utilise maintenant MySQL au lieu de fichiers YAML pour stocker les données. 

### Migration automatique

Si vous avez des données YAML existantes, utilisez le script de migration:

```bash
# Assurez-vous que la base de données est configurée
python migrate_yaml_to_db.py
```

### Fichiers supportés pour la migration

- `config/welcome.yaml` → `welcome_config`
- `data/confessions.yaml` → `confessions`
- `data/role_requests.yaml` → `role_requests`

### Après migration

```bash
# Sauvegardez les fichiers YAML (optionnel)
mkdir backup
mv config/welcome.yaml backup/
mv data/confessions.yaml backup/
mv data/role_requests.yaml backup/

# Ou supprimez-les directement
rm config/welcome.yaml data/confessions.yaml data/role_requests.yaml
```

## 🎯 Commandes Disponibles

### � Commandes Utilisateur

| Commande | Description |
|----------|-------------|
| `/ping` | Affiche la latence du bot |
| `/avatar [user]` | Affiche l'avatar d'un utilisateur |
| `/level` | Voir son niveau et ses XP |
| `/topxp` | Classement XP du serveur |
| `/roll` | Lance un dé (1-100) |
| `/confession <message>` | Envoie une confession anonyme |
| `/role add <role>` | Demande l'ajout d'un rôle |
| `/role remove <role>` | Demande la suppression d'un rôle |

### 🛠️ Commandes Administrateur

| Commande | Permission requise | Description |
|----------|-------------------|-------------|
| `/configwelcome` | Manage Channels | Configure les messages de bienvenue |
| `/configgoodbye` | Manage Channels | Configure les messages d'au revoir |
| `/configconfession` | Manage Channels | Configure le canal de confessions |
| `/configrolechannel` | Manage Channels | Configure le canal des demandes de rôles |
| `/configlevel` | Manage Roles | Configure le système XP et rôles |
| `/rolereact` | Administrator | Configure les rôles par réaction |
| `/setup_ticket` | Administrator | Configure le système de tickets |
| `/clear <number>` | Manage Messages | Supprime des messages |
| `/rename <user> <name>` | Manage Nicknames | Renomme un utilisateur |

### 📊 Commandes Statistiques

| Commande | Permission requise | Description |
|----------|-------------------|-------------|
| `/confessionstats` | Manage Messages | Statistiques des confessions |
| `/rolestats` | Manage Roles | Statistiques des demandes de rôles |
| `/levelroles` | - | Liste des rôles par niveau |

## 🔧 Améliorations & Nouvelles Fonctionnalités

### 🆕 Version 2.0 - Migration MySQL

#### Nouvelles fonctionnalités
- **Système de rôles par demande** avec approbation administrative
- **Confessions anonymes** avec statistiques
- **Système de rôles par réaction** interactif
- **Configuration flexible** pour tous les modules
- **Persistance complète** des données
- **Interface utilisateur moderne** avec boutons Discord

#### Améliorations techniques
- **Base de données MySQL** pour des performances optimales
- **Architecture modulaire** améliorée
- **Gestion d'erreurs** renforcée
- **Logging complet** pour le débogage
- **Support multi-serveurs** natif

#### Migration YAML → MySQL
- **Système de bienvenue**: Configuration stockée en base
- **Confessions**: Historique complet avec statistiques
- **Demandes de rôles**: Suivi des statuts et approbations
- **Performances**: Accès plus rapide aux données
- **Scalabilité**: Support illimité de serveurs

## 🛡️ Sécurité & Permissions

### Permissions Discord requises

Le bot nécessite les permissions suivantes:
- `Send Messages` - Envoi de messages
- `Embed Links` - Création d'embeds
- `Manage Messages` - Suppression de messages (clear)
- `Manage Roles` - Gestion des rôles
- `Manage Nicknames` - Changement de pseudos
- `Add Reactions` - Ajout de réactions
- `Read Message History` - Lecture de l'historique

### Sécurité des données

- **Chiffrement**: Variables d'environnement pour les données sensibles
- **Isolation**: Chaque serveur a ses propres données
- **Sauvegarde**: Base de données MySQL avec sauvegarde recommandée
- **Logs**: Système de logging pour audit

## 🐛 Dépannage

### Problèmes courants

1. **Bot ne démarre pas**
   ```bash
   # Vérifiez les variables d'environnement
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Token:', bool(os.getenv('DISCORD_TOKEN')))"
   ```

2. **Erreur de base de données**
   ```bash
   # Testez la connexion MySQL
   mysql -h localhost -u your_user -p your_database
   ```

3. **Commandes slash non synchronisées**
   - Attendez jusqu'à 1 heure (cache Discord)
   - Redémarrez le bot
   - Vérifiez les permissions du bot

### Support

- **GitHub Issues**: [Signaler un bug](https://github.com/imutig/MaybeBot/issues)
- **Discord**: Contactez iMutig#0000
- **Documentation**: Lisez les commentaires dans le code

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

**Développé avec ❤️ par iMutig**

*MaybeBot - Votre compagnon Discord tout-en-un*