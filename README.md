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

Certaines informations sensibles (token, identifiants SQL, etc.) doivent être placées dans un fichier `.env`. 

1. Copiez le fichier `.env.example` vers `.env`
2. Complétez les informations :

```env
DISCORD_TOKEN=your_discord_bot_token_here
DB_HOST=localhost
DB_USER=your_db_username
DB_PASS=your_db_password
DB_NAME=your_db_name
```

## 🚀 Installation

1. Clonez le repository
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Configurez le fichier `.env` (voir section Configuration)
4. Lancez le bot :
   ```bash
   python main.py
   ```