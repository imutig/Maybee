#!/usr/bin/env python3
"""
Script pour vérifier et créer les tables du système Disboard
Ce script s'assure que toutes les tables nécessaires existent dans la base de données
"""

import asyncio
import aiomysql
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def ensure_disboard_tables():
    """Vérifie et crée les tables du système Disboard si elles n'existent pas"""
    
    # Configuration de la base de données
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASS', ''),
        'db': os.getenv('DB_NAME', 's1032881_Maybee'),
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    try:
        # Connexion à la base de données
        print("🔌 Connexion à la base de données...")
        pool = await aiomysql.create_pool(**db_config)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                print("✅ Connexion établie")
                
                # Vérifier et créer la table disboard_bumps
                print("\n📊 Vérification de la table disboard_bumps...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS disboard_bumps (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        bumper_id BIGINT NOT NULL,
                        bumper_name VARCHAR(255) NOT NULL,
                        channel_id BIGINT NOT NULL,
                        bump_time TIMESTAMP NOT NULL,
                        bumps_count INT DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_guild_id (guild_id),
                        INDEX idx_bumper_id (bumper_id),
                        INDEX idx_bump_time (bump_time),
                        INDEX idx_guild_bump_time (guild_id, bump_time)
                    )
                """)
                print("✅ Table disboard_bumps vérifiée/créée")
                
                # Vérifier et créer la table disboard_reminders
                print("\n📊 Vérification de la table disboard_reminders...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS disboard_reminders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        channel_id BIGINT NOT NULL,
                        reminder_time TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_guild_id (guild_id),
                        INDEX idx_reminder_time (reminder_time),
                        INDEX idx_guild_reminder_time (guild_id, reminder_time)
                    )
                """)
                print("✅ Table disboard_reminders vérifiée/créée")
                
                # Vérifier et créer la table disboard_config
                print("\n📊 Vérification de la table disboard_config...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS disboard_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL UNIQUE,
                        reminder_channel_id BIGINT DEFAULT NULL,
                        bump_role_id BIGINT DEFAULT NULL,
                        reminder_enabled BOOLEAN DEFAULT TRUE,
                        reminder_interval_hours INT DEFAULT 2,
                        bump_confirmation_enabled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_guild_id (guild_id)
                    )
                """)
                print("✅ Table disboard_config vérifiée/créée")
                
                # Vérifier si la colonne bump_role_id existe
                print("\n🔍 Vérification de la colonne bump_role_id...")
                await cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'disboard_config' 
                    AND COLUMN_NAME = 'bump_role_id'
                """, (db_config['db'],))
                
                result = await cursor.fetchone()
                if result[0] == 0:
                    print("➕ Ajout de la colonne bump_role_id...")
                    await cursor.execute("""
                        ALTER TABLE disboard_config 
                        ADD COLUMN bump_role_id BIGINT DEFAULT NULL AFTER reminder_channel_id
                    """)
                    print("✅ Colonne bump_role_id ajoutée")
                else:
                    print("✅ Colonne bump_role_id existe déjà")
                
                # Vérifier si l'index idx_bump_role_id existe
                print("\n🔍 Vérification de l'index idx_bump_role_id...")
                await cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'disboard_config' 
                    AND INDEX_NAME = 'idx_bump_role_id'
                """, (db_config['db'],))
                
                result = await cursor.fetchone()
                if result[0] == 0:
                    print("➕ Création de l'index idx_bump_role_id...")
                    await cursor.execute("""
                        CREATE INDEX idx_bump_role_id ON disboard_config(bump_role_id)
                    """)
                    print("✅ Index idx_bump_role_id créé")
                else:
                    print("✅ Index idx_bump_role_id existe déjà")
                
                # Afficher le statut des tables
                print("\n📋 Statut des tables du système Disboard:")
                print("-" * 50)
                
                for table_name in ['disboard_bumps', 'disboard_reminders', 'disboard_config']:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    result = await cursor.fetchone()
                    count = result[0] if result else 0
                    print(f"📊 {table_name}: {count} lignes")
                
                print("\n🎉 Toutes les tables du système Disboard sont prêtes !")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

if __name__ == "__main__":
    print("🚀 Script de vérification des tables Disboard")
    print("=" * 50)
    
    # Exécuter la vérification
    success = asyncio.run(ensure_disboard_tables())
    
    if success:
        print("\n✅ Script terminé avec succès")
    else:
        print("\n❌ Script terminé avec des erreurs")
        exit(1)
