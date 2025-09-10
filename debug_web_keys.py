#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de débogage pour vérifier les clés manquantes spécifiques
"""

import json

def get_nested_value(data, key_path):
    """Récupère une valeur imbriquée dans un dictionnaire"""
    keys = key_path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    
    return current

def main():
    # Chargement des fichiers
    with open('web/languages/fr.json', 'r', encoding='utf-8') as f:
        fr_data = json.load(f)
    
    with open('web/languages/en.json', 'r', encoding='utf-8') as f:
        en_data = json.load(f)
    
    # Clés manquantes selon le script
    missing_keys = [
        "Chargement...",
        "Loading...",
        "Refreshing...",
        "moderation.action_error",
        "moderation.action_success",
        "moderation.limit",
        "moderation.no_history_found",
        "moderation.no_members",
        "moderation.select_member_action",
        "shown.bs.tab",
        "ticket_system.general_settings",
        "utilisateurs...",
        "xp_system.all_channels",
        "xp_system.enable_xp",
        "xp_system.level_up_channel",
        "xp_system.level_up_channel_description",
        "xp_system.level_up_messages",
        "xp_system.reset_xp",
        "xp_system.same_channel",
        "xp_system.save_xp_settings",
        "xp_system.test_level_up",
        "xp_system.xp_channel",
        "xp_system.xp_channel_description"
    ]
    
    print("🔍 Vérification des clés manquantes...")
    print("=" * 50)
    
    for key in missing_keys:
        fr_exists = get_nested_value(fr_data, key) is not None
        en_exists = get_nested_value(en_data, key) is not None
        
        print(f"Clé: {key}")
        print(f"  FR: {'✅' if fr_exists else '❌'}")
        print(f"  EN: {'✅' if en_exists else '❌'}")
        
        if not fr_exists:
            print(f"  Valeur FR trouvée: {get_nested_value(fr_data, key)}")
        if not en_exists:
            print(f"  Valeur EN trouvée: {get_nested_value(en_data, key)}")
        print()

if __name__ == "__main__":
    main()
