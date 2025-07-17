import discord
from discord import app_commands
from discord.ext import commands
from i18n import _


class Clear(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear",
                          description="Delete messages from the channel")
    @app_commands.describe(nombre="Number of messages to delete (max 100)")
    async def clear(self, interaction: discord.Interaction, nombre: int):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                _("commands.clear.no_permission", user_id, guild_id),
                ephemeral=True)
            return
        if nombre < 1 or nombre > 100:
            await interaction.response.send_message(
                _("commands.clear.invalid_number", user_id, guild_id), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=nombre)
        await interaction.followup.send(
            _("commands.clear.success", user_id, guild_id, count=len(deleted)), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Clear(bot))
