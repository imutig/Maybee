import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
import asyncio
from datetime import datetime, timedelta
from i18n import _
from validation import InputValidator
import logging

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
    """Moderation commands for server management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.validator = InputValidator()
        
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(
        member="The member to warn",
        reason="The reason for the warning"
    )
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Warn a member and log the warning"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                _("errors.no_permission", user_id, guild_id),
                ephemeral=True
            )
            return
            
        # Validate input
        if not self.validator.validate_user_id(member.id):
            await interaction.response.send_message(
                _("errors.invalid_input", user_id, guild_id),
                ephemeral=True
            )
            return
            
        # Check if trying to warn a bot or higher role
        if member.bot:
            await interaction.response.send_message(
                _("moderation.warn.cannot_warn_bot", user_id, guild_id),
                ephemeral=True
            )
            return
            
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                _("moderation.warn.cannot_warn_higher_role", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            # Log warning to database
            await self.bot.db.execute(
                """INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp)
                   VALUES (%s, %s, %s, %s, %s)""",
                (guild_id, member.id, user_id, reason, datetime.utcnow())
            )
            
            # Create warning embed
            embed = discord.Embed(
                title=_("moderation.warn.embed_title", user_id, guild_id),
                description=_("moderation.warn.embed_description", user_id, guild_id, 
                            user=member.mention, reason=reason),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name=_("moderation.warn.moderator_field", user_id, guild_id),
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name=_("moderation.warn.member_field", user_id, guild_id),
                value=member.mention,
                inline=True
            )
            embed.set_footer(text=f"ID: {member.id}")
            
            await interaction.response.send_message(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=_("moderation.warn.dm_title", user_id, guild_id),
                    description=_("moderation.warn.dm_description", user_id, guild_id,
                                server=interaction.guild.name, reason=reason),
                    color=discord.Color.orange()
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
                
        except Exception as e:
            logger.error(f"Error warning member: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
            
    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration in minutes (max 2880 = 48 hours)",
        reason="The reason for the timeout"
    )
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, 
                     duration: int, reason: str = "No reason provided"):
        """Timeout a member for a specified duration"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                _("errors.no_permission", user_id, guild_id),
                ephemeral=True
            )
            return
            
        # Validate duration (max 48 hours)
        if duration < 1 or duration > 2880:
            await interaction.response.send_message(
                _("moderation.timeout.invalid_duration", user_id, guild_id),
                ephemeral=True
            )
            return
            
        # Check if trying to timeout a bot or higher role
        if member.bot:
            await interaction.response.send_message(
                _("moderation.timeout.cannot_timeout_bot", user_id, guild_id),
                ephemeral=True
            )
            return
            
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                _("moderation.timeout.cannot_timeout_higher_role", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            # Calculate timeout duration
            timeout_until = datetime.utcnow() + timedelta(minutes=duration)
            
            # Apply timeout
            await member.edit(timed_out_until=timeout_until, reason=reason)
            
            # Log timeout to database
            await self.bot.db.execute(
                """INSERT INTO timeouts (guild_id, user_id, moderator_id, duration, reason, timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (guild_id, member.id, user_id, duration, reason, datetime.utcnow())
            )
            
            # Create timeout embed
            embed = discord.Embed(
                title=_("moderation.timeout.embed_title", user_id, guild_id),
                description=_("moderation.timeout.embed_description", user_id, guild_id,
                            user=member.mention, duration=duration, reason=reason),
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name=_("moderation.timeout.moderator_field", user_id, guild_id),
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name=_("moderation.timeout.duration_field", user_id, guild_id),
                value=_("moderation.timeout.duration_value", user_id, guild_id, duration=duration),
                inline=True
            )
            embed.set_footer(text=f"ID: {member.id}")
            
            await interaction.response.send_message(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=_("moderation.timeout.dm_title", user_id, guild_id),
                    description=_("moderation.timeout.dm_description", user_id, guild_id,
                                server=interaction.guild.name, duration=duration, reason=reason),
                    color=discord.Color.red()
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
                
        except discord.Forbidden:
            await interaction.response.send_message(
                _("errors.bot_missing_permissions", user_id, guild_id),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error timing out member: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
            
    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.describe(
        member="The member to remove timeout from",
        reason="The reason for removing the timeout"
    )
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, 
                       reason: str = "No reason provided"):
        """Remove timeout from a member"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                _("errors.no_permission", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            # Remove timeout
            await member.edit(timed_out_until=None, reason=reason)
            
            # Create success embed
            embed = discord.Embed(
                title=_("moderation.untimeout.embed_title", user_id, guild_id),
                description=_("moderation.untimeout.embed_description", user_id, guild_id,
                            user=member.mention, reason=reason),
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name=_("moderation.untimeout.moderator_field", user_id, guild_id),
                value=interaction.user.mention,
                inline=True
            )
            embed.set_footer(text=f"ID: {member.id}")
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                _("errors.bot_missing_permissions", user_id, guild_id),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error removing timeout: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
            
    @app_commands.command(name="warnings", description="View warnings for a member")
    @app_commands.describe(member="The member to view warnings for")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        """View warnings for a member"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                _("errors.no_permission", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            # Get warnings from database
            warnings = await self.bot.db.query(
                """SELECT moderator_id, reason, timestamp FROM warnings 
                   WHERE guild_id = %s AND user_id = %s 
                   ORDER BY timestamp DESC LIMIT 10""",
                (guild_id, member.id)
            )
            
            if not warnings:
                await interaction.response.send_message(
                    _("moderation.warnings.no_warnings", user_id, guild_id, user=member.mention),
                    ephemeral=True
                )
                return
                
            # Create warnings embed
            embed = discord.Embed(
                title=_("moderation.warnings.embed_title", user_id, guild_id, user=member.display_name),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            for i, warning in enumerate(warnings, 1):
                moderator = self.bot.get_user(warning[0])
                moderator_name = moderator.display_name if moderator else "Unknown"
                
                embed.add_field(
                    name=_("moderation.warnings.warning_field", user_id, guild_id, number=i),
                    value=_("moderation.warnings.warning_value", user_id, guild_id,
                           moderator=moderator_name, reason=warning[1], 
                           timestamp=warning[2].strftime("%Y-%m-%d %H:%M")),
                    inline=False
                )
                
            embed.set_footer(text=f"Total warnings: {len(warnings)}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error fetching warnings: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
            
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member")
    @app_commands.describe(member="The member to clear warnings for")
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        """Clear all warnings for a member"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions (only admins can clear warnings)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("errors.admin_only", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            # Clear warnings from database
            result = await self.bot.db.execute(
                "DELETE FROM warnings WHERE guild_id = %s AND user_id = %s",
                (guild_id, member.id)
            )
            
            await interaction.response.send_message(
                _("moderation.clearwarnings.success", user_id, guild_id, user=member.mention),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error clearing warnings: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
