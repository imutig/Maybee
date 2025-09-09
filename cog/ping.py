import discord
from discord.ext import commands
from discord import app_commands
from i18n import _
from .command_logger import log_command_usage
from custom_emojis import PING

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Show bot latency")
    @log_command_usage
    async def ping(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        latency = round(self.bot.latency * 1000)
        message = f"{PING} Pong ! {latency} ms"
        await interaction.response.send_message(message)

async def setup(bot):
    await bot.add_cog(Ping(bot))
