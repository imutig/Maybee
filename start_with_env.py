#!/usr/bin/env python3
"""
Script de démarrage avec configuration des variables d'environnement
"""

import os
import sys

# Configuration des variables d'environnement
os.environ['DISCORD_TOKEN'] = 'VOTRE_TOKEN_DISCORD_ICI'  # Remplacez par votre vrai token
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'u1032881_FHbKyeCStV'
os.environ['DB_PASS'] = 'VOTRE_MOT_DE_PASSE_DB_ICI'  # Remplacez par votre vrai mot de passe
os.environ['DB_NAME'] = 's1032881_Maybee'
os.environ['DEBUG'] = 'false'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['DEFAULT_LANGUAGE'] = 'fr'

# Import et lancement du bot
if __name__ == "__main__":
    try:
        from main import main
        import asyncio
        asyncio.run(main())
    except Exception as e:
        print(f"Erreur lors du démarrage: {e}")
        sys.exit(1)
