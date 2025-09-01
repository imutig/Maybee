#!/usr/bin/env python3
"""
Script de diagnostic complet pour le système Disboard
"""

import asyncio
import aiomysql
import os
import re
from dotenv import load_dotenv
from datetime import datetime

# Charger les variables d'environnement
load_dotenv()

async def check_database_status():
    """Vérifie l'état de la base de données"""
    
    print("🔌 Vérification de la base de données")
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
                
                # Vérifier la configuration des serveurs
                print("\n🔧 Vérification de la configuration des serveurs...")
                
                await cursor.execute("SELECT * FROM disboard_config")
                configs = await cursor.fetchall()
                
                if configs:
                    print(f"  📋 {len(configs)} serveur(s) configuré(s):")
                    for config in configs:
                        print(f"     - Guild ID: {config['guild_id']}")
                        print(f"       Canal de rappel: {config.get('reminder_channel_id', 'Non configuré')}")
                        print(f"       Rôle de bump: {config.get('bump_role_id', 'Non configuré')}")
                        print(f"       Rappels activés: {config.get('reminder_enabled', 'Non configuré')}")
                else:
                    print("  ❌ Aucun serveur configuré")
                
                # Vérifier les bumps existants
                print("\n📈 Vérification des bumps existants...")
                
                await cursor.execute("SELECT COUNT(*) FROM disboard_bumps")
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
                
                # Vérifier les rappels
                print("\n⏰ Vérification des rappels...")
                
                await cursor.execute("SELECT COUNT(*) FROM disboard_reminders")
                result = await cursor.fetchone()
                total_reminders = result[0] if result else 0
                print(f"  📊 Total des rappels envoyés: {total_reminders}")
                
                if total_reminders > 0:
                    await cursor.execute(
                        "SELECT * FROM disboard_reminders ORDER BY reminder_time DESC LIMIT 5"
                    )
                    recent_reminders = await cursor.fetchall()
                    
                    print("  📋 5 derniers rappels:")
                    for reminder in recent_reminders:
                        print(f"     - Guild {reminder['guild_id']} - {reminder['reminder_time']}")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()
    
    return True

def check_bot_configuration():
    """Vérifie la configuration du bot"""
    
    print("\n🤖 Vérification de la configuration du bot")
    print("=" * 50)
    
    # Vérifier le fichier main.py
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        # Vérifier si les cogs Disboard sont dans la liste des extensions
        if 'cog.disboard_reminder' in main_content and 'cog.disboard_config' in main_content:
            print("✅ Les cogs Disboard sont dans main.py")
        else:
            print("❌ Les cogs Disboard ne sont pas dans main.py")
            return False
        
        # Vérifier la structure des extensions
        if 'load_extensions' in main_content:
            print("✅ Fonction load_extensions trouvée")
        else:
            print("❌ Fonction load_extensions non trouvée")
            return False
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de main.py: {e}")
        return False
    
    # Vérifier les fichiers des cogs
    cog_files = ['cog/disboard_reminder.py', 'cog/disboard_config.py']
    
    for cog_file in cog_files:
        if os.path.exists(cog_file):
            print(f"✅ {cog_file} existe")
        else:
            print(f"❌ {cog_file} n'existe pas")
            return False
    
    return True

