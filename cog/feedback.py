import discord
from .command_logger import log_command_usage
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
from i18n import _

class Feedback(commands.Cog):
    """Feedback collection system for bot improvement"""

    def __init__(self, bot):
        self.bot = bot
        self.feedback_channel_id = None  # Set this to your feedback channel ID
        self.owner_id = 263679048712978432  # Owner ID for DM feedback
        
    @app_commands.command(name="feedback", description="Send feedback about the bot to the developers")
    @app_commands.describe(
        type="Type of feedback",
        message="Your detailed feedback"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🐛 Bug Report", value="bug"),
        app_commands.Choice(name="💡 Feature Request", value="feature"),
        app_commands.Choice(name="⭐ General Feedback", value="general"),
        app_commands.Choice(name="❓ Question/Help", value="question")
    ])
    async def feedback(self, interaction: discord.Interaction, type: str, message: str):
        """Submit feedback to developers"""
        
        # Create feedback embed
        embed = discord.Embed(
            title=f"📝 {_('feedback.new_feedback', interaction.user.id, interaction.guild.id)} - {_('feedback.types.' + type, interaction.user.id, interaction.guild.id)}",
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add user info
        embed.add_field(
            name=f"👤 {_('feedback.user_info', interaction.user.id, interaction.guild.id)}",
            value=f"**{_('feedback.user', interaction.user.id, interaction.guild.id)}:** {interaction.user.mention} ({interaction.user.id})\n"
                  f"**{_('feedback.server', interaction.user.id, interaction.guild.id)}:** {interaction.guild.name} ({interaction.guild.id})\n"
                  f"**{_('feedback.members', interaction.user.id, interaction.guild.id)}:** {interaction.guild.member_count}",
            inline=False
        )
        
        # Add type-specific emoji
        type_emojis = {
            "bug": "🐛",
            "feature": "💡",
            "general": "⭐",
            "question": "❓"
        }
        
        embed.set_footer(
            text=f"{type_emojis.get(type, '📝')} {_('feedback.footer', interaction.user.id, interaction.guild.id, user=interaction.user.display_name)}",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Send to feedback channel (if configured)
        if self.feedback_channel_id:
            try:
                feedback_channel = self.bot.get_channel(self.feedback_channel_id)
                if feedback_channel:
                    await feedback_channel.send(embed=embed)
            except:
                pass
        
        # Send DM to owner
        try:
            owner = self.bot.get_user(self.owner_id)
            if owner:
                await owner.send(embed=embed)
        except Exception as e:
            print(f"❌ Failed to send feedback DM to owner: {e}")
        
        # Also log to console for development
        print(f"📝 FEEDBACK ({type.upper()}): {message} - From {interaction.user} in {interaction.guild.name}")
        
        # Confirm to user
        thank_you_embed = discord.Embed(
            title=f"✅ {_('feedback.submitted', interaction.user.id, interaction.guild.id)}",
            description=_('feedback.thank_you', interaction.user.id, interaction.guild.id),
            color=discord.Color.green()
        )
        
        if type == "bug":
            thank_you_embed.add_field(
                name=f"🐛 {_('feedback.bug_reports', interaction.user.id, interaction.guild.id)}",
                value=_('feedback.bug_message', interaction.user.id, interaction.guild.id),
                inline=False
            )
        elif type == "feature":
            thank_you_embed.add_field(
                name=f"💡 {_('feedback.feature_requests', interaction.user.id, interaction.guild.id)}", 
                value=_('feedback.feature_message', interaction.user.id, interaction.guild.id),
                inline=False
            )
        elif type == "question":
            thank_you_embed.add_field(
                name=f"❓ {_('feedback.questions', interaction.user.id, interaction.guild.id)}",
                value=_('feedback.question_message', interaction.user.id, interaction.guild.id),
                inline=False
            )
        
        await interaction.response.send_message(embed=thank_you_embed, ephemeral=True)
    
    # suggest command removed - use /feedback instead

async def setup(bot):
    await bot.add_cog(Feedback(bot))
