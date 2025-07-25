import discord
from discord.ext import commands
from discord import app_commands
from i18n import _

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Show bot latency")
    async def ping(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        latency = round(self.bot.latency * 1000)
        message = _("commands.ping.response", user_id, guild_id, latency=latency)
        await interaction.response.send_message(message)

async def setup(bot):
    await bot.add_cog(Ping(bot))