def check_disboard_patterns():
    """Vérifie les patterns de détection"""
    
    print("\n🔍 Vérification des patterns de détection")
    print("=" * 50)
    
    # Patterns de test
    bump_patterns = [
        r"<@!?(\d+)> bumped the server!",
        r"<@!?(\d+)> just bumped the server!",
        r"<@!?(\d+)> bumped the server",
        r"<@!?(\d+)> just bumped the server",
        r"<@!?(\d+)> bumped",
        r"<@!?(\d+)> just bumped"
    ]
    
    # Messages de test basés sur les vrais messages de Disboard
    test_messages = [
        "<@!123456789> bumped the server!",
        "<@123456789> just bumped the server!",
        "<@!123456789> bumped the server",
        "<@123456789> bumped",
        # Messages qui ne devraient PAS matcher
        "Someone bumped the server!",
        "The server was bumped!",
        "Bump successful!"
    ]
    
    print("📝 Test des patterns:")
    
    all_tests_passed = True
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i}. {message}")
        
        # Tester chaque pattern
        matched = False
        for pattern in bump_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                user_id = match.group(1)
                print(f"   ✅ MATCH: Pattern '{pattern}' -> User ID: {user_id}")
                matched = True
                break
        
        if not matched:
            print(f"   ❌ NO MATCH")
            # Pour les messages qui ne devraient pas matcher, c'est normal
            if i <= 4:  # Les 4 premiers messages devraient matcher
                all_tests_passed = False
        
        print()
    
    return all_tests_passed

def check_environment():
    """Vérifie l'environnement"""
    
    print("\n🌍 Vérification de l'environnement")
    print("=" * 50)
    
    # Vérifier les variables d'environnement
    required_env_vars = ['DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME']
    
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * len(value)}")
        else:
            print(f"❌ {var}: Non défini")
            return False
    
    # Vérifier les fichiers nécessaires
    required_files = [
        '.env',
        'main.py',
        'cog/disboard_reminder.py',
        'cog/disboard_config.py',
        'languages/fr.json',
        'languages/en.json'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} existe")
        else:
            print(f"❌ {file_path} n'existe pas")
            return False
    
    return True

async def main():
    """Fonction principale de diagnostic"""
    
    print("🚀 Diagnostic complet du système Disboard")
    print("=" * 60)
    
    # Test 1: Environnement
    env_ok = check_environment()
    
    # Test 2: Configuration du bot
    bot_ok = check_bot_configuration()
    
    # Test 3: Patterns de détection
    patterns_ok = check_disboard_patterns()
    
    # Test 4: Base de données
    db_ok = await check_database_status()
    
    print("\n🎯 Résumé du diagnostic:")
    print("=" * 60)
    
    print(f"🌍 Environnement: {'✅ OK' if env_ok else '❌ ERREUR'}")
    print(f"🤖 Configuration bot: {'✅ OK' if bot_ok else '❌ ERREUR'}")
    print(f"🔍 Patterns détection: {'✅ OK' if patterns_ok else '❌ ERREUR'}")
    print(f"🔌 Base de données: {'✅ OK' if db_ok else '❌ ERREUR'}")
    
    if env_ok and bot_ok and patterns_ok and db_ok:
        print("\n🎉 Tous les tests sont passés !")
        print("✅ Le système Disboard est correctement configuré")
        print("\n💡 Le problème pourrait être:")
        print("   - Le bot n'a pas été redémarré depuis l'ajout des cogs")
        print("   - Le bot Disboard n'est pas présent sur votre serveur")
        print("   - Le bot n'a pas les permissions de lecture des messages")
        print("   - Le message de bump n'a pas le bon format")
        print("   - Le bot n'a pas les permissions d'envoyer des messages")
        
        print("\n🔧 Actions recommandées:")
        print("1. 🔄 Redémarrez le bot")
        print("2. 🤖 Vérifiez que le bot Disboard est sur votre serveur")
        print("3. 📝 Testez avec un vrai bump")
        print("4. 📋 Vérifiez les logs du bot")
        print("5. ⚙️  Configurez le système avec /disboard setup")
        
    else:
        print("\n❌ Certains tests ont échoué")
        print("\n💡 Solutions:")
        if not env_ok:
            print("   - Vérifiez les variables d'environnement")
        if not bot_ok:
            print("   - Vérifiez la configuration du bot")
        if not patterns_ok:
            print("   - Vérifiez les patterns de détection")
        if not db_ok:
            print("   - Vérifiez la connexion à la base de données")

if __name__ == "__main__":
    asyncio.run(main())

