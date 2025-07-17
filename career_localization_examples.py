import discord
from discord import app_commands
from discord.ext import commands
from i18n import _


class CareerAdvanced(commands.Cog):
    """
    Advanced version of Career command with Discord's built-in localization
    
    NOTE: This approach has limitations:
    1. Only works with Discord's supported locales (not custom server languages)
    2. Requires more complex setup
    3. User must have their Discord client set to the target language
    """

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="career_advanced",
        description="Add a career decision for a member"
    )
    @app_commands.describe(
        member="The member concerned",
        decision="Type of decision made",
        reason="The reason for this decision",
        decided_by="Mention the roles that made the decision"
    )
    @app_commands.choices(decision=[
        app_commands.Choice(name="Warning", value="warning"),
        app_commands.Choice(name="Blame", value="blame"),
        app_commands.Choice(name="Demotion", value="demotion"),
        app_commands.Choice(name="Promotion", value="promotion"),
        app_commands.Choice(name="Exclusion", value="exclusion")
    ])
    async def career_advanced(self, interaction: discord.Interaction,
                            member: discord.Member,
                            decision: app_commands.Choice[str], 
                            reason: str,
                            decided_by: str):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Get localized decision name (this works for the embed content)
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


class CareerDynamic(commands.Cog):
    """
    Dynamic version using subcommands - this allows for more flexibility
    but changes the command structure
    """

    def __init__(self, bot):
        self.bot = bot

    career_group = app_commands.Group(name="career", description="Career decision commands")

    @career_group.command(name="warning", description="Add a warning decision")
    @app_commands.describe(
        member="The member concerned",
        reason="The reason for this decision",
        decided_by="Who made the decision"
    )
    async def career_warning(self, interaction: discord.Interaction,
                           member: discord.Member, reason: str, decided_by: str):
        await self._create_career_decision(interaction, member, "warning", reason, decided_by)

    @career_group.command(name="promotion", description="Add a promotion decision") 
    @app_commands.describe(
        member="The member concerned",
        reason="The reason for this decision",
        decided_by="Who made the decision"
    )
    async def career_promotion(self, interaction: discord.Interaction,
                             member: discord.Member, reason: str, decided_by: str):
        await self._create_career_decision(interaction, member, "promotion", reason, decided_by)

    @career_group.command(name="demotion", description="Add a demotion decision")
    @app_commands.describe(
        member="The member concerned", 
        reason="The reason for this decision",
        decided_by="Who made the decision"
    )
    async def career_demotion(self, interaction: discord.Interaction,
                            member: discord.Member, reason: str, decided_by: str):
        await self._create_career_decision(interaction, member, "demotion", reason, decided_by)

    async def _create_career_decision(self, interaction: discord.Interaction, 
                                    member: discord.Member, decision_type: str,
                                    reason: str, decided_by: str):
        """Helper method to create career decision embed"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Get localized decision name
        decision_name = _(f"commands.career.decisions.{decision_type}", user_id, guild_id)
        
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
    # Choose which implementation to use:
    # await bot.add_cog(CareerAdvanced(bot))  # Advanced with Discord localization
    # await bot.add_cog(CareerDynamic(bot))  # Dynamic subcommand approach
    pass  # This file is for reference only
