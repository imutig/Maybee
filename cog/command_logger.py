"""
Décorateur pour ajouter automatiquement le logging DM aux commandes
"""
import discord
from discord.ext import commands
from functools import wraps
from typing import Callable, Any


def log_command_usage(func: Callable) -> Callable:
    """
    Décorateur pour logger l'utilisation des commandes app_commands
    """
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        # Exécuter la commande originale
        result = await func(self, interaction, *args, **kwargs)
        
        # Logger l'utilisation si c'est une commande app_commands
        if hasattr(self, 'bot') and hasattr(self.bot, 'get_cog'):
            dm_logs_cog = self.bot.get_cog('DMLogsSystem')
            if dm_logs_cog and hasattr(dm_logs_cog, 'log_command_usage'):
                command_name = getattr(func, '__name__', 'unknown')
                await dm_logs_cog.log_command_usage(command_name, interaction.user, interaction.guild)
        
        return result
    
    return wrapper


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
