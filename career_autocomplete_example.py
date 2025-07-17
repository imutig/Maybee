import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from i18n import _


class CareerWithAutocomplete(commands.Cog):
    """
    Enhanced Career command with autocomplete for translated decision names
    This allows users to see localized decision names while typing
    """

    def __init__(self, bot):
        self.bot = bot

    async def decision_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete function that provides translated decision names"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Define the decision options with their translation keys
        decisions = [
            ("warning", "commands.career.decisions.warning"),
            ("blame", "commands.career.decisions.blame"),
            ("demotion", "commands.career.decisions.demotion"),
            ("promotion", "commands.career.decisions.promotion"),
            ("exclusion", "commands.career.decisions.exclusion")
        ]
        
        # Create choices with translated names
        choices = []
        for value, translation_key in decisions:
            translated_name = _(translation_key, user_id, guild_id)
            choices.append(app_commands.Choice(name=translated_name, value=value))
        
        # Filter choices based on current input
        if not current:
            return choices
        
        # Return choices that match the current input
        return [
            choice for choice in choices 
            if current.lower() in choice.name.lower()
        ]

    @app_commands.command(
        name="career_enhanced",
        description="Add a career decision for a member (with autocomplete)"
    )
    @app_commands.describe(
        member="The member concerned",
        decision="Type of decision made (start typing to see options)",
        reason="The reason for this decision",
        decided_by="Mention the roles that made the decision"
    )
    @app_commands.autocomplete(decision=decision_autocomplete)
    async def career_enhanced(self, interaction: discord.Interaction,
                            member: discord.Member,
                            decision: str,
                            reason: str,
                            decided_by: str):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Validate the decision value
        valid_decisions = ["warning", "blame", "demotion", "promotion", "exclusion"]
        if decision not in valid_decisions:
            await interaction.response.send_message(
                _("commands.career.invalid_decision", user_id, guild_id),
                ephemeral=True
            )
            return
        
        # Get localized decision name
        decision_name = _(f"commands.career.decisions.{decision}", user_id, guild_id)
        
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
    await bot.add_cog(CareerWithAutocomplete(bot))
