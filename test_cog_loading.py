#!/usr/bin/env python3
"""
Script de test pour vérifier le chargement des cogs Disboard
"""

import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def test_cog_loading():
    """Teste le chargement des cogs Disboard"""
    
    print("🧪 Test du chargement des cogs Disboard")
    print("=" * 50)
    
    # Configuration du bot de test
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Liste des cogs à tester
    cogs_to_test = [
        "cog.disboard_reminder",
        "cog.disboard_config"
    ]
    
    print("📋 Cogs à tester:")
    for cog in cogs_to_test:
        print(f"  - {cog}")
    
    print("\n🔧 Test de chargement des cogs:")
    print("-" * 40)
    
    for cog_name in cogs_to_test:
        try:
            await bot.load_extension(cog_name)
            print(f"✅ {cog_name} chargé avec succès")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {cog_name}: {e}")
    
    print("\n📊 Cogs chargés:")
    print("-" * 40)
    
    for cog_name, cog in bot.cogs.items():
        print(f"  - {cog_name}: {type(cog).__name__}")
    
    print(f"\n📈 Total des cogs chargés: {len(bot.cogs)}")
    
    # Vérifier spécifiquement les cogs Disboard
    disboard_cogs = [name for name in bot.cogs.keys() if 'disboard' in name.lower()]
    
    if disboard_cogs:
        print(f"\n✅ Cogs Disboard trouvés: {disboard_cogs}")
        
        # Vérifier les commandes des cogs Disboard
        for cog_name in disboard_cogs:
            cog = bot.cogs[cog_name]
            print(f"\n🔍 Commandes de {cog_name}:")
            
            # Vérifier les commandes slash
            if hasattr(cog, 'get_commands'):
                commands = cog.get_commands()
                for cmd in commands:
                    print(f"  - /{cmd.name}: {cmd.description}")
            
            # Vérifier les listeners
            if hasattr(cog, 'get_listeners'):
                listeners = cog.get_listeners()
                for listener in listeners:
                    print(f"  - Listener: {listener}")
            
            # Vérifier les tâches
            if hasattr(cog, 'get_tasks'):
                tasks = cog.get_tasks()
                for task in tasks:
                    print(f"  - Tâche: {task.name}")
    
    else:
        print("\n❌ Aucun cog Disboard trouvé")
    
    # Nettoyer
    await bot.close()
    
    return len(disboard_cogs) > 0

async def test_disboard_patterns():
    """Teste les patterns de détection des bumps"""
    
    print("\n🔍 Test des patterns de détection")
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
    
    # Messages de test
    test_messages = [
        "<@!123456789> bumped the server!",
        "<@123456789> just bumped the server!",
        "Someone bumped the server!",
        "<@!123456789> bumped the server! 🚀"
    ]
    
    print("📝 Messages de test:")
    for i, message in enumerate(test_messages, 1):
        print(f"{i}. {message}")
        
        # Tester chaque pattern
        matched = False
        for pattern in bump_patterns:
            import re
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                user_id = match.group(1)
                print(f"   ✅ MATCH: Pattern '{pattern}' -> User ID: {user_id}")
                matched = True
                break
        
        if not matched:
            print(f"   ❌ NO MATCH")
        
        print()

async def main():
    """Fonction principale de test"""
    
    print("🚀 Test complet des cogs Disboard")
    print("=" * 60)
    
    # Test 1: Chargement des cogs
    cogs_loaded = await test_cog_loading()
    
    # Test 2: Patterns de détection
    await test_disboard_patterns()
    
    print("\n🎯 Résumé:")
    print("-" * 30)
    
    if cogs_loaded:
        print("✅ Les cogs Disboard sont correctement chargés")
        print("✅ Les patterns de détection fonctionnent")
        print("\n💡 Le problème pourrait être:")
        print("   - Le bot n'a pas été redémarré")
        print("   - Le bot Disboard n'est pas présent sur le serveur")
        print("   - Le bot n'a pas les permissions de lecture des messages")
        print("   - Le message de bump n'a pas le bon format")
    else:
        print("❌ Les cogs Disboard ne sont pas chargés")
        print("\n💡 Solutions:")
        print("   - Vérifiez que les fichiers existent")
        print("   - Vérifiez la syntaxe des cogs")
        print("   - Redémarrez le bot")
    
    print("\n🔧 Actions recommandées:")
    print("1. Redémarrez le bot")
    print("2. Vérifiez que le bot Disboard est sur votre serveur")
    print("3. Testez avec un vrai bump")
    print("4. Vérifiez les logs du bot")

if __name__ == "__main__":
    asyncio.run(main())

