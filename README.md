# MaybeBot

🎮 **MaybeBot** est un bot Discord modulaire et avancé, conçu avec `discord.py` (v2) et `discord.app_commands`. Il propose de nombreuses fonctionnalités avec un système de base de données MySQL pour des performances optimales et une architecture évolutive. Bot développé par iMutig.

## 📦 Technologies & Architecture

- **Python 3.11+** avec support asyncio
- **discord.py 2.3+** pour l'API Discord
- **Base de données MySQL** avec aiomysql pour la persistance
- **Système modulaire** avec cogs pour une maintenance facile
- **Variables d'environnement** pour la sécurité
- **Interface utilisateur** avec boutons et modales Discord
- **Système de traduction** avec support multilingue (EN/FR)
- **Configuration centralisée** avec interface unifiée
- **Système de cache** avec persistance pour les performances
- **Système de modération** intégré

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
| `xp_config` | Configuration du système XP et canal d'annonces |
| `xp_history` | Historique des gains XP pour statistiques |
| `xp_multipliers` | Multiplicateurs XP par serveur |
| `level_roles` | Rôles attribués par niveau |
| `role_reactions` | Système de rôles par réaction |
| `user_languages` | Préférences linguistiques des utilisateurs |
| `guild_languages` | Préférences linguistiques des serveurs |
| `warnings` | Système d'avertissements de modération |
| `timeouts` | Historique des sanctions temporaires |

## ✨ Fonctionnalités principales

### 📈 **Système d'XP / Niveaux Avancé**
- **Gain d'XP intelligent**: Par message (anti-spam avec cooldown 10s) et vocal (automatique toutes les 10 min)
- **Multiplicateurs XP**: Configurables par serveur pour équilibrer les gains
- **Classements persistants**: `/topxp` (vocal, texte, total) avec cache pour performance
- **Statistiques détaillées**: `/xpstats` avec historique de gains et activité récente
- **Leaderboards temporels**: Classements hebdomadaires et mensuels
- **Rôles par niveau**: Attribution automatique via `/config`
- **Annonces de niveau**: Canal configurable pour les montées de niveau
- **Historique complet**: Suivi des gains XP avec source (message/vocal)

### 🛡️ **Système de Modération**
- **Avertissements**: `/warn` pour avertir les utilisateurs avec raison
- **Sanctions temporaires**: `/timeout` et `/untimeout` pour gérer les timeouts
- **Historique complet**: `/warnings` pour voir l'historique d'un utilisateur
- **Nettoyage**: `/clearwarnings` pour effacer les avertissements
- **Permissions**: Contrôle des permissions pour les modérateurs
- **Logs en base**: Traçabilité complète des actions de modération

### 🎭 **Système de Rôles**
- **Demandes de rôles**: `/role add` et `/role remove` pour demander des rôles
- **Système d'approbation**: Interface avec boutons pour les administrateurs
- **Configuration flexible**: Configuration via `/config` pour définir le canal des demandes
- **Statistiques**: `/rolestats` pour voir les demandes approuvées/refusées
- **Persistance**: Les boutons fonctionnent même après redémarrage du bot

### 🔄 **Système de Rôles par Réaction**
- Configuration interactive avec `/rolereact`
- Attribution automatique de rôles via réactions emoji
- Support multi-rôles par message
- Stockage en base de données pour la persistance

### 💬 **Système de Confessions**
- Confessions anonymes avec `/confession`
- Configuration du canal avec `/config`
- Statistiques des confessions avec `/confessionstats`
- Historique complet en base de données

### 👋 **Système de Bienvenue**
- Messages de bienvenue et d'au revoir personnalisables
- Configuration avec `/config` pour les messages et canaux
- Variables dynamiques: `{memberName}`, `{memberMention}`, `{serverName}`
- Embeds colorés avec avatars

### 🎫 **Système de Tickets**
- Création de tickets avec interface interactive
- Catégories automatiques
- Permissions personnalisées par ticket
- Fermeture automatique avec délai

