#!/usr/bin/env python3
"""
Script simple pour tester les cogs Disboard
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cog_import():
    """Teste l'importation des cogs Disboard"""
    
    print("🧪 Test d'importation des cogs Disboard")
    print("=" * 50)
    
    # Test d'importation du cog disboard_reminder
    try:
        from cog.disboard_reminder import DisboardReminder
        print("✅ cog.disboard_reminder importé avec succès")
        print(f"   - Classe: {DisboardReminder.__name__}")
        print(f"   - Module: {DisboardReminder.__module__}")
        
        # Vérifier les attributs de la classe
        if hasattr(DisboardReminder, 'bump_patterns'):
            print(f"   - Patterns de bump: {len(DisboardReminder.__init__.__code__.co_varnames)} paramètres")
        
        if hasattr(DisboardReminder, 'disboard_id'):
            print(f"   - ID Disboard: {DisboardReminder.__init__.__code__.co_varnames}")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'importation de cog.disboard_reminder: {e}")
        return False
    
    # Test d'importation du cog disboard_config
    try:
        from cog.disboard_config import DisboardConfig
        print("✅ cog.disboard_config importé avec succès")
        print(f"   - Classe: {DisboardConfig.__name__}")
        print(f"   - Module: {DisboardConfig.__module__}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'importation de cog.disboard_config: {e}")
        return False
    
    return True

def test_cog_syntax():
    """Teste la syntaxe des cogs"""
    
    print("\n🔍 Test de la syntaxe des cogs")
    print("=" * 50)
    
    # Test de syntaxe du cog disboard_reminder
    try:
        with open('cog/disboard_reminder.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Compiler le code pour vérifier la syntaxe
        compile(code, 'cog/disboard_reminder.py', 'exec')
        print("✅ Syntaxe de cog/disboard_reminder.py correcte")
        
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe dans cog/disboard_reminder.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de cog/disboard_reminder.py: {e}")
        return False
    
    # Test de syntaxe du cog disboard_config
    try:
        with open('cog/disboard_config.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Compiler le code pour vérifier la syntaxe
        compile(code, 'cog/disboard_config.py', 'exec')
        print("✅ Syntaxe de cog/disboard_config.py correcte")
        
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe dans cog/disboard_config.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de cog/disboard_config.py: {e}")
        return False
    
    return True

def test_dependencies():
    """Teste les dépendances nécessaires"""
    
    print("\n📦 Test des dépendances")
    print("=" * 50)
    
    required_modules = [
        'discord',
        'asyncio',
        're',
        'datetime',
        'typing',
        'i18n',
        'services',
        'monitoring'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} disponible")
        except ImportError as e:
            print(f"❌ {module} manquant: {e}")
            return False
    
    return True

def main():
    """Fonction principale de test"""
    
    print("🚀 Test simple des cogs Disboard")
    print("=" * 60)
    
    # Test 1: Dépendances
    deps_ok = test_dependencies()
    
    # Test 2: Syntaxe
    syntax_ok = test_cog_syntax()
    
    # Test 3: Importation
    import_ok = test_cog_import()
    
    print("\n🎯 Résumé:")
    print("-" * 30)
    
    if deps_ok and syntax_ok and import_ok:
        print("✅ Tous les tests sont passés")
        print("✅ Les cogs Disboard sont prêts")
        print("\n💡 Le problème pourrait être:")
        print("   - Le bot n'a pas été redémarré")
        print("   - Le bot Disboard n'est pas présent sur le serveur")
        print("   - Le bot n'a pas les permissions de lecture des messages")
        print("   - Le message de bump n'a pas le bon format")
    else:
        print("❌ Certains tests ont échoué")
        print("\n💡 Solutions:")
        if not deps_ok:
            print("   - Installez les dépendances manquantes")
        if not syntax_ok:
            print("   - Corrigez les erreurs de syntaxe")
        if not import_ok:
            print("   - Vérifiez les imports dans les cogs")
    
    print("\n🔧 Actions recommandées:")
    print("1. Redémarrez le bot")
    print("2. Vérifiez que le bot Disboard est sur votre serveur")
    print("3. Testez avec un vrai bump")
    print("4. Vérifiez les logs du bot")

if __name__ == "__main__":
    main()

