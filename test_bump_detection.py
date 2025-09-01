#!/usr/bin/env python3
"""
Script de test pour vérifier la détection des bumps Disboard
Ce script teste les patterns de détection et simule un bump
"""

import re
import asyncio
import aiomysql
import os
from dotenv import load_dotenv
from datetime import datetime

# Charger les variables d'environnement
load_dotenv()

# Patterns de détection des bumps
bump_patterns = [
    r"<@!?(\d+)> bumped the server!",
    r"<@!?(\d+)> just bumped the server!",
    r"<@!?(\d+)> bumped the server",
    r"<@!?(\d+)> just bumped the server",
    r"<@!?(\d+)> bumped",
    r"<@!?(\d+)> just bumped"
]

# ID du bot Disboard
disboard_id = 302050872383242240

def test_bump_patterns():
    """Teste les patterns de détection avec différents messages"""
    
    print("🧪 Test des patterns de détection des bumps")
    print("=" * 50)
    
    # Messages de test basés sur les vrais messages de Disboard
    test_messages = [
        "<@!123456789> bumped the server!",
        "<@123456789> bumped the server!",
        "<@!123456789> just bumped the server!",
        "<@123456789> just bumped the server!",
        "<@!123456789> bumped the server",
        "<@123456789> bumped the server",
        "<@!123456789> just bumped the server",
        "<@123456789> just bumped the server",
        "<@!123456789> bumped",
        "<@123456789> bumped",
        "<@!123456789> just bumped",
        "<@123456789> just bumped",
        # Messages avec des variations
        "<@!123456789> bumped the server! 🚀",
        "<@123456789> just bumped the server! Great job!",
        # Messages qui ne devraient PAS matcher
        "Someone bumped the server!",
        "The server was bumped!",
        "Bump successful!",
        "Server bumped by someone"
    ]
    
    print("📝 Messages de test:")
    print("-" * 30)
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i:2d}. {message}")
        
        # Tester chaque pattern
        matched = False
        for pattern in bump_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                user_id = match.group(1)
                print(f"    ✅ MATCH: Pattern '{pattern}' -> User ID: {user_id}")
                matched = True
                break
        
        if not matched:
            print(f"    ❌ NO MATCH")
        
        print()
    
    print("🔍 Analyse des patterns:")
    print("-" * 30)
    
    for i, pattern in enumerate(bump_patterns, 1):
        print(f"{i}. {pattern}")
    
    print(f"\n🤖 ID du bot Disboard: {disboard_id}")
    print(f"📊 Nombre de patterns: {len(bump_patterns)}")

async def test_database_connection():
    """Teste la connexion à la base de données"""
    
    print("\n🔌 Test de la connexion à la base de données")
    print("=" * 50)
    
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
                
                # Vérifier les tables Disboard
                print("\n📊 Vérification des tables Disboard...")
                
                tables_to_check = ['disboard_bumps', 'disboard_reminders', 'disboard_config']
                
                for table_name in tables_to_check:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    result = await cursor.fetchone()
                    count = result[0] if result else 0
                    print(f"  📊 {table_name}: {count} lignes")
                
                # Vérifier la configuration du serveur
                print("\n🔧 Vérification de la configuration...")
                
                # Simuler un guild_id de test
                test_guild_id = 123456789
                
                await cursor.execute(
                    "SELECT * FROM disboard_config WHERE guild_id = %s",
                    (test_guild_id,)
                )
                
                config = await cursor.fetchone()
                if config:
                    print(f"  ✅ Configuration trouvée pour guild_id {test_guild_id}")
                    print(f"     - Canal de rappel: {config.get('reminder_channel_id', 'Non configuré')}")
                    print(f"     - Rôle de bump: {config.get('bump_role_id', 'Non configuré')}")
                    print(f"     - Rappels activés: {config.get('reminder_enabled', 'Non configuré')}")
                else:
                    print(f"  ❌ Aucune configuration trouvée pour guild_id {test_guild_id}")
                
                # Vérifier les bumps existants
                print("\n📈 Vérification des bumps existants...")
                
                await cursor.execute(
                    "SELECT COUNT(*) FROM disboard_bumps"
                )
                result = await cursor.fetchone()
                total_bumps = result[0] if result else 0
                print(f"  📊 Total des bumps enregistrés: {total_bumps}")
                
                if total_bumps > 0:
                    await cursor.execute(
                        "SELECT * FROM disboard_bumps ORDER BY bump_time DESC LIMIT 5"
                    )
                    recent_bumps = await cursor.fetchall()
                    
                    print("  📋 5 derniers bumps:")
                    for bump in recent_bumps:
                        print(f"     - {bump['bumper_name']} ({bump['bumper_id']}) - {bump['bump_time']}")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

def test_message_parsing():
    """Teste le parsing des messages Discord"""
    
    print("\n🔍 Test du parsing des messages Discord")
    print("=" * 50)
    
    # Simuler différents formats de messages Discord
    test_cases = [
        {
            "content": "<@!123456789> bumped the server!",
            "author_id": disboard_id,
            "guild_id": 987654321
        },
        {
            "content": "<@123456789> just bumped the server!",
            "author_id": disboard_id,
            "guild_id": 987654321
        },
        {
            "content": "Someone bumped the server!",
            "author_id": disboard_id,
            "guild_id": 987654321
        },
        {
            "content": "<@!123456789> bumped the server!",
            "author_id": 123456789,  # Pas Disboard
            "guild_id": 987654321
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}:")
        print(f"  Contenu: {case['content']}")
        print(f"  Auteur ID: {case['author_id']}")
        print(f"  Guild ID: {case['guild_id']}")
        
        # Vérifier si c'est Disboard
        if case['author_id'] != disboard_id:
            print("  ❌ Pas un message de Disboard")
            print()
            continue
        
        # Vérifier les patterns
        matched = False
        for pattern in bump_patterns:
            match = re.search(pattern, case['content'], re.IGNORECASE)
            if match:
                user_id = match.group(1)
                print(f"  ✅ MATCH: User ID {user_id}")
                matched = True
                break
        
        if not matched:
            print("  ❌ Aucun pattern ne correspond")
        
        print()

async def main():
    """Fonction principale de test"""
    
    print("🚀 Test de la détection des bumps Disboard")
    print("=" * 60)
    
    # Test 1: Patterns de détection
    test_bump_patterns()
    
    # Test 2: Connexion à la base de données
    await test_database_connection()
    
    # Test 3: Parsing des messages
    test_message_parsing()
    
    print("\n🎯 Recommandations:")
    print("-" * 30)
    print("1. Vérifiez que le bot Disboard est présent sur votre serveur")
    print("2. Vérifiez que le cog DisboardReminder est chargé")
    print("3. Vérifiez les logs du bot pour les erreurs")
    print("4. Testez avec un vrai bump sur le serveur")
    print("5. Vérifiez que le bot a les permissions de lecture des messages")

if __name__ == "__main__":
    asyncio.run(main())

