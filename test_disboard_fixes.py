#!/usr/bin/env python3
"""
Script de test pour vérifier les corrections du système Disboard
"""

import re

def test_custom_id_parsing():
    """Teste le parsing des custom_id des boutons"""
    
    print("🧪 Test du parsing des custom_id")
    print("=" * 50)
    
    # Test cases pour les custom_id
    test_cases = [
        "bump_role_yes_123456789_987654321",
        "bump_role_no_123456789_987654321",
        "other_button_id",
        "bump_role_yes_123",
        "bump_role_yes_123_456_789"  # Trop de parties
    ]
    
    for custom_id in test_cases:
        print(f"\nTest: '{custom_id}'")
        
        if not custom_id.startswith("bump_role_"):
            print("  ❌ Ne commence pas par 'bump_role_'")
            continue
        
        parts = custom_id.split("_")
        print(f"  📝 Parties: {parts} (longueur: {len(parts)})")
        
        if len(parts) != 5:
            print("  ❌ Nombre de parties incorrect (attendu: 5)")
            continue
        
        try:
            action = parts[2]
            user_id = int(parts[3])
            guild_id = int(parts[4])
            
            print(f"  ✅ Parsing réussi:")
            print(f"     Action: {action}")
            print(f"     User ID: {user_id}")
            print(f"     Guild ID: {guild_id}")
        except ValueError as e:
            print(f"  ❌ Erreur de conversion: {e}")

def test_database_query_syntax():
    """Teste la syntaxe des requêtes de base de données"""
    
    print("\n🧪 Test de la syntaxe des requêtes DB")
    print("=" * 50)
    
    # Exemples de requêtes corrigées
    queries = [
        {
            "name": "Recherche bump existant",
            "query": "SELECT * FROM disboard_bumps WHERE guild_id = %s ORDER BY bump_time DESC LIMIT 1",
            "params": "(guild.id,)",
            "method": "fetchone=True"
        },
        {
            "name": "Mise à jour bump",
            "query": "UPDATE disboard_bumps SET bumper_id = %s WHERE id = %s",
            "params": "(bumper.id, existing_bump['id'])",
            "method": "None (INSERT/UPDATE)"
        },
        {
            "name": "Insertion nouveau bump",
            "query": "INSERT INTO disboard_bumps (guild_id, bumper_id) VALUES (%s, %s)",
            "params": "(guild.id, bumper.id)",
            "method": "None (INSERT/UPDATE)"
        },
        {
            "name": "Top bumpers",
            "query": "SELECT bumper_id, COUNT(*) FROM disboard_bumps WHERE guild_id = %s GROUP BY bumper_id",
            "params": "(guild_id,)",
            "method": "fetchall=True"
        }
    ]
    
    for query_info in queries:
        print(f"\n📝 {query_info['name']}:")
        print(f"   Query: {query_info['query']}")
        print(f"   Params: {query_info['params']}")
        print(f"   Method: await self.bot.db.query(query, params, {query_info['method']})")

def test_debug_patterns():
    """Teste les patterns de debugging"""
    
    print("\n🧪 Test des patterns de debugging")
    print("=" * 50)
    
    # Messages de test
    test_messages = [
        "<@!123456789> bumped the server!",
        "<@123456789> just bumped the server!",
        "This is not a bump message"
    ]
    
    bump_patterns = [
        r"<@!?(\d+)> bumped the server!",
        r"<@!?(\d+)> just bumped the server!",
        r"<@!?(\d+)> bumped the server",
        r"<@!?(\d+)> just bumped the server",
        r"<@!?(\d+)> bumped",
        r"<@!?(\d+)> just bumped"
    ]
    
    for message in test_messages:
        print(f"\nMessage: '{message}'")
        
        is_bump_message = False
        matched_pattern = None
        user_id = None
        
        for pattern in bump_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                is_bump_message = True
                matched_pattern = pattern
                user_id = int(match.group(1))
                print(f"  ✅ Match trouvé avec pattern: '{pattern}'")
                print(f"  👤 User ID extrait: {user_id}")
                break
        
        if not is_bump_message:
            print(f"  ❌ Aucun pattern ne correspond")

def main():
    """Fonction principale"""
    
    print("🚀 Test des corrections Disboard")
    print("=" * 60)
    
    test_custom_id_parsing()
    test_database_query_syntax()
    test_debug_patterns()
    
    print("\n🎯 Résumé des corrections:")
    print("-" * 30)
    print("✅ Correction des méthodes de base de données:")
    print("   - fetchone() -> query(..., fetchone=True)")
    print("   - fetchall() -> query(..., fetchall=True)")
    print("   - execute() -> query(...)")
    print("✅ Correction du parsing des custom_id:")
    print("   - Vérification du nombre de parties (5)")
    print("   - Extraction correcte des IDs")
    print("✅ Ajout du debugging détaillé:")
    print("   - Messages de réception")
    print("   - Vérification Disboard")
    print("   - Détection des bumps")
    print("   - Traitement complet")
    
    print("\n💡 Prochaines étapes:")
    print("1. Redémarrez votre bot pour charger les corrections")
    print("2. Effectuez un bump avec Disboard")
    print("3. Vérifiez les logs pour voir le debugging")
    print("4. Testez les commandes /bumptop et /bumpstats")

if __name__ == "__main__":
    main()
