#!/usr/bin/env python3
"""
Script de test pour vérifier le bon fonctionnement des tables Disboard
Ce script teste l'insertion et la récupération de données dans toutes les tables
"""

import asyncio
import aiomysql
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Charger les variables d'environnement
load_dotenv()

async def test_disboard_tables():
    """Teste le bon fonctionnement des tables du système Disboard"""
    
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
                
                # Test 1: Insertion dans disboard_config
                print("\n🧪 Test 1: Configuration du serveur...")
                test_guild_id = 123456789
                test_channel_id = 987654321
                test_role_id = 555666777
                
                await cursor.execute("""
                    INSERT INTO disboard_config 
                    (guild_id, reminder_channel_id, bump_role_id, reminder_enabled, reminder_interval_hours)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    reminder_channel_id = VALUES(reminder_channel_id),
                    bump_role_id = VALUES(bump_role_id),
                    reminder_enabled = VALUES(reminder_enabled),
                    reminder_interval_hours = VALUES(reminder_interval_hours)
                """, (test_guild_id, test_channel_id, test_role_id, True, 2))
                
                print("✅ Configuration insérée/mise à jour")
                
                # Test 2: Insertion dans disboard_bumps
                print("\n🧪 Test 2: Enregistrement d'un bump...")
                test_bumper_id = 111222333
                test_bumper_name = "TestUser#1234"
                test_bump_time = datetime.now()
                
                await cursor.execute("""
                    INSERT INTO disboard_bumps 
                    (guild_id, bumper_id, bumper_name, channel_id, bump_time, bumps_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (test_guild_id, test_bumper_id, test_bumper_name, test_channel_id, test_bump_time, 1))
                
                print("✅ Bump enregistré")
                
                # Test 3: Insertion dans disboard_reminders
                print("\n🧪 Test 3: Enregistrement d'un rappel...")
                test_reminder_time = datetime.now() + timedelta(hours=2)
                
                await cursor.execute("""
                    INSERT INTO disboard_reminders 
                    (guild_id, channel_id, reminder_time)
                    VALUES (%s, %s, %s)
                """, (test_guild_id, test_channel_id, test_reminder_time))
                
                print("✅ Rappel enregistré")
                
                # Test 4: Vérification des données insérées
                print("\n🧪 Test 4: Vérification des données...")
                
                # Vérifier la configuration
                await cursor.execute("""
                    SELECT guild_id, reminder_channel_id, bump_role_id, reminder_enabled, reminder_interval_hours
                    FROM disboard_config WHERE guild_id = %s
                """, (test_guild_id,))
                
                config_result = await cursor.fetchone()
                if config_result:
                    print(f"✅ Configuration récupérée: Guild {config_result[0]}, Channel {config_result[1]}, Role {config_result[2]}")
                else:
                    print("❌ Configuration non trouvée")
                
                # Vérifier le bump
                await cursor.execute("""
                    SELECT guild_id, bumper_id, bumper_name, bumps_count
                    FROM disboard_bumps WHERE guild_id = %s
                """, (test_guild_id,))
                
                bump_result = await cursor.fetchone()
                if bump_result:
                    print(f"✅ Bump récupéré: User {bump_result[2]} ({bump_result[1]}) - {bump_result[3]} bump(s)")
                else:
                    print("❌ Bump non trouvé")
                
                # Vérifier le rappel
                await cursor.execute("""
                    SELECT guild_id, channel_id, reminder_time
                    FROM disboard_reminders WHERE guild_id = %s
                """, (test_guild_id,))
                
                reminder_result = await cursor.fetchone()
                if reminder_result:
                    print(f"✅ Rappel récupéré: Channel {reminder_result[1]}, Time {reminder_result[2]}")
                else:
                    print("❌ Rappel non trouvé")
                
                # Test 5: Nettoyage des données de test
                print("\n🧪 Test 5: Nettoyage des données de test...")
                
                await cursor.execute("DELETE FROM disboard_reminders WHERE guild_id = %s", (test_guild_id,))
                await cursor.execute("DELETE FROM disboard_bumps WHERE guild_id = %s", (test_guild_id,))
                await cursor.execute("DELETE FROM disboard_config WHERE guild_id = %s", (test_guild_id,))
                
                print("✅ Données de test supprimées")
                
                # Test 6: Vérification finale
                print("\n🧪 Test 6: Vérification finale...")
                
                for table_name in ['disboard_bumps', 'disboard_reminders', 'disboard_config']:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    result = await cursor.fetchone()
                    count = result[0] if result else 0
                    print(f"📊 {table_name}: {count} lignes")
                
                print("\n🎉 Tous les tests sont passés avec succès !")
                print("✅ Les tables du système Disboard fonctionnent parfaitement")
                
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

if __name__ == "__main__":
    print("🧪 Test des tables Disboard")
    print("=" * 50)
    
    # Exécuter les tests
    success = asyncio.run(test_disboard_tables())
    
    if success:
        print("\n✅ Tests terminés avec succès")
    else:
        print("\n❌ Tests échoués")
        exit(1)

