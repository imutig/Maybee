"""
Décorateur pour ajouter automatiquement le logging DM aux commandes
"""
import discord
from discord.ext import commands
from functools import wraps
from typing import Callable, Any
import asyncio


def log_command_usage(func: Callable) -> Callable:
    """
    Décorateur pour logger l'utilisation des commandes app_commands
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        print(f"🔍 [COMMAND LOGGER] Décorateur appelé pour la fonction: {func.__name__}")
        print(f"🔍 [COMMAND LOGGER] Arguments reçus: {len(args)} args, {len(kwargs)} kwargs")
        
        # Trouver l'interaction dans les arguments pour récupérer les détails avant exécution
        interaction = None
        bot_instance = None
        
        for i, arg in enumerate(args):
            print(f"🔍 [COMMAND LOGGER] Arg {i}: {type(arg)}")
            if isinstance(arg, discord.Interaction):
                interaction = arg
                print(f"🔍 [COMMAND LOGGER] Interaction trouvée: {interaction.command.name if interaction.command else 'No command'}")
            elif hasattr(arg, 'bot'):  # Si c'est un cog, récupérer le bot
                bot_instance = arg.bot
                print(f"🔍 [COMMAND LOGGER] Bot trouvé via cog: {bot_instance is not None}")
        
        # Exécuter la commande originale
        result = await func(*args, **kwargs)
        
        print(f"🔍 [COMMAND LOGGER] Commande exécutée, maintenant logging...")
        
        if not interaction:
            print(f"❌ [COMMAND LOGGER] Interaction non trouvée dans les arguments")
            return result
        
        # Logger l'utilisation si c'est une commande app_commands
        try:
            if not bot_instance:
                # Fallback: essayer d'importer le bot global
                from main import bot
                bot_instance = bot
                print(f"🔍 [COMMAND LOGGER] Bot importé depuis main: {bot_instance is not None}")
            
            print(f"🔍 [COMMAND LOGGER] Bot instance: {bot_instance is not None}")
            print(f"🔍 [COMMAND LOGGER] Cogs disponibles: {list(bot_instance.cogs.keys())}")
            
            dm_logs_cog = bot_instance.get_cog('DMLogsSystem')
            print(f"🔍 [COMMAND LOGGER] DMLogsSystem cog trouvé: {dm_logs_cog is not None}")
            if dm_logs_cog and hasattr(dm_logs_cog, 'log_command_usage'):
                # Essayer de récupérer le nom de la commande depuis l'interaction
                command_name = interaction.command.name if interaction.command else func.__name__
                print(f"🔍 [COMMAND LOGGER] Logging command: {command_name}")
                
                # Récupérer les détails supplémentaires spécifiques à la commande
                extra_details = await _get_command_details(func.__name__, interaction, args, kwargs, result)
                
                await dm_logs_cog.log_command_usage(command_name, interaction.user, interaction.guild, extra_details)
            else:
                print(f"❌ [COMMAND LOGGER] DMLogsSystem cog non trouvé ou méthode manquante")
        except Exception as e:
            print(f"❌ [COMMAND LOGGER] Erreur lors du logging: {e}")
        
        return result
    
    return wrapper


async def _get_command_details(command_name: str, interaction: discord.Interaction, args: tuple, kwargs: dict, result) -> dict:
    """
    Récupère les détails supplémentaires spécifiques à chaque commande
    """
    details = {}
    
    try:
        if command_name == "clear":
            # Pour clear: nombre de messages et canal
            if len(args) >= 2:  # self, interaction, nombre
                nombre = args[2] if len(args) > 2 else kwargs.get('nombre', 'N/A')
                details = {
                    "messages_deleted": nombre,
                    "channel": interaction.channel.name if interaction.channel else "N/A",
                    "channel_id": interaction.channel.id if interaction.channel else None
                }
        
        elif command_name == "warn":
            # Pour warn: membre warn et raison
            if len(args) >= 3:  # self, interaction, member
                member = args[2] if len(args) > 2 else kwargs.get('member', None)
                reason = kwargs.get('reason', 'Aucune raison spécifiée')
                details = {
                    "warned_user": member.display_name if member else "N/A",
                    "reason": reason
                }
        
        elif command_name == "timeout":
            # Pour timeout: membre, durée et raison
            if len(args) >= 3:
                member = args[2] if len(args) > 2 else kwargs.get('member', None)
                duration = kwargs.get('duration', 'N/A')
                reason = kwargs.get('reason', 'Aucune raison spécifiée')
                details = {
                    "timed_out_user": member.display_name if member else "N/A",
                    "duration_minutes": duration,
                    "reason": reason
                }
        
        elif command_name == "career":
            # Pour career: membre, décision et raison
            if len(args) >= 3:
                member = args[2] if len(args) > 2 else kwargs.get('member', None)
                decision = kwargs.get('decision', 'N/A')
                reason = kwargs.get('reason', 'N/A')
                details = {
                    "target_user": member.display_name if member else "N/A",
                    "decision": decision,
                    "reason": reason
                }
        
        elif command_name == "confession":
            # Pour confession: longueur du message
            message = kwargs.get('message', '')
            details = {
                "message_length": len(message),
                "channel": interaction.channel.name if interaction.channel else "N/A"
            }
        
        print(f"🔍 [COMMAND LOGGER] Détails extraits pour {command_name}: {details}")
        
    except Exception as e:
        print(f"❌ [COMMAND LOGGER] Erreur lors de l'extraction des détails: {e}")
    
    return details


def add_logging_to_command(cog_class):
    """
    Ajoute automatiquement le logging à toutes les commandes app_commands d'un cog
    """
    original_setup = cog_class.setup if hasattr(cog_class, 'setup') else None
    
    @classmethod
    async def setup_with_logging(cls, bot):
        # Charger le cog normalement
        cog_instance = cls(bot)
        
        # Ajouter le logging à toutes les commandes app_commands
        for attr_name in dir(cog_instance):
            attr = getattr(cog_instance, attr_name)
            if hasattr(attr, '__name__') and hasattr(attr, '__annotations__'):
                # Vérifier si c'est une commande app_commands
                if hasattr(attr, '_callback') or (hasattr(attr, '__wrapped__') and 'interaction' in str(attr.__annotations__)):
                    # Appliquer le décorateur de logging
                    setattr(cog_instance, attr_name, log_command_usage(attr))
        
        await bot.add_cog(cog_instance)
    
    # Remplacer la méthode setup
    cog_class.setup = setup_with_logging
    return cog_class
