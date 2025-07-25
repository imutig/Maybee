import discord
from discord.ext import commands
from discord import app_commands
from i18n import _


class Avatar(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar",
                          description="Show a user's avatar")
    @app_commands.describe(user="The user whose avatar you want to see")
    async def avatar(self,
                     interaction: discord.Interaction,
                     user: discord.Member = None):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        user = user or interaction.user
        
        title = _("commands.avatar.embed_title", user_id, guild_id, user=user.display_name)
        embed = discord.Embed(title=title, color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Avatar(bot))
