import discord
from discord import app_commands
from discord.ext import commands
from i18n import _
from .command_logger import log_command_usage


class Rename(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="rename",
        description="Rename a member (you need permission)")
    @app_commands.describe(user="The member to rename",
                           new_nickname="The new nickname")
    async def rename(self, interaction: discord.Interaction,
                     user: discord.Member, new_nickname: str):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        if not interaction.user.guild_permissions.manage_nicknames:
            await interaction.response.send_message(
                _("commands.rename.no_permission", user_id, guild_id),
                ephemeral=True)
            return

        try:
            await user.edit(nick=new_nickname)
            await interaction.response.send_message(
                _("commands.rename.success", user_id, guild_id, user=user.mention, nickname=new_nickname)
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                _("commands.rename.bot_no_permission", user_id, guild_id),
                ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                _("commands.rename.error", user_id, guild_id, error=str(e)),
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(Rename(bot))
