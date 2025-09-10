#!/usr/bin/env python3
"""
Script pour vérifier les clés de traduction utilisées dans les cogs
et s'assurer qu'elles existent dans les fichiers de langue.
"""

import os
import re
import json
import ast
from pathlib import Path

def load_language_files():
    """Charge les fichiers de langue fr.json et en.json"""
    try:
        with open('languages/fr.json', 'r', encoding='utf-8') as f:
            fr_data = json.load(f)
        with open('languages/en.json', 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        return fr_data, en_data
    except Exception as e:
        print(f"❌ Erreur lors du chargement des fichiers de langue: {e}")
        return None, None

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

def find_translation_keys_in_file(file_path):
    """Trouve toutes les clés de traduction utilisées dans un fichier Python"""
    keys_found = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Recherche des patterns de traduction plus larges
        patterns = [
            r'_\([\'"]([^\'"]+)[\'"]\)',  # _("key") ou _('key')
            r'i18n\.t\([\'"]([^\'"]+)[\'"]',  # i18n.t("key")
            r'gettext\([\'"]([^\'"]+)[\'"]',  # gettext("key")
            r'\.t\([\'"]([^\'"]+)[\'"]',  # .t("key")
            r'[\'"]([a-zA-Z_][a-zA-Z0-9_.]*)[\'"]',  # Toute chaîne qui ressemble à une clé
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            # Filtrer les clés qui ressemblent à des clés de traduction
            for match in matches:
                if '.' in match and not match.startswith('http') and not match.startswith('www'):
                    keys_found.add(match)
        
        # Recherche spécifique pour les clés avec des points
        dot_pattern = r'[\'"]([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z0-9_.]+)[\'"]'
        dot_matches = re.findall(dot_pattern, content)
        keys_found.update(dot_matches)
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la lecture de {file_path}: {e}")
    
    return keys_found

def scan_cogs_directory():
    """Scanne le répertoire cog pour trouver tous les fichiers Python"""
    cog_dir = Path('cog')
    python_files = []
    
    if cog_dir.exists():
        for file_path in cog_dir.rglob('*.py'):
            if file_path.name != '__init__.py':
                python_files.append(file_path)
    
    return python_files

def check_all_translation_keys():
    """Fonction principale pour vérifier toutes les clés de traduction"""
    print("🔍 Analyse des clés de traduction...")
    print("=" * 50)
    
    # Charger les fichiers de langue
    fr_data, en_data = load_language_files()
    if fr_data is None or en_data is None:
        return
    
    # Scanner tous les fichiers cog
    python_files = scan_cogs_directory()
    all_keys = set()
    
    print(f"📁 Fichiers trouvés: {len(python_files)}")
    print()
    
    # Collecter toutes les clés
    for file_path in python_files:
        keys = find_translation_keys_in_file(file_path)
        if keys:
            print(f"📄 {file_path.name}: {len(keys)} clés trouvées")
            all_keys.update(keys)
    
    print()
    print(f"🔑 Total des clés uniques trouvées: {len(all_keys)}")
    print()
    
    # Vérifier l'existence des clés
    missing_in_fr = []
    missing_in_en = []
    
    for key in sorted(all_keys):
        fr_exists = get_nested_value(fr_data, key) is not None
        en_exists = get_nested_value(en_data, key) is not None
        
        if not fr_exists:
            missing_in_fr.append(key)
        if not en_exists:
            missing_in_en.append(key)
    
    # Afficher les résultats
    print("📊 RÉSULTATS:")
    print("=" * 50)
    
    if missing_in_fr:
        print(f"❌ Clés manquantes dans fr.json ({len(missing_in_fr)}):")
        for key in missing_in_fr:
            print(f"   - {key}")
        print()
    else:
        print("✅ Toutes les clés existent dans fr.json")
        print()
    
    if missing_in_en:
        print(f"❌ Clés manquantes dans en.json ({len(missing_in_en)}):")
        for key in missing_in_en:
            print(f"   - {key}")
        print()
    else:
        print("✅ Toutes les clés existent dans en.json")
        print()
    
    # Clés manquantes dans les deux fichiers
    missing_in_both = set(missing_in_fr) & set(missing_in_en)
    if missing_in_both:
        print(f"🚨 Clés manquantes dans les DEUX fichiers ({len(missing_in_both)}):")
        for key in sorted(missing_in_both):
            print(f"   - {key}")
        print()
    
    # Statistiques finales
    print("📈 STATISTIQUES:")
    print(f"   • Total des clés analysées: {len(all_keys)}")
    print(f"   • Clés présentes dans fr.json: {len(all_keys) - len(missing_in_fr)}")
    print(f"   • Clés présentes dans en.json: {len(all_keys) - len(missing_in_en)}")
    print(f"   • Clés manquantes dans fr.json: {len(missing_in_fr)}")
    print(f"   • Clés manquantes dans en.json: {len(missing_in_en)}")
    
    return missing_in_fr, missing_in_en, all_keys

if __name__ == "__main__":
    check_all_translation_keys()
