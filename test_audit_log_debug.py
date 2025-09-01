#!/usr/bin/env python3
"""
Script pour tester les nouveaux logs de debug des audit logs
"""

def test_audit_log_debug_format():
    """Teste le format des nouveaux logs de debug"""
    
    print("🧪 Test des nouveaux logs de debug des audit logs")
    print("=" * 60)
    
    # Simuler différents types d'audit logs
    audit_logs = [
        {
            'command': 'bump',
            'user': 'JohnDoe',
            'time_diff': 15.2,
            'is_bump': True
        },
        {
            'command': 'config',
            'user': 'Alice',
            'time_diff': 8.7,
            'is_bump': False
        },
        {
            'command': 'ping',
            'user': 'Bob',
            'time_diff': 45.1,
            'is_bump': False
        },
        {
            'command': 'bump',
            'user': 'Charlie',
            'time_diff': 32.3,
            'is_bump': True
        }
    ]
    
    print("📋 Simulation des logs d'audit log:")
    print("-" * 40)
    
    for log in audit_logs:
        if log['time_diff'] > 30:
            print(f"⏰ Audit log ignoré (trop ancien): {log['time_diff']:.1f}s - Utilisateur: {log['user']}")
            continue
        
        print(f"📋 Audit log trouvé: Commande='{log['command']}' | Utilisateur: {log['user']} | Temps: {log['time_diff']:.1f}s")
        
        if log['is_bump']:
            print(f"🎯 ✅ Commande /bump trouvée dans l'audit log - Utilisateur: {log['user']}")
        else:
            print(f"❌ Pas un bump: Commande '{log['command']}' - Utilisateur: {log['user']}")
        print()

def test_message_history_debug():
    """Teste les logs de debug de l'historique des messages"""
    
    print("📋 Simulation des logs d'historique de messages:")
    print("-" * 40)
    
    # Simuler différents messages
    messages = [
        {
            'content': '/bump',
            'author': 'JohnDoe',
            'time_diff': 12.5,
            'is_bump': True
        },
        {
            'content': 'Hello everyone!',
            'author': 'Alice',
            'time_diff': 5.2,
            'is_bump': False
        },
        {
            'content': '/config language',
            'author': 'Bob',
            'time_diff': 18.9,
            'is_bump': False
        },
        {
            'content': '/bump',
            'author': 'Charlie',
            'time_diff': 35.7,
            'is_bump': True
        }
    ]
    
    for msg in messages:
        print(f"📋 Message trouvé: Contenu='{msg['content'][:50]}...' | Auteur: {msg['author']} | Temps: {msg['time_diff']:.1f}s")
        
        if '/bump' in msg['content'].lower():
            if msg['time_diff'] <= 30:
                print(f"🎯 ✅ Message /bump trouvé - Utilisateur: {msg['author']}")
            else:
                print(f"⏰ Message /bump trop ancien: {msg['time_diff']:.1f}s - Utilisateur: {msg['author']}")
        else:
            print(f"❌ Pas un message /bump: '{msg['content'][:30]}...' - Utilisateur: {msg['author']}")
        print()

def main():
    """Fonction principale"""
    print("🚀 Test des nouveaux logs de debug des audit logs")
    print("=" * 60)
    
    test_audit_log_debug_format()
    test_message_history_debug()
    
    print("💡 Améliorations apportées:")
    print("-" * 40)
    print("✅ Logs détaillés pour tous les audit logs")
    print("✅ Identification claire des bumps vs autres commandes")
    print("✅ Temps écoulé affiché pour chaque entrée")
    print("✅ Logs détaillés pour l'historique des messages")
    print("✅ Distinction entre messages récents et anciens")
    
    print("\n🔍 Exemples de logs attendus:")
    print("-" * 30)
    print("📋 Audit log trouvé: Commande='config' | Utilisateur: Alice | Temps: 8.7s")
    print("❌ Pas un bump: Commande 'config' - Utilisateur: Alice")
    print("📋 Audit log trouvé: Commande='bump' | Utilisateur: JohnDoe | Temps: 15.2s")
    print("🎯 ✅ Commande /bump trouvée dans l'audit log - Utilisateur: JohnDoe")

if __name__ == "__main__":
    main()
