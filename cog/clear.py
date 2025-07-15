import discord
from discord import app_commands
from discord.ext import commands


class Clear(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear",
                          description="Supprime les messages du canal.")
    @app_commands.describe(nombre="Nombre de messages à supprimer (max 100)")
    async def clear(self, interaction: discord.Interaction, nombre: int):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Tu n'as pas la permission de gérer les messages.",
                ephemeral=True)
            return
        if nombre < 1 or nombre > 100:
            await interaction.response.send_message(
                "❌ Le nombre doit être entre 1 et 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=nombre)
        await interaction.followup.send(
            f"🧹 {len(deleted)} messages supprimés.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Clear(bot))
