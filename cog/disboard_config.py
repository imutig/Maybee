"""
Disboard Configuration System for Maybee
Allows server administrators to configure bump reminders and notifications
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timezone
from i18n import _
from .command_logger import log_command_usage

# Services and monitoring modules removed during cleanup
import logging
logger = logging.getLogger(__name__)

class DisboardConfig(commands.Cog):
    """Configuration system for Disboard bump reminders"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="disboard", description="Configure Disboard reminder system")
    @app_commands.describe(
        action="Action to perform (setup/status/reset)",
        channel="Channel for reminders (optional)",
        role="Role to ping for reminders (optional)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="setup", value="setup"),
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="reset", value="reset")
    ])
    async def disboard_config(self, interaction: discord.Interaction, action: str, channel: Optional[discord.TextChannel] = None, role: Optional[discord.Role] = None):
        """Configure Disboard reminder system"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("errors.admin_only", interaction.guild_id),
                ephemeral=True
            )
            return
        
        try:
            guild_id = interaction.guild.id
            
            if action == "setup":
                await self._setup_disboard(interaction, guild_id, channel, role)
            elif action == "status":
                await self._show_status(interaction, guild_id)
            elif action == "reset":
                await self._reset_config(interaction, guild_id)
            else:
                await interaction.response.send_message(
                    _("commands.disboard.invalid_action", guild_id=guild_id),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in disboard config command: {e}")
            await interaction.response.send_message(
                _("commands.disboard.setup_error", guild_id=guild_id),
                ephemeral=True
            )
    
    async def _setup_disboard(self, interaction: discord.Interaction, guild_id: int, channel: Optional[discord.TextChannel], role: Optional[discord.Role]):
        """Setup Disboard configuration for the server"""
        try:
            # Use provided channel or current channel
            reminder_channel = channel or interaction.channel
            
            # Check if configuration already exists
            existing_config = await self.bot.db.query(
                "SELECT * FROM disboard_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            
            if existing_config:
                # Update existing configuration
                await self.bot.db.query(
                    """UPDATE disboard_config 
                       SET reminder_channel_id = %s, bump_role_id = %s, updated_at = %s
                       WHERE guild_id = %s""",
                    (reminder_channel.id, role.id if role else None, datetime.now(), guild_id)
                )
                action = _("commands.disboard.setup_updated", guild_id=guild_id)
            else:
                # Create new configuration
                await self.bot.db.query(
                    """INSERT INTO disboard_config 
                       (guild_id, reminder_channel_id, bump_role_id, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (guild_id, reminder_channel.id, role.id if role else None, datetime.now(), datetime.now())
                )
                action = _("commands.disboard.setup_created", guild_id=guild_id)
            
            # Create confirmation embed
            embed = discord.Embed(
                title=_("commands.disboard.title", guild_id=guild_id),
                description=_("commands.disboard.setup_success", guild_id=guild_id, action=action),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name=_("commands.disboard.reminder_channel", guild_id=guild_id), 
                value=reminder_channel.mention, 
                inline=True
            )
            if role:
                embed.add_field(
                    name=_("commands.disboard.bump_role", guild_id=guild_id), 
                    value=role.mention, 
                    inline=True
                )
            embed.add_field(
                name=_("commands.disboard.status", guild_id=guild_id), 
                value=_("commands.disboard.enabled", guild_id=guild_id), 
                inline=True
            )
            embed.add_field(
                name=_("commands.disboard.interval", guild_id=guild_id), 
                value="2h", 
                inline=True
            )
            embed.set_footer(text=_("commands.disboard.disboard_system", guild_id=guild_id))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error setting up Disboard config: {e}")
            await interaction.response.send_message(
                _("commands.disboard.config_error", guild_id=guild_id),
                ephemeral=True
            )
    
    async def _show_status(self, interaction: discord.Interaction, guild_id: int):
        """Show current Disboard configuration status"""
        try:
            # Get configuration
            config = await self.bot.db.query(
                "SELECT * FROM disboard_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            
            if not config:
                embed = discord.Embed(
                    title=_("commands.disboard.title", guild_id=guild_id),
                    description=_("commands.disboard.not_configured", guild_id=guild_id),
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name=_("commands.disboard.status", guild_id=guild_id), 
                    value=_("commands.disboard.disabled", guild_id=guild_id), 
                    inline=True
                )
                embed.add_field(
                    name=_("commands.disboard.action", guild_id=guild_id), 
                    value=_("commands.disboard.use_setup", guild_id=guild_id), 
                    inline=True
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Get reminder channel
            reminder_channel = interaction.guild.get_channel(config['reminder_channel_id'])
            channel_status = reminder_channel.mention if reminder_channel else _("commands.disboard.channel_not_found", guild_id=guild_id)
            
            # Get bump role
            bump_role = None
            if config['bump_role_id']:
                bump_role = interaction.guild.get_role(config['bump_role_id'])
            role_status = bump_role.mention if bump_role else _("commands.disboard.no_role_configured", guild_id=guild_id)
            
            # Get bump statistics
            bump_stats = await self.bot.db.query(
                "SELECT COUNT(*) as total_bumps, MAX(bump_time) as last_bump FROM disboard_bumps WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            
            # Create status embed
            embed = discord.Embed(
                title=_("commands.disboard.title", guild_id=guild_id),
                description=_("commands.disboard.current_config", guild_id=guild_id),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name=_("commands.disboard.status", guild_id=guild_id), 
                value=_("commands.disboard.enabled", guild_id=guild_id) if config['reminder_enabled'] else _("commands.disboard.disabled", guild_id=guild_id), 
                inline=True
            )
            embed.add_field(
                name=_("commands.disboard.reminder_channel", guild_id=guild_id), 
                value=channel_status, 
                inline=True
            )
            embed.add_field(
                name=_("commands.disboard.bump_role", guild_id=guild_id), 
                value=role_status, 
                inline=True
            )
            embed.add_field(
                name=_("commands.disboard.interval", guild_id=guild_id), 
                value=f"{config['reminder_interval_hours']}h", 
                inline=True
            )
            
            if bump_stats and bump_stats['total_bumps']:
                embed.add_field(
                    name=_("commands.disboard.total_bumps", guild_id=guild_id), 
                    value=f"**{bump_stats['total_bumps']}**", 
                    inline=True
                )
                if bump_stats['last_bump']:
                    embed.add_field(
                        name=_("commands.disboard.last_bump", guild_id=guild_id), 
                        value=f"<t:{int(bump_stats['last_bump'].timestamp())}:R>", 
                        inline=True
                    )
            
            embed.set_footer(text=_("commands.disboard.disboard_system", guild_id=guild_id))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing Disboard status: {e}")
            await interaction.response.send_message(
                _("commands.disboard.status_error", guild_id=guild_id),
                ephemeral=True
            )
    
    async def _reset_config(self, interaction: discord.Interaction, guild_id: int):
        """Reset Disboard configuration for the server"""
        try:
            # Delete configuration
            await self.bot.db.query(
                "DELETE FROM disboard_config WHERE guild_id = %s",
                (guild_id,)
            )
            
            # Create confirmation embed
            embed = discord.Embed(
                title=_("commands.disboard.title", guild_id=guild_id),
                description=_("commands.disboard.reset_success", guild_id=guild_id),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name=_("commands.disboard.action", guild_id=guild_id), 
                value=_("commands.disboard.config_deleted", guild_id=guild_id), 
                inline=True
            )
            embed.add_field(
                name=_("commands.disboard.status", guild_id=guild_id), 
                value=_("commands.disboard.disabled", guild_id=guild_id), 
                inline=True
            )
            embed.set_footer(text=_("commands.disboard.disboard_system", guild_id=guild_id))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error resetting Disboard config: {e}")
            await interaction.response.send_message(
                _("commands.disboard.reset_error", guild_id=guild_id),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(DisboardConfig(bot))
