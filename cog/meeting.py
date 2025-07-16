import discord
from discord import app_commands
from discord.ext import commands
from i18n import _


class Meeting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meeting",
                          description="Create a meeting reminder")
    @app_commands.describe(
        meeting=
        "Who is concerned by the meeting? (mention as many people as necessary)",
        par=
        "Who organizes the meeting? (mention as many people as necessary)",
        lieu="Voice channel where the meeting will take place",
        note="Optional note for the meeting")
    async def meeting(self,
                      interaction: discord.Interaction,
                      meeting: str,
                      par: str,
                      lieu: discord.VoiceChannel,
                      note: str = None):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        if note is None:
            note = _("commands.meeting.no_note", user_id, guild_id)
        
        embed = discord.Embed(
            title=_("commands.meeting.embed_title", user_id, guild_id),
            color=discord.Color.blue()
        )
        embed.add_field(
            name=_("commands.meeting.participants_field", user_id, guild_id), 
            value=meeting, inline=False
        )
        embed.add_field(
            name=_("commands.meeting.organized_by_field", user_id, guild_id), 
            value=par, inline=False
        )
        embed.add_field(
            name=_("commands.meeting.location_field", user_id, guild_id), 
            value=f"{lieu.mention}", inline=False
        )
        embed.add_field(
            name=_("commands.meeting.note_field", user_id, guild_id), 
            value=note, inline=False
        )
        embed.set_footer(
            text=_("commands.meeting.footer", user_id, guild_id, user=interaction.user.display_name),
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(content=f"{meeting}", embed=embed)


async def setup(bot):
    await bot.add_cog(Meeting(bot))
