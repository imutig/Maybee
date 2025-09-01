#!/usr/bin/env python3
"""
Script de vérification rapide des tables du système Disboard
Ce script vérifie simplement l'existence et le nombre de lignes des tables
"""

import asyncio
import aiomysql
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def check_disboard_tables():
    """Vérifie l'état des tables du système Disboard"""
    
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
                
                # Vérifier l'existence des tables
                print("\n🔍 Vérification de l'existence des tables...")
                
                tables_to_check = [
                    'disboard_bumps',
                    'disboard_reminders', 
                    'disboard_config'
                ]
                
                existing_tables = []
                missing_tables = []
                
                for table_name in tables_to_check:
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
                print("\n📋 Statut des tables du système Disboard:")
                print("-" * 50)
                
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
                    print(f"   python ensure_disboard_tables.py")
                
                # Vérifier la colonne bump_role_id
                print("\n🔍 Vérification de la colonne bump_role_id...")
                await cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'disboard_config' 
                    AND COLUMN_NAME = 'bump_role_id'
                """, (db_config['db'],))
                
                result = await cursor.fetchone()
                if result and result[0] > 0:
                    print("✅ Colonne bump_role_id existe")
                else:
                    print("❌ Colonne bump_role_id manquante")
                    print("💡 Exécutez ensure_disboard_tables.py pour l'ajouter")
                
                # Vérifier l'index idx_bump_role_id
                print("\n🔍 Vérification de l'index idx_bump_role_id...")
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
                    print("💡 Exécutez ensure_disboard_tables.py pour le créer")
                
                # Résumé final
                if not missing_tables:
                    print("\n🎉 Toutes les tables du système Disboard sont présentes !")
                else:
                    print(f"\n⚠️  {len(missing_tables)} table(s) manquante(s) détectée(s)")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

if __name__ == "__main__":
    print("🔍 Vérification des tables Disboard")
    print("=" * 50)
    
    # Exécuter la vérification
    success = asyncio.run(check_disboard_tables())
    
    if success:
        print("\n✅ Vérification terminée")
    else:
        print("\n❌ Vérification échouée")
        exit(1)
