import discord
from discord import app_commands
from discord.ext import commands


class Rename(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="rename",
        description="Renomme un membre (tu dois avoir la permission)")
    @app_commands.describe(user="Le membre à renommer",
                           new_nickname="Le nouveau pseudo")
    async def rename(self, interaction: discord.Interaction,
                     user: discord.Member, new_nickname: str):
        if not interaction.user.guild_permissions.manage_nicknames:
            await interaction.response.send_message(
                "❌ Tu n'as pas la permission de changer des pseudos.",
                ephemeral=True)
            return

        try:
            await user.edit(nick=new_nickname)
            await interaction.response.send_message(
                f"✅ {user.mention} s'appelle maintenant **{new_nickname}**.")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission de modifier ce pseudo.",
                ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Erreur : {e}",
                                                    ephemeral=True)


async def setup(bot):
    await bot.add_cog(Rename(bot))
