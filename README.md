# MaybeBot

🎮 **MaybeBot** est un bot Discord multifonction, modulaire, conçu avec `discord.py` (v2) et `discord.app_commands`. Il propose plusieurs fonctions, listées ci-dessous. Bot développé par iMutig.

## ✨ Fonctionnalités principales

- 📈 **Système d'XP / Niveaux**
  - Gain d'XP par message (anti-spam intégré avec cooldown)
  - Gain d'XP vocal
  - Commande `/level` pour voir son niveau et son montant d'XP
  - Classement `/topxp` par serveur, pour la catégorie vocal, texte et totale.
  - Configuration de rôles débloqués à certains niveaux (avec `/configlevel`)


- ⚙️ **Commandes utilitaires**
  - `/ping`, `/avatar`, `/roll`, etc.

## 📦 Technologies

- Python 3.10+
- discord.py 2.3+
- Base de données MySQL (gestion de l’XP, des rôles, et des configs)
- Système modulaire avec `cogs`

## 🔐 Configuration & Sécurité

Certaines informations sensibles (token, identifiants SQL, etc.) doivent être placées dans un fichier `.env`. Exemple :

```env
DISCORD_TOKEN=your_token_here
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```