### 📊 **Système de Cache Avancé**
- **Cache persistant**: Leaderboards sauvegardés sur disque
- **Cache temporaire**: Données fréquemment utilisées en mémoire
- **Statistiques**: `/cachestats` pour monitorer les performances
- **Gestion**: `/clearcache` pour nettoyer le cache
- **Persistance**: Survit aux redémarrages du bot

### 🌍 **Système de Traduction**
- **Support multilingue**: Anglais et Français
- **Préférences utilisateur**: Chaque utilisateur peut choisir sa langue
- **Préférences serveur**: Configuration de la langue par défaut du serveur
- **Interface traduite**: Tous les menus, boutons et messages sont traduits
- **Configuration via `/config`**: Changement de langue simple et rapide

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

### 👤 Commandes Utilisateur

| Commande | Description |
|----------|-------------|
| `/ping` | Affiche la latence du bot |
| `/avatar [user]` | Affiche l'avatar d'un utilisateur |
| `/level` | Voir son niveau et ses XP |
| `/topxp` | Classement XP du serveur (global, vocal, texte) |
| `/xpstats [user]` | Statistiques XP détaillées avec historique |
| `/roll` | Lance un dé (1-100) |
| `/confession <message>` | Envoie une confession anonyme |
| `/role add <role>` | Demande l'ajout d'un rôle |
| `/role remove <role>` | Demande la suppression d'un rôle |

### 🛠️ Commandes Administrateur

| Commande | Permission requise | Description |
|----------|-------------------|-------------|
| `/config` | Administrator | **Interface de configuration unifiée** |
| `/clear <number>` | Manage Messages | Supprime des messages |
| `/rename <user> <name>` | Manage Nicknames | Renomme un utilisateur |
| `/setup_ticket` | Administrator | Configure le système de tickets |

### 🛡️ Commandes de Modération

| Commande | Permission requise | Description |
|----------|-------------------|-------------|
| `/warn <user> <reason>` | Moderate Members | Avertit un utilisateur |
| `/timeout <user> <duration> <reason>` | Moderate Members | Sanctionne temporairement un utilisateur |
| `/untimeout <user>` | Moderate Members | Retire une sanction temporaire |
| `/warnings [user]` | Moderate Members | Affiche l'historique des avertissements |
| `/clearwarnings <user>` | Moderate Members | Efface les avertissements d'un utilisateur |

### 📊 Commandes Statistiques

| Commande | Permission requise | Description |
|----------|-------------------|-------------|
| `/confessionstats` | Manage Messages | Statistiques des confessions |
| `/rolestats` | Manage Roles | Statistiques des demandes de rôles |
| `/levelroles` | - | Liste des rôles par niveau |
| `/cachestats` | Administrator | Statistiques du cache système |
| `/clearcache` | Administrator | Vide le cache système |

### 🔄 Commandes XP Avancées

| Commande | Permission requise | Description |
|----------|-------------------|-------------|
| `/weeklyleaderboard` | - | Classement XP de la semaine |
| `/monthlyleaderboard` | - | Classement XP du mois |
| `/xpmultiplier <value>` | Administrator | Configure le multiplicateur XP |

**Note**: La commande `/config` remplace toutes les anciennes commandes de configuration individuelles (`/configwelcome`, `/configconfession`, `/configlevel`, etc.)

### 🔧 Configuration avec `/config`

La commande `/config` fournit une interface unifiée pour configurer tous les aspects du bot:

#### Systèmes configurables:
- **🎉 Système de Bienvenue**: Messages et canaux de bienvenue/au revoir
- **💬 Confessions**: Canal pour les confessions anonymes
- **🎭 Demandes de Rôles**: Canal pour les demandes de rôles
- **⚡ Rôles par Réaction**: Gestion des rôles par réaction (référence à `/rolereact`)
- **📊 Système XP**: Configuration du système XP, canal d'annonces et multiplicateurs
- **🎫 Système de Tickets**: Configuration des tickets de support
- **🌍 Langue**: Choix de la langue du serveur (Anglais/Français)

#### Fonctionnalités du système XP:
- **Activer/Désactiver** le système XP
- **Configurer le canal d'annonces** pour les montées de niveau
- **Gérer les multiplicateurs XP** pour équilibrer les gains
- **Visualisation** des paramètres actuels avec statistiques

