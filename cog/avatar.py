import discord
from discord.ext import commands
from discord import app_commands


class Avatar(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar",
                          description="Affiche l'avatar d'un utilisateur")
    @app_commands.describe(user="L'utilisateur dont tu veux voir l'avatar")
    async def avatar(self,
                     interaction: discord.Interaction,
                     user: discord.Member = None):
        user = user or interaction.user
        embed = discord.Embed(title=f"Avatar de {user}",
                              color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Avatar(bot))
