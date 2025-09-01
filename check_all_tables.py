#!/usr/bin/env python3
"""
Script de vérification générale de toutes les tables du bot Maybee
Ce script vérifie l'état de toutes les tables nécessaires au bon fonctionnement du bot
"""

import asyncio
import aiomysql
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def check_all_tables():
    """Vérifie l'état de toutes les tables du bot Maybee"""
    
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
                
                # Liste de toutes les tables requises
                all_tables = [
                    # Tables de base du bot
                    'guild_config',
                    'welcome_config', 
                    'role_requests',
                    'confessions',
                    'confession_config',
                    'role_request_config',
                    
                    # Système XP
                    'xp_data',
                    'xp_config',
                    'xp_history',
                    'level_roles',
                    
                    # Système de rôles et modération
                    'role_reactions',
                    'warnings',
                    'timeouts',
                    
                    # Système Disboard
                    'disboard_bumps',
                    'disboard_reminders',
                    'disboard_config'
                ]
                
                print(f"\n🔍 Vérification de {len(all_tables)} tables...")
                
                existing_tables = []
                missing_tables = []
                
                # Vérifier l'existence de chaque table
                for table_name in all_tables:
                    await cursor.execute("""
                        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    """, (db_config['db'], table_name))
                    
                    result = await cursor.fetchone()
                    if result and result[0] > 0:
                        existing_tables.append(table_name)
                    else:
                        missing_tables.append(table_name)
                
                # Afficher le statut des tables
                print("\n📋 Statut général des tables:")
                print("-" * 60)
                
                if existing_tables:
                    print("✅ Tables existantes:")
                    for table_name in existing_tables:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        result = await cursor.fetchone()
                        count = result[0] if result else 0
                        print(f"  📊 {table_name}: {count} lignes")
                
                if missing_tables:
                    print("\n❌ Tables manquantes:")
                    for table_name in missing_tables:
                        print(f"  🚫 {table_name}")
                    
                    print(f"\n💡 Pour créer les tables manquantes, exécutez:")
                    print(f"   python ensure_all_tables.py")
                
                # Vérifications spéciales
                print("\n🔍 Vérifications spéciales:")
                print("-" * 40)
                
                # Vérifier la colonne bump_role_id dans disboard_config
                if 'disboard_config' in existing_tables:
                    await cursor.execute("""
                        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = %s 
                        AND TABLE_NAME = 'disboard_config' 
                        AND COLUMN_NAME = 'bump_role_id'
                    """, (db_config['db'],))
                    
                    result = await cursor.fetchone()
                    if result and result[0] > 0:
                        print("✅ Colonne bump_role_id existe dans disboard_config")
                    else:
                        print("❌ Colonne bump_role_id manquante dans disboard_config")
                
                # Vérifier l'index idx_bump_role_id
                if 'disboard_config' in existing_tables:
                    await cursor.execute("""
                        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
                        WHERE TABLE_SCHEMA = %s 
                        AND TABLE_NAME = 'disboard_config' 
                        AND INDEX_NAME = 'idx_bump_role_id'
                    """, (db_config['db'],))
                    
                    result = await cursor.fetchone()
                    if result and result[0] > 0:
                        print("✅ Index idx_bump_role_id existe")
                    else:
                        print("❌ Index idx_bump_role_id manquant")
                
                # Vérifier la table guild_config (essentielle)
                if 'guild_config' in existing_tables:
                    print("✅ Table guild_config présente (essentielle pour le bot)")
                else:
                    print("❌ Table guild_config manquante (CRITIQUE pour le bot)")
                
                # Résumé final
                print("\n📊 Résumé final:")
                print("-" * 40)
                print(f"📋 Total des tables: {len(all_tables)}")
                print(f"✅ Tables existantes: {len(existing_tables)}")
                print(f"❌ Tables manquantes: {len(missing_tables)}")
                
                if not missing_tables:
                    print("\n🎉 Toutes les tables sont présentes !")
                    print("✅ Le bot Maybee est entièrement configuré")
                else:
                    print(f"\n⚠️  {len(missing_tables)} table(s) manquante(s) détectée(s)")
                    print("💡 Exécutez ensure_all_tables.py pour les créer")
                
                # Vérifier les données existantes
                print("\n📊 Données existantes:")
                print("-" * 40)
                
                data_tables = ['xp_data', 'xp_history', 'warnings', 'timeouts']
                for table_name in data_tables:
                    if table_name in existing_tables:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        result = await cursor.fetchone()
                        count = result[0] if result else 0
                        if count > 0:
                            print(f"📈 {table_name}: {count} enregistrements")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

if __name__ == "__main__":
    print("🔍 Vérification générale des tables Maybee")
    print("=" * 60)
    
    # Exécuter la vérification
    success = asyncio.run(check_all_tables())
    
    if success:
        print("\n✅ Vérification terminée")
    else:
        print("\n❌ Vérification échouée")
        exit(1)

