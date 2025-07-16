import discord
from discord import app_commands
from discord.ext import commands
from i18n import _


class Career(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="career",
        description="Add a career decision for a member")
    @app_commands.describe(
        member="The member concerned",
        decision="Type of decision made",
        reason="The reason for this decision",
        decided_by=
        "Mention the roles that made the decision (separated by commas or spaces)"
    )
    @app_commands.choices(decision=[
        app_commands.Choice(name="Warning", value="warning"),
        app_commands.Choice(name="Blame", value="blame"),
        app_commands.Choice(name="Demotion", value="demotion"),
        app_commands.Choice(name="Promotion", value="promotion"),
        app_commands.Choice(name="Exclusion", value="exclusion")
    ])
    async def career(self, interaction: discord.Interaction,
                     member: discord.Member,
                     decision: app_commands.Choice[str], reason: str,
                     decided_by: str):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Get localized decision name
        decision_name = _(f"commands.career.decisions.{decision.value}", user_id, guild_id)
        
        embed = discord.Embed(
            title=_("commands.career.embed_title", user_id, guild_id),
            color=discord.Color.orange()
        )
        embed.add_field(
            name=_("commands.career.member_field", user_id, guild_id), 
            value=member.mention, inline=False
        )
        embed.add_field(
            name=_("commands.career.decision_field", user_id, guild_id), 
            value=decision_name, inline=False
        )
        embed.add_field(
            name=_("commands.career.reason_field", user_id, guild_id), 
            value=reason, inline=False
        )
        embed.add_field(
            name=_("commands.career.decided_by_field", user_id, guild_id), 
            value=decided_by, inline=False
        )
        embed.set_footer(
            text=_("commands.career.footer", user_id, guild_id, user=interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(content=member.mention, embed=embed)


async def setup(bot):
    await bot.add_cog(Career(bot))
