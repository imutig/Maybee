#!/usr/bin/env python3
"""
Migration script to convert YAML data to MySQL database
Run this script after setting up the database to migrate existing data
"""

import os
import yaml
import asyncio
import aiomysql
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': 3306,
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'db': os.getenv('DB_NAME')
}

async def migrate_welcome_data():
    """Migrate welcome.yaml data to database"""
    welcome_file = "config/welcome.yaml"
    if not os.path.exists(welcome_file):
        print("❌ Fichier welcome.yaml introuvable")
        return
    
    try:
        with open(welcome_file, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        if not data:
            print("ℹ️ Aucune donnée de bienvenue à migrer")
            return
            
        conn = await aiomysql.connect(**DB_CONFIG)
        cursor = await conn.cursor()
        
        for guild_id, config in data.items():
            guild_id = int(guild_id)
            welcome_channel = config.get('welcome_channel')
            welcome_message = config.get('welcome_message')
            goodbye_channel = config.get('goodbye_channel')
            goodbye_message = config.get('goodbye_message')
            
            await cursor.execute("""
                INSERT INTO welcome_config (guild_id, welcome_channel, welcome_message, goodbye_channel, goodbye_message)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                welcome_channel = VALUES(welcome_channel),
                welcome_message = VALUES(welcome_message),
                goodbye_channel = VALUES(goodbye_channel),
                goodbye_message = VALUES(goodbye_message)
            """, (guild_id, welcome_channel, welcome_message, goodbye_channel, goodbye_message))
        
        await conn.commit()
        await cursor.close()
        conn.close()
        
        print(f"✅ Migré {len(data)} configurations de bienvenue")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration des données de bienvenue: {e}")

async def migrate_confession_data():
    """Migrate confessions.yaml data to database"""
    confession_file = "data/confessions.yaml"
    if not os.path.exists(confession_file):
        print("❌ Fichier confessions.yaml introuvable")
        return
    
    try:
        with open(confession_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or []
        
        if not data:
            print("ℹ️ Aucune confession à migrer")
            return
            
        conn = await aiomysql.connect(**DB_CONFIG)
        cursor = await conn.cursor()
        
        # Note: We don't have guild_id in the old format, so we'll use 0 as default
        # You might want to manually set the correct guild_id for your server
        default_guild_id = 0
        
        for confession in data:
            username = confession.get('user', 'Anonymous')
            message = confession.get('confession', '')
            
            # Extract user ID from username if possible (format: username#discriminator)
            user_id = 0  # Default unknown user
            
            await cursor.execute("""
                INSERT INTO confessions (user_id, username, confession, guild_id)
                VALUES (%s, %s, %s, %s)
            """, (user_id, username, message, default_guild_id))
        
        await conn.commit()
        await cursor.close()
        conn.close()
        
        print(f"✅ Migré {len(data)} confessions")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration des confessions: {e}")

async def migrate_role_requests():
    """Migrate role_requests.yaml data to database"""
    role_file = "data/role_requests.yaml"
    if not os.path.exists(role_file):
        print("❌ Fichier role_requests.yaml introuvable")
        return
    
    try:
        with open(role_file, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        if not data:
            print("ℹ️ Aucune demande de rôle à migrer")
            return
            
        conn = await aiomysql.connect(**DB_CONFIG)
        cursor = await conn.cursor()
        
        # Note: We don't have guild_id in the old format, so we'll use 0 as default
        default_guild_id = 0
        
        for message_id, request in data.items():
            message_id = int(message_id)
            user_id = request.get('user_id', 0)
            role_id = request.get('role_id', 0)
            action = request.get('action', 'add')
            
            await cursor.execute("""
                INSERT INTO role_requests (message_id, user_id, role_id, action, guild_id, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                role_id = VALUES(role_id),
                action = VALUES(action)
            """, (message_id, user_id, role_id, action, default_guild_id, 'pending'))
        
        await conn.commit()
        await cursor.close()
        conn.close()
        
        print(f"✅ Migré {len(data)} demandes de rôles")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration des demandes de rôles: {e}")

async def main():
    """Main migration function"""
    print("🔄 Début de la migration des données YAML vers MySQL...")
    
    # Test database connection
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        conn.close()
        print("✅ Connexion à la base de données réussie")
    except Exception as e:
        print(f"❌ Impossible de se connecter à la base de données: {e}")
        return
    
    # Run migrations
    await migrate_welcome_data()
    await migrate_confession_data()
    await migrate_role_requests()
    
    print("✅ Migration terminée!")
    print("\nℹ️ Après la migration, vous pouvez sauvegarder puis supprimer les fichiers YAML:")
    print("- config/welcome.yaml")
    print("- data/confessions.yaml")
    print("- data/role_requests.yaml")

if __name__ == "__main__":
    asyncio.run(main())