#### Utilisation:
1. Tapez `/config`
2. Sélectionnez le système à configurer dans le menu déroulant
3. Utilisez les boutons pour effectuer les modifications
4. Toutes les modifications sont sauvegardées automatiquement

## 🔧 Améliorations & Nouvelles Fonctionnalités

### 🆕 Version 3.0 - Système Avancé & Modération

#### Nouvelles fonctionnalités majeures
- **Système de modération complet** avec avertissements et sanctions
- **XP System avancé** avec multiplicateurs et leaderboards temporels
- **Cache persistant** pour les performances et la persistance des données
- **Statistiques détaillées** pour tous les systèmes
- **Historique complet** des actions et gains XP

#### Améliorations du système XP
- **Multiplicateurs configurables** par serveur
- **Leaderboards hebdomadaires/mensuels** avec persistance
- **Statistiques détaillées** avec historique des gains
- **Cache persistant** pour les classements (survit aux redémarrages)
- **Suivi de l'activité** avec sources (message/vocal)

#### Système de modération
- **Avertissements** avec raisons et historique
- **Sanctions temporaires** (timeout/untimeout)
- **Traçabilité complète** des actions de modération
- **Permissions granulaires** pour les modérateurs
- **Interface intuitive** avec commandes slash

#### Système de cache avancé
- **Persistance sur disque** pour les données critiques
- **Cache temporaire** pour les performances
- **Statistiques de performance** détaillées
- **Gestion administrative** du cache
- **Optimisation automatique** des requêtes

### 🆕 Version 2.1 - Interface Unifiée & Traduction

#### Nouvelles fonctionnalités
- **Commande `/config` unifiée** pour toutes les configurations
- **Système de traduction multilingue** (Anglais/Français)
- **Configuration du canal d'annonces XP** via l'interface unifiée
- **Préférences linguistiques** par utilisateur et par serveur
- **Interface modernisée** avec menus déroulants et boutons

#### Améliorations techniques
- **Centralisation des configurations** en une seule commande
- **Traduction dynamique** des interfaces utilisateur
- **Persistance des préférences** linguistiques en base de données
- **Chargement automatique** des préférences au démarrage
- **Gestion améliorée** des erreurs de traduction

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
- **Préférences linguistiques**: Stockage des langues par utilisateur/serveur
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
- `Moderate Members` - Sanctions temporaires (timeout)
- `View Audit Log` - Consultation des logs de modération

### Sécurité des données

- **Chiffrement**: Variables d'environnement pour les données sensibles
- **Isolation**: Chaque serveur a ses propres données
- **Sauvegarde**: Base de données MySQL avec sauvegarde recommandée
- **Logs**: Système de logging pour audit et traçabilité
- **Cache sécurisé**: Persistance des données sensibles avec protection

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

4. **Problèmes de cache**
   - Utilisez `/cachestats` pour vérifier l'état du cache
   - Utilisez `/clearcache` pour nettoyer le cache si nécessaire
   - Vérifiez les permissions d'écriture dans le dossier `cache_data`

5. **Problèmes de modération**
   - Vérifiez que le bot a les permissions `Moderate Members`
   - Assurez-vous que le rôle du bot est au-dessus des utilisateurs à modérer
   - Consultez l'historique avec `/warnings` pour déboguer

### Support

- **GitHub Issues**: [Signaler un bug](https://github.com/imutig/MaybeBot/issues)
- **Discord**: Contactez iMutig#0000
- **Documentation**: Lisez les commentaires dans le code
- **Configuration**: Utilisez `/config` pour toutes les configurations

### Fonctionnalités récentes

- ✅ **Système de modération complet** avec avertissements et sanctions
- ✅ **XP System avancé** avec multiplicateurs et leaderboards temporels
- ✅ **Cache persistant** pour les performances optimales
- ✅ **Interface de configuration unifiée** avec `/config`
- ✅ **Système de traduction multilingue** (EN/FR)
- ✅ **Statistiques détaillées** pour tous les systèmes
- ✅ **Préférences linguistiques** persistantes

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

**Développé avec ❤️ par iMutig**

*MaybeBot - Votre compagnon Discord tout-en-un*