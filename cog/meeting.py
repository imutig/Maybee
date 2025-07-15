import discord
from discord import app_commands
from discord.ext import commands


class Meeting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meeting",
                          description="Créer un rappel de meeting")
    @app_commands.describe(
        meeting=
        "Qui est concerné par le meeting ? (mentionnez autant de monde que nécessaire)",
        par=
        "Qui organise le meeting ? (mentionnez autant de monde que nécessaire)",
        lieu="Salon vocal où se déroulera le meeting",
        note="Note optionnelle pour le meeting")
    async def meeting(self,
                      interaction: discord.Interaction,
                      meeting: str,
                      par: str,
                      lieu: discord.VoiceChannel,
                      note: str = "Aucune note spécifiée."):
        embed = discord.Embed(title="📢 Nouveau meeting planifié !",
                              color=discord.Color.blue())
        embed.add_field(name="👥 Participants", value=meeting, inline=False)
        embed.add_field(name="🧑‍💼 Organisé par", value=par, inline=False)
        embed.add_field(name="📍 Lieu", value=f"{lieu.mention}", inline=False)
        embed.add_field(name="📝 Note", value=note, inline=False)
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}",
                         icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(content=f"{meeting}",
                                                embed=embed)


async def setup(bot):
    await bot.add_cog(Meeting(bot))
