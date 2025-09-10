#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier les clés de traduction du site web
Analyse les fichiers HTML et vérifie l'existence des clés dans fr.json et en.json
"""

import os
import json
import re
from pathlib import Path

def load_json_file(file_path):
    """Charge un fichier JSON et retourne son contenu"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur lors du chargement de {file_path}: {e}")
        return None

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

def find_translation_keys_in_html(file_path):
    """Trouve toutes les clés de traduction dans un fichier HTML"""
    keys = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Recherche des attributs data-translate
        pattern = r'data-translate="([^"]+)"'
        matches = re.findall(pattern, content)
        
        for match in matches:
            keys.add(match)
            
        # Recherche des clés dans le JavaScript (si présentes)
        js_pattern = r'translate\(["\']([^"\']+)["\']\)'
        js_matches = re.findall(js_pattern, content)
        
        for match in js_matches:
            keys.add(match)
            
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de {file_path}: {e}")
    
    return keys

def find_translation_keys_in_js(file_path):
    """Trouve toutes les clés de traduction dans un fichier JavaScript"""
    keys = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Recherche des appels translate()
        pattern = r'translate\(["\']([^"\']+)["\']\)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            keys.add(match)
            
        # Recherche des clés dans les objets de traduction
        obj_pattern = r'["\']([a-zA-Z_][a-zA-Z0-9_.]*)["\']'
        obj_matches = re.findall(obj_pattern, content)
        
        for match in obj_matches:
            if '.' in match and len(match) > 3:  # Filtre les clés qui ressemblent à des clés de traduction
                keys.add(match)
                
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de {file_path}: {e}")
    
    return keys

def main():
    print("🔍 Analyse des clés de traduction du site web...")
    print("=" * 50)
    
    # Chemins des fichiers
    web_fr_path = "web/languages/fr.json"
    web_en_path = "web/languages/en.json"
    
    # Chargement des fichiers de traduction
    fr_data = load_json_file(web_fr_path)
    en_data = load_json_file(web_en_path)
    
    if fr_data is None or en_data is None:
        print("❌ Impossible de charger les fichiers de traduction")
        return
    
    # Recherche des fichiers HTML et JS
    web_dir = Path("web")
    html_files = list(web_dir.rglob("*.html"))
    js_files = list(web_dir.rglob("*.js"))
    
    print(f"📁 Fichiers HTML trouvés: {len(html_files)}")
    print(f"📁 Fichiers JS trouvés: {len(js_files)}")
    print()
    
    # Collecte de toutes les clés
    all_keys = set()
    
    # Analyse des fichiers HTML
    for html_file in html_files:
        keys = find_translation_keys_in_html(html_file)
        if keys:
            print(f"📄 {html_file.name}: {len(keys)} clés trouvées")
            all_keys.update(keys)
    
    # Analyse des fichiers JavaScript
    for js_file in js_files:
        keys = find_translation_keys_in_js(js_file)
        if keys:
            print(f"📄 {js_file.name}: {len(keys)} clés trouvées")
            all_keys.update(keys)
    
    print(f"\n🔑 Total des clés uniques trouvées: {len(all_keys)}")
    
    # Vérification de l'existence des clés
    fr_missing = []
    en_missing = []
    
    for key in sorted(all_keys):
        fr_exists = get_nested_value(fr_data, key) is not None
        en_exists = get_nested_value(en_data, key) is not None
        
        if not fr_exists:
            fr_missing.append(key)
        if not en_exists:
            en_missing.append(key)
    
    # Affichage des résultats
    print("\n📊 RÉSULTATS:")
    print("=" * 50)
    
    if fr_missing:
        print(f"❌ Clés manquantes dans {web_fr_path} ({len(fr_missing)}):")
        for key in fr_missing:
            print(f"   - {key}")
    else:
        print(f"✅ Toutes les clés existent dans {web_fr_path}")
    
    print()
    
    if en_missing:
        print(f"❌ Clés manquantes dans {web_en_path} ({len(en_missing)}):")
        for key in en_missing:
            print(f"   - {key}")
    else:
        print(f"✅ Toutes les clés existent dans {web_en_path}")
    
    # Clés manquantes dans les deux fichiers
    both_missing = set(fr_missing) & set(en_missing)
    if both_missing:
        print(f"\n🚨 Clés manquantes dans les DEUX fichiers ({len(both_missing)}):")
        for key in sorted(both_missing):
            print(f"   - {key}")
    
    # Statistiques
    print(f"\n📈 STATISTIQUES:")
    print(f"   • Total des clés analysées: {len(all_keys)}")
    print(f"   • Clés présentes dans {web_fr_path}: {len(all_keys) - len(fr_missing)}")
    print(f"   • Clés présentes dans {web_en_path}: {len(all_keys) - len(en_missing)}")
    print(f"   • Clés manquantes dans {web_fr_path}: {len(fr_missing)}")
    print(f"   • Clés manquantes dans {web_en_path}: {len(en_missing)}")

if __name__ == "__main__":
    main()
