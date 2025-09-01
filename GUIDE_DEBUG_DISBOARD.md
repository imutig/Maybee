# Guide de Debugging du Système Disboard

## 🎯 Objectif

Ce guide explique comment utiliser le système de debugging ajouté au cog `disboard_reminder.py` pour diagnostiquer les problèmes de détection des bumps Disboard.

## 🔧 Configuration du Debugging

### 1. Niveau de Log

Pour activer le debugging, assurez-vous que le niveau de log est configuré sur `DEBUG` dans votre bot :

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Redémarrage du Bot

Après avoir modifié le niveau de log, **redémarrez votre bot** pour que les changements prennent effet.

## 📋 Messages de Debug Disponibles

### Messages de Base

Chaque message reçu par le bot génère ces logs :

```
🔍 Message reçu - Auteur: [nom] (ID: [id]) | Contenu: '[contenu]' | Serveur: [serveur]
🤖 Ce message provient-t-il de Disboard ? [Oui/Non] (ID attendu: [id], ID reçu: [id])
```

### Messages de Détection de Bump

Si le message provient de Disboard, ces logs supplémentaires apparaissent :

```
🎯 S'agit-il d'un message de bump ? [Oui/Non] | Pattern: '[pattern]' | User ID: [id]
```

### Messages de Traitement

Si un bump est détecté, ces logs de traitement apparaissent :

```
🚀 Bump détecté ! Utilisateur: [nom] (ID: [id]) | Serveur: [serveur]
🔄 Traitement du bump détecté - Serveur: [serveur] | Utilisateur: [nom] | Canal: [canal]
📊 Recherche du dernier bump pour le serveur [id]
✅ Nouveau bump créé - Count: [nombre]
📤 Envoi de l'embed de confirmation de bump
✅ Embed de confirmation envoyé dans #[canal]
📤 Envoi du message de remerciement
💬 Préparation du message de remerciement pour [nom]
🔧 Récupération de la configuration du serveur [id]
```

### Messages de Configuration

Selon la configuration du serveur :

```
❌ Aucun rôle de bump configuré pour le serveur [id]
✅ Message de remerciement simple envoyé (pas de rôle configuré)
```

ou

```
✅ L'utilisateur [nom] a déjà le rôle [rôle]
✅ Message de remerciement envoyé (utilisateur a déjà le rôle)
```

ou

```
🎯 Création du message avec proposition de rôle pour [nom]
✅ Message avec proposition de rôle envoyé (Message ID: [id])
💾 Informations du message stockées pour [id]
```

## 🔍 Diagnostic des Problèmes

### Problème 1 : Aucun message de debug n'apparaît

**Cause possible :** Le bot n'a pas les permissions de lecture des messages
**Solution :** Vérifiez que le bot a la permission "Lire les messages" dans le canal

### Problème 2 : "Ce message provient-t-il de Disboard ? Non"

**Cause possible :** Le bot Disboard n'est pas présent sur le serveur
**Solution :** Vérifiez que le bot Disboard (ID: 302050872383242240) est sur votre serveur

### Problème 3 : "S'agit-il d'un message de bump ? Non"

**Cause possible :** Le message de Disboard n'a pas le format attendu
**Solution :** Vérifiez le contenu exact du message de Disboard dans les logs

### Problème 4 : "Bump détecté" mais pas de traitement

**Cause possible :** Erreur dans la base de données ou permissions
**Solution :** Vérifiez les logs d'erreur et les permissions du bot

## 📊 Exemple de Logs Complets

```
2025-09-01 18:22:10,129 - DEBUG - 🔍 Message reçu - Auteur: Disboard (ID: 302050872383242240) | Contenu: '<@!123456789> bumped the server!' | Serveur: Mon Serveur
2025-09-01 18:22:10,129 - DEBUG - 🤖 Ce message provient-t-il de Disboard ? ✅ Oui (ID attendu: 302050872383242240, ID reçu: 302050872383242240)
2025-09-01 18:22:10,130 - DEBUG - 🎯 S'agit-il d'un message de bump ? ✅ Oui | Pattern: '<@!?(\d+)> bumped the server!' | User ID: 123456789
2025-09-01 18:22:10,130 - INFO - 🚀 Bump détecté ! Utilisateur: MonUtilisateur (ID: 123456789) | Serveur: Mon Serveur
2025-09-01 18:22:10,130 - INFO - 🔄 Traitement du bump détecté - Serveur: Mon Serveur | Utilisateur: MonUtilisateur | Canal: #général
2025-09-01 18:22:10,130 - DEBUG - 📊 Recherche du dernier bump pour le serveur 987654321
2025-09-01 18:22:10,130 - INFO - ✅ Nouveau bump créé - Count: 1
2025-09-01 18:22:10,130 - DEBUG - 📤 Envoi de l'embed de confirmation de bump
2025-09-01 18:22:10,130 - INFO - ✅ Embed de confirmation envoyé dans #général
2025-09-01 18:22:10,130 - DEBUG - 📤 Envoi du message de remerciement
2025-09-01 18:22:10,130 - DEBUG - 💬 Préparation du message de remerciement pour MonUtilisateur
2025-09-01 18:22:10,130 - DEBUG - 🔧 Récupération de la configuration du serveur 987654321
2025-09-01 18:22:10,130 - DEBUG - ❌ Aucun rôle de bump configuré pour le serveur 987654321
2025-09-01 18:22:10,130 - INFO - ✅ Message de remerciement simple envoyé (pas de rôle configuré)
2025-09-01 18:22:10,130 - INFO - 🎉 Bump traité avec succès dans Mon Serveur par MonUtilisateur (ID: 123456789)
```

## 🛠️ Actions Recommandées

1. **Activez le debugging** en configurant le niveau de log sur DEBUG
2. **Redémarrez votre bot** pour charger les nouveaux logs
3. **Effectuez un bump** avec Disboard sur votre serveur
4. **Vérifiez les logs** pour voir le processus complet
5. **Identifiez le problème** en comparant avec les exemples ci-dessus

## 📝 Notes Importantes

- Les messages de debug sont très verbeux, utilisez-les uniquement pour le diagnostic
- En production, remettez le niveau de log sur INFO ou WARNING
- Les emojis dans les logs peuvent causer des problèmes d'encodage sur certains systèmes
- Le fichier de log peut devenir très volumineux avec le debugging activé

## 🔧 Scripts de Test

Utilisez les scripts de test fournis pour vérifier le fonctionnement :

- `test_debug_simple.py` : Test simple du système de debugging
- `test_bump_detection.py` : Test des patterns de détection
- `diagnostic_disboard.py` : Diagnostic complet du système

Ces scripts vous aideront à identifier rapidement les problèmes sans avoir à effectuer de vrais bumps.
