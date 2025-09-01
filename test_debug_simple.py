#!/usr/bin/env python3
"""
Script de test simple pour vérifier le debugging du système Disboard
"""

import logging
import re

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_simple.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_debug_patterns():
    """Teste les patterns de debug"""
    
    print("Test des patterns de debug Disboard")
    print("=" * 50)
    
    # Patterns de détection
    bump_patterns = [
        r"<@!?(\d+)> bumped the server!",
        r"<@!?(\d+)> just bumped the server!",
        r"<@!?(\d+)> bumped the server",
        r"<@!?(\d+)> just bumped the server",
        r"<@!?(\d+)> bumped",
        r"<@!?(\d+)> just bumped"
    ]
    
    disboard_id = 302050872383242240
    
    # Messages de test
    test_messages = [
        {
            "author_name": "Disboard",
            "author_id": disboard_id,
            "content": "<@!123456789> bumped the server!",
            "guild_name": "Test Server"
        },
        {
            "author_name": "Disboard", 
            "author_id": disboard_id,
            "content": "<@123456789> just bumped the server!",
            "guild_name": "Test Server"
        },
        {
            "author_name": "Other Bot",
            "author_id": 123456789,
            "content": "Some other message",
            "guild_name": "Test Server"
        }
    ]
    
    for i, case in enumerate(test_messages, 1):
        print(f"\nTest {i}: {case['content']}")
        
        # Simuler le debug du listener on_message
        logger.debug(f"Message recu - Auteur: {case['author_name']} (ID: {case['author_id']}) | Contenu: '{case['content']}' | Serveur: {case['guild_name']}")
        
        # Vérifier si c'est Disboard
        is_disboard = case['author_id'] == disboard_id
        logger.debug(f"Ce message provient-t-il de Disboard ? {'Oui' if is_disboard else 'Non'} (ID attendu: {disboard_id}, ID recu: {case['author_id']})")
        
        if not is_disboard:
            logger.debug("Message ignore: pas de Disboard")
            continue
        
        # Vérifier les patterns
        is_bump_message = False
        user_id = None
        
        for pattern in bump_patterns:
            match = re.search(pattern, case['content'], re.IGNORECASE)
            if match:
                is_bump_message = True
                user_id = int(match.group(1))
                logger.debug(f"S'agit-il d'un message de bump ? Oui | Pattern: '{pattern}' | User ID: {user_id}")
                break
        
        if not is_bump_message:
            logger.debug(f"S'agit-il d'un message de bump ? Non | Contenu: '{case['content']}'")
            continue
        
        # Simuler le traitement du bump
        logger.info(f"Bump detecte ! Utilisateur: User{user_id} (ID: {user_id}) | Serveur: {case['guild_name']}")
        logger.info(f"Traitement du bump detecte - Serveur: {case['guild_name']} | Utilisateur: User{user_id}")
        logger.debug(f"Recherche du dernier bump pour le serveur 123456789")
        logger.info(f"Nouveau bump cree - Count: 1")
        logger.debug(f"Envoi de l'embed de confirmation de bump")
        logger.info(f"Embed de confirmation envoye dans #general")
        logger.debug(f"Envoi du message de remerciement")
        logger.info(f"Message de remerciement simple envoye (pas de role configure)")
        logger.info(f"Bump traite avec succes dans {case['guild_name']} par User{user_id} (ID: {user_id})")

def main():
    """Fonction principale"""
    
    print("Test du debugging Disboard (version simple)")
    print("=" * 60)
    
    test_debug_patterns()
    
    print("\nResume:")
    print("-" * 30)
    print("Le systeme de debugging est configure")
    print("Les messages de debug sont generes")
    print("Les logs sont ecrits dans debug_simple.log")
    
    print("\nMessages de debug a surveiller:")
    print("- Message recu - Auteur: ...")
    print("- Ce message provient-t-il de Disboard ? ...")
    print("- S'agit-il d'un message de bump ? ...")
    print("- Bump detecte ! ...")
    print("- Traitement du bump detecte ...")
    print("- Envoi de l'embed de confirmation ...")
    print("- Envoi du message de remerciement ...")

if __name__ == "__main__":
    main()
