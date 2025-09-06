import discord
from .command_logger import log_command_usage
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio

class Feedback(commands.Cog):
    """Feedback collection system for bot improvement"""

    def __init__(self, bot):
        self.bot = bot
        self.feedback_channel_id = None  # Set this to your feedback channel ID
        
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
            title=f"📝 New Feedback - {type.title()}",
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add user info
        embed.add_field(
            name="👤 User Info",
            value=f"**User:** {interaction.user.mention} ({interaction.user.id})\n"
                  f"**Server:** {interaction.guild.name} ({interaction.guild.id})\n"
                  f"**Members:** {interaction.guild.member_count}",
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
            text=f"{type_emojis.get(type, '📝')} Feedback from {interaction.user.display_name}",
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
        
        # Also log to console for development
        print(f"📝 FEEDBACK ({type.upper()}): {message} - From {interaction.user} in {interaction.guild.name}")
        
        # Confirm to user
        thank_you_embed = discord.Embed(
            title="✅ Feedback Submitted!",
            description="Thank you for your feedback! This helps us improve Maybee.",
            color=discord.Color.green()
        )
        
        if type == "bug":
            thank_you_embed.add_field(
                name="🐛 Bug Reports",
                value="We'll investigate this issue and work on a fix. Thanks for helping us improve!",
                inline=False
            )
        elif type == "feature":
            thank_you_embed.add_field(
                name="💡 Feature Requests", 
                value="We'll consider this feature for future updates. Great suggestion!",
                inline=False
            )
        elif type == "question":
            thank_you_embed.add_field(
                name="❓ Questions",
                value="We'll try to get back to you soon. Check our documentation at github.com/imutig/Maybee",
                inline=False
            )
        
        await interaction.response.send_message(embed=thank_you_embed, ephemeral=True)
    
    @app_commands.command(name="suggest", description="Quick feature suggestion")
    @app_commands.describe(suggestion="What feature would you like to see?")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        """Quick suggestion shortcut"""
        
        embed = discord.Embed(
            title="💡 Feature Suggestion",
            description=suggestion,
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Suggested by",
            value=f"{interaction.user.mention} in {interaction.guild.name}",
            inline=False
        )
        
        # Log suggestion
        print(f"💡 SUGGESTION: {suggestion} - From {interaction.user} in {interaction.guild.name}")
        
        # Send to feedback channel if configured
        if self.feedback_channel_id:
            try:
                feedback_channel = self.bot.get_channel(self.feedback_channel_id)
                if feedback_channel:
                    await feedback_channel.send(embed=embed)
            except:
                pass
        
        await interaction.response.send_message(
            "💡 Thanks for the suggestion! We'll consider it for future updates.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Feedback(bot))
