import discord
from discord.ext import commands
import re
import logging

logger = logging.getLogger(__name__)


class FeurMode(commands.Cog):
    """
    Cog pour le mode Feur - répond "Feur" aux messages contenant "quoi"
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Variations possibles de "quoi" à détecter
        self.quoi_patterns = [
            r'\bquoi\b',
            r'\bkoi\b',
            r'\bkwa\b',
            r'\bquoa\b',
            r'\bkoa\b',
            r'\bquoii+\b',
            r'\bkoii+\b',
            r'\bquoi\?+',
            r'\bkoi\?+',
            r'\bquoi\!+',
            r'\bkoi\!+',
        ]
        
        # Compiler les patterns pour la performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.quoi_patterns]
    
    async def is_feur_mode_enabled(self, guild_id: int) -> bool:
        """Check if Feur mode is enabled for a guild"""
        try:
            result = await self.bot.db.query(
                "SELECT enabled FROM feur_mode WHERE guild_id = %s",
                (str(guild_id),),
                fetchone=True
            )
            return bool(result['enabled']) if result else False
        except Exception as e:
            logger.error(f"Error checking feur mode status: {e}")
            return False
    
    def message_ends_with_quoi(self, content: str) -> bool:
        """Check if message ends with a variation of 'quoi'"""
        # Nettoyer le message des espaces et ponctuation à la fin
        cleaned = content.strip().rstrip('?!.,;:')
        
        # Vérifier si le message se termine par une variation de "quoi"
        for pattern in self.compiled_patterns:
            # Chercher à la fin du message
            matches = list(pattern.finditer(cleaned))
            if matches:
                # Vérifier si le dernier match est à la fin du message
                last_match = matches[-1]
                if last_match.end() == len(cleaned):
                    return True
        
        return False
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages ending with 'quoi' and respond with Feur gif"""
        # Ignorer les messages du bot et les DMs
        if message.author.bot or not message.guild:
            return
        
        # Vérifier si le mode Feur est activé pour ce serveur
        if not await self.is_feur_mode_enabled(message.guild.id):
            return
        
        # Vérifier si le message se termine par "quoi" ou une variation
        if self.message_ends_with_quoi(message.content):
            try:
                # Répondre avec "Feur !"
                await message.reply("Feur !", mention_author=False)
                logger.info(f"Feur mode triggered in {message.guild.name} by {message.author}")
            except discord.Forbidden:
                logger.warning(f"Missing permissions to send Feur in {message.guild.name}")
            except Exception as e:
                logger.error(f"Error sending Feur response: {e}")


async def setup(bot):
    await bot.add_cog(FeurMode(bot))
