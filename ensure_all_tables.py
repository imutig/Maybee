#!/usr/bin/env python3
"""
Script pour vérifier et créer TOUTES les tables nécessaires au bot Maybee
Ce script s'assure que toutes les tables requises existent dans la base de données
"""

import asyncio
import aiomysql
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def ensure_all_tables():
    """Vérifie et crée toutes les tables nécessaires au bot"""
    
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
                
                # ============================================================================
                # TABLES DE BASE DU BOT
                # ============================================================================
                
                print("\n📊 Vérification des tables de base du bot...")
                
                # 1. Table guild_config (ESSENTIELLE)
                print("\n🔧 Vérification de la table guild_config...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS guild_config (
                        guild_id BIGINT PRIMARY KEY,
                        xp_enabled BOOLEAN DEFAULT TRUE,
                        xp_multiplier DECIMAL(3,1) DEFAULT 1.0,
                        level_up_message BOOLEAN DEFAULT TRUE,
                        level_up_channel BIGINT NULL,
                        moderation_enabled BOOLEAN DEFAULT TRUE,
                        welcome_enabled BOOLEAN DEFAULT FALSE,
                        welcome_channel BIGINT NULL,
                        welcome_message TEXT,
                        logs_enabled BOOLEAN DEFAULT FALSE,
                        logs_channel BIGINT NULL,
                        auto_role_enabled BOOLEAN DEFAULT FALSE,
                        auto_role_ids JSON DEFAULT NULL,
                        xp_text_min INT DEFAULT 15,
                        xp_text_max INT DEFAULT 25,
                        xp_voice_rate INT DEFAULT 15,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_guild_id (guild_id)
                    )
                """)
                print("✅ Table guild_config vérifiée/créée")
                
                # 2. Table welcome_config
                print("\n🔧 Vérification de la table welcome_config...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS welcome_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        welcome_channel BIGINT DEFAULT NULL,
                        welcome_title VARCHAR(256) DEFAULT '👋 New member!',
                        welcome_message TEXT DEFAULT NULL,
                        goodbye_channel BIGINT DEFAULT NULL,
                        goodbye_title VARCHAR(256) DEFAULT '👋 Departure',
                        goodbye_message TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_guild (guild_id)
                    )
                """)
                print("✅ Table welcome_config vérifiée/créée")
                
                # 3. Table role_requests
                print("\n🔧 Vérification de la table role_requests...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS role_requests (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        message_id BIGINT NOT NULL UNIQUE,
                        user_id BIGINT NOT NULL,
                        role_id BIGINT NOT NULL,
                        action ENUM('add', 'remove') NOT NULL DEFAULT 'add',
                        status ENUM('pending', 'approved', 'denied') NOT NULL DEFAULT 'pending',
                        guild_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_message_id (message_id),
                        INDEX idx_user_id (user_id),
                        INDEX idx_status (status)
                    )
                """)
                print("✅ Table role_requests vérifiée/créée")
                
                # 4. Table confessions
                print("\n🔧 Vérification de la table confessions...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS confessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username VARCHAR(255) NOT NULL,
                        confession TEXT NOT NULL,
                        guild_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        INDEX idx_guild_id (guild_id)
                    )
                """)
                print("✅ Table confessions vérifiée/créée")
                
                # 5. Table confession_config
                print("\n🔧 Vérification de la table confession_config...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS confession_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL UNIQUE,
                        channel_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                print("✅ Table confession_config vérifiée/créée")
                
                # 6. Table role_request_config
                print("\n🔧 Vérification de la table role_request_config...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS role_request_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL UNIQUE,
                        channel_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                print("✅ Table role_request_config vérifiée/créée")
                
                # ============================================================================
                # SYSTÈME XP
                # ============================================================================
                
                print("\n📊 Vérification des tables du système XP...")
                
                # 7. Table xp_data
                print("\n🔧 Vérification de la table xp_data...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS xp_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        guild_id BIGINT NOT NULL,
                        xp INT NOT NULL DEFAULT 0,
                        level INT NOT NULL DEFAULT 1,
                        text_xp INT NOT NULL DEFAULT 0,
                        voice_xp INT NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_user_guild (user_id, guild_id),
                        INDEX idx_user_id (user_id),
                        INDEX idx_guild_id (guild_id),
                        INDEX idx_xp (xp),
                        INDEX idx_level (level)
                    )
                """)
                print("✅ Table xp_data vérifiée/créée")
                
                # 8. Table xp_config
                print("\n🔧 Vérification de la table xp_config...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS xp_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL UNIQUE,
                        xp_channel BIGINT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                print("✅ Table xp_config vérifiée/créée")
                
                # 9. Table xp_history
                print("\n🔧 Vérification de la table xp_history...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS xp_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        guild_id BIGINT NOT NULL,
                        xp_gained INT NOT NULL,
                        xp_type ENUM('text', 'voice') NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_guild (user_id, guild_id),
                        INDEX idx_timestamp (timestamp),
                        INDEX idx_guild_time (guild_id, timestamp)
                    )
                """)
                print("✅ Table xp_history vérifiée/créée")
                
                # 10. Table level_roles
                print("\n🔧 Vérification de la table level_roles...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS level_roles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        level INT NOT NULL,
                        role_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_guild_level (guild_id, level),
                        INDEX idx_guild_id (guild_id),
                        INDEX idx_level (level)
                    )
                """)
                print("✅ Table level_roles vérifiée/créée")
                
                # ============================================================================
                # SYSTÈME DE RÔLES ET MODÉRATION
                # ============================================================================
                
                print("\n📊 Vérification des tables de rôles et modération...")
                
                # 11. Table role_reactions
                print("\n🔧 Vérification de la table role_reactions...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS role_reactions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        message_id BIGINT NOT NULL,
                        emoji VARCHAR(255) NOT NULL,
                        role_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_message_emoji (guild_id, message_id, emoji),
                        INDEX idx_guild_id (guild_id),
                        INDEX idx_message_id (message_id)
                    )
                """)
                print("✅ Table role_reactions vérifiée/créée")
                
                # 12. Table warnings
                print("\n🔧 Vérification de la table warnings...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS warnings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        moderator_id BIGINT NOT NULL,
                        reason TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_guild_user (guild_id, user_id),
                        INDEX idx_moderator (moderator_id),
                        INDEX idx_timestamp (timestamp)
                    )
                """)
                print("✅ Table warnings vérifiée/créée")
                
                # 13. Table timeouts
                print("\n🔧 Vérification de la table timeouts...")
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS timeouts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        moderator_id BIGINT NOT NULL,
                        duration INT NOT NULL,
                        reason TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_guild_user (guild_id, user_id),
                        INDEX idx_moderator (moderator_id),
                        INDEX idx_timestamp (timestamp)
                    )
                """)
                print("✅ Table timeouts vérifiée/créée")
                
                # ============================================================================
                # SYSTÈME DISBOARD
                # ============================================================================
                
                print("\n📊 Vérification des tables du système Disboard...")
                
                # 14. Table disboard_bumps
                print("\n🔧 Vérification de la table disboard_bumps...")
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
                
                # 15. Table disboard_reminders
                print("\n🔧 Vérification de la table disboard_reminders...")
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
                
                # 16. Table disboard_config
                print("\n🔧 Vérification de la table disboard_config...")
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
                
                # ============================================================================
                # VÉRIFICATION DES COLONNES MANQUANTES
                # ============================================================================
                
                print("\n🔍 Vérification des colonnes manquantes...")
                
                # Vérifier si la colonne bump_role_id existe dans disboard_config
                await cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'disboard_config' 
                    AND COLUMN_NAME = 'bump_role_id'
                """, (db_config['db'],))
                
                result = await cursor.fetchone()
                if result and result[0] == 0:
                    print("➕ Ajout de la colonne bump_role_id...")
                    await cursor.execute("""
                        ALTER TABLE disboard_config 
                        ADD COLUMN bump_role_id BIGINT DEFAULT NULL AFTER reminder_channel_id
                    """)
                    print("✅ Colonne bump_role_id ajoutée")
                else:
                    print("✅ Colonne bump_role_id existe déjà")
                
                # Vérifier si l'index idx_bump_role_id existe
                await cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'disboard_config' 
                    AND INDEX_NAME = 'idx_bump_role_id'
                """, (db_config['db'],))
                
                result = await cursor.fetchone()
                if result and result[0] == 0:
                    print("➕ Création de l'index idx_bump_role_id...")
                    await cursor.execute("""
                        CREATE INDEX idx_bump_role_id ON disboard_config(bump_role_id)
                    """)
                    print("✅ Index idx_bump_role_id créé")
                else:
                    print("✅ Index idx_bump_role_id existe déjà")
                
                # ============================================================================
                # STATUT FINAL
                # ============================================================================
                
                print("\n📋 Statut final de toutes les tables:")
                print("-" * 60)
                
                all_tables = [
                    'guild_config', 'welcome_config', 'role_requests', 'confessions',
                    'confession_config', 'role_request_config', 'xp_data', 'xp_config',
                    'xp_history', 'level_roles', 'role_reactions', 'warnings',
                    'timeouts', 'disboard_bumps', 'disboard_reminders', 'disboard_config'
                ]
                
                total_tables = len(all_tables)
                existing_tables = 0
                
                for table_name in all_tables:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    result = await cursor.fetchone()
                    count = result[0] if result else 0
                    print(f"📊 {table_name}: {count} lignes")
                    existing_tables += 1
                
                print(f"\n🎉 Toutes les {total_tables} tables sont prêtes !")
                print("✅ Le bot Maybee est maintenant entièrement configuré")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

if __name__ == "__main__":
    print("🚀 Script de vérification complète des tables Maybee")
    print("=" * 60)
    
    # Exécuter la vérification
    success = asyncio.run(ensure_all_tables())
    
    if success:
        print("\n✅ Script terminé avec succès")
    else:
        print("\n❌ Script terminé avec des erreurs")
        exit(1)
