import discord
from discord.ext import commands
from discord import app_commands
import random
from i18n import _
from .command_logger import log_command_usage


class Roll(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll",
                          description="Roll a dice between 1 and 100")
    @log_command_usage
    async def roll(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        result = random.randint(1, 100)
        message = _("commands.roll.result", user_id, guild_id, 
                   user=interaction.user.mention, result=result)
        await interaction.response.send_message(message)


async def setup(bot):
    await bot.add_cog(Roll(bot))
