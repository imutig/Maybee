"""
Disboard Bump Reminder System for Maybee
Automatically detects bumps and sends reminders for server promotion
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta, timezone
import asyncio
import re
from i18n import _
from .command_logger import log_command_usage
from custom_emojis import CHART_BAR, STATS, TROPHY, GOLD_MEDAL, SILVER_MEDAL, BRONZE_MEDAL, CLOCK, USERS, FIRE, ARROW_UP, INFO, ERROR

# Services and monitoring modules removed during cleanup
import logging
logger = logging.getLogger(__name__)

class DisboardReminder(commands.Cog):
    """Disboard bump reminder system with automatic detection and reminders"""
    
    def __init__(self, bot):
        self.bot = bot
        self.disboard_id = 302050872383242240  # Disboard bot ID
        self.reminder_interval = 2  # Hours between bumps
        self.check_reminders.start()
        
    def cog_unload(self):
        self.check_reminders.cancel()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect Disboard bumps automatically"""
        # Check if message is from Disboard
        if message.author.id != self.disboard_id or not message.guild:
            return
            
        # Get command info from interaction metadata
        command_name = "unknown"
        user = None
        
        if hasattr(message, 'interaction') and message.interaction:
            command_name = message.interaction.name
            user_id = message.interaction.user.id
            user = message.guild.get_member(user_id)
        
        # Log the command cleanly
        if user:
            logger.info(f"📨 Disboard: /{command_name} by {user.display_name} ({user.id})")
        else:
            logger.info(f"📨 Disboard: /{command_name} by unknown user")
        
        # Only process if it's a bump command
        if command_name != 'bump':
            return
        
        # If we have a user and command_name is 'bump', it's a successful bump!
        if user:
            logger.info(f"🚀 Bump confirmed by {user.display_name} ({user.id})")
            await self._handle_bump_detected(message.guild, user, message.channel)
        else:
            logger.warning(f"⚠️ Bump detected but user not found")

    async def _handle_bump_detected(self, guild: discord.Guild, bumper: discord.Member, channel: discord.TextChannel):
        """Handle detected bump and update database"""
        try:
            current_time = datetime.now()
            
            # Always create a new record for each bump
            await self.bot.db.query(
                """INSERT INTO disboard_bumps 
                   (guild_id, bumper_id, bumper_name, channel_id, bump_time, bumps_count, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, 1, %s, %s)""",
                (guild.id, bumper.id, bumper.display_name, channel.id, current_time, current_time, current_time)
            )
            
            # Get total bumps for this user in this guild
            total_bumps = await self.bot.db.query(
                "SELECT COUNT(*) as count FROM disboard_bumps WHERE guild_id = %s AND bumper_id = %s",
                (guild.id, bumper.id),
                fetchone=True
            )
            bump_count = total_bumps['count']
            
            # Send simple thank you message
            await channel.send(_("disboard.thank_you.message", guild_id=guild.id, bumper=bumper.display_name, server=guild.name))
            
            # Send thank you message with role offer
            await self._send_thank_you_message(guild, bumper, channel)
            
            logger.info(f"✅ Bump recorded: {bumper.display_name} ({bump_count} total)")
            
        except Exception as e:
            logger.error(f"Error handling bump detection: {e}")

    async def _send_thank_you_message(self, guild: discord.Guild, bumper: discord.Member, channel: discord.TextChannel):
        """Send bump role offer message to user"""
        try:
            # Get server configuration
            config = await self.bot.db.query(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild.id,),
                fetchone=True
            )
            
            if not config or not config['bump_role_id']:
                # No bump role configured, don't send any message
                return
            
            bump_role = guild.get_role(config['bump_role_id'])
            if not bump_role:
                # Role not found, don't send any message
                return
            
            # Check if user already has the bump role
            if bump_role in bumper.roles:
                # User already has the role, don't send any message
                return
            
            # User doesn't have the role, send ephemeral message with role offer
            embed = discord.Embed(
                title=f"🔔 {_('disboard.notification.title', guild_id=guild.id)}",
                description=_('disboard.notification.description', guild_id=guild.id, bumper=bumper.display_name),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=f"🎯 {_('disboard.notification.click_to_notify', guild_id=guild.id)}",
                value=_('disboard.notification.role_benefit', guild_id=guild.id, role=bump_role.mention),
                inline=False
            )
            
            # Create buttons with proper callback handling
            class BumpRoleView(discord.ui.View):
                def __init__(self, bot, bumper_id, guild_id, role_id):
                    super().__init__(timeout=30)  # 30 seconds timeout to match deletion
                    self.bot = bot
                    self.bumper_id = bumper_id
                    self.guild_id = guild_id
                    self.role_id = role_id
                
                @discord.ui.button(label="✅ Yes, notify me", style=discord.ButtonStyle.green, custom_id="bump_role_yes")
                async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self._handle_button_click(interaction, "yes")
                
                @discord.ui.button(label="❌ No, thanks", style=discord.ButtonStyle.red, custom_id="bump_role_no")
                async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self._handle_button_click(interaction, "no")
                
                async def _handle_button_click(self, interaction: discord.Interaction, action: str):
                    try:
                        logger.info(f"🔘 Button {action} clicked by {interaction.user.display_name} (ID: {interaction.user.id})")
                        
                        # Check if this interaction is from the intended user
                        if interaction.user.id != self.bumper_id:
                            logger.warning(f"❌ Wrong user: {interaction.user.display_name} (ID: {interaction.user.id}) instead of expected user (ID: {self.bumper_id})")
                            await interaction.response.send_message(
                                _("disboard.error.wrong_user", guild_id=interaction.guild.id),
                                ephemeral=True
                            )
                            return
                        
                        # Get guild and role
                        guild = interaction.guild
                        if not guild or guild.id != self.guild_id:
                            logger.error(f"❌ Wrong guild: guild_id={guild.id if guild else None}, expected_guild_id={self.guild_id}")
                            await interaction.response.send_message(_("disboard.error.wrong_guild", guild_id=interaction.guild.id), ephemeral=True)
                            return
                        
                        logger.info(f"🔍 Searching configuration for guild_id={self.guild_id}")
                        config = await self.bot.db.query(
                            "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                            (self.guild_id,),
                            fetchone=True
                        )
                        
                        if not config or not config['bump_role_id']:
                            logger.error(f"❌ Bump role configuration not found for guild_id={self.guild_id}")
                            await interaction.response.send_message(
                                _("disboard.error.role_config_not_found", guild_id=interaction.guild.id),
                                ephemeral=True
                            )
                            return
                        
                        logger.info(f"🔍 Configured role: role_id={config['bump_role_id']}")
                        bump_role = guild.get_role(config['bump_role_id'])
                        if not bump_role:
                            logger.error(f"❌ Bump role not found: role_id={config['bump_role_id']} in guild={guild.name}")
                            await interaction.response.send_message(
                                _("disboard.error.role_not_found", guild_id=interaction.guild.id),
                                ephemeral=True
                            )
                            return
                        
                        logger.info(f"✅ Role found: {bump_role.name} (ID: {bump_role.id})")
                        
                        if action == "yes":
                            # Assign the role
                            logger.info(f"🎯 Attempting to assign role {bump_role.name} to {interaction.user.display_name}")
                            try:
                                await interaction.user.add_roles(bump_role)
                                logger.info(f"✅ Role {bump_role.name} successfully assigned to {interaction.user.display_name}")
                                
                                embed = discord.Embed(
                                    title=f"✅ {_('disboard.success.role_assigned_title', guild_id=guild.id)}",
                                    description=_("disboard.thank_you.role_assigned", guild_id=guild.id),
                                    color=discord.Color.green(),
                                    timestamp=datetime.now()
                                )
                                await interaction.response.send_message(embed=embed, ephemeral=True)
                                
                                logger.info(f"Bump role {bump_role.name} assigned to {interaction.user.display_name} in {guild.name}")
                                
                            except discord.Forbidden:
                                logger.error(f"❌ Permission denied to assign role {bump_role.name} to {interaction.user.display_name}")
                                await interaction.response.send_message(
                                    _("disboard.error.no_permission", guild_id=guild.id),
                                    ephemeral=True
                                )
                            except Exception as e:
                                logger.error(f"❌ Error assigning role {bump_role.name} to {interaction.user.display_name}: {e}")
                                await interaction.response.send_message(
                                    _("disboard.error.role_assignment_error", guild_id=guild.id),
                                    ephemeral=True
                                )
                                
                        elif action == "no":
                            # User declined the role
                            embed = discord.Embed(
                                title=f"❌ {_('disboard.success.role_declined_title', guild_id=guild.id)}",
                                description=_("disboard.thank_you.role_declined", guild_id=guild.id),
                                color=discord.Color.orange(),
                                timestamp=datetime.now()
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        # Delete the original message after interaction
                        try:
                            original_message = interaction.message
                            if original_message:
                                await original_message.delete()
                        except discord.NotFound:
                            # Message already deleted
                            pass
                        except Exception as e:
                            logger.error(f"Error deleting original message: {e}")
                            
                    except Exception as e:
                        logger.error(f"Error handling bump role button: {e}")
                        await interaction.response.send_message(
                            _("disboard.error.processing_error", guild_id=interaction.guild.id),
                            ephemeral=True
                        )
            
            # Create view with buttons
            view = BumpRoleView(self.bot, bumper.id, guild.id, config['bump_role_id'])
            
            # Send temporary message with buttons in the channel
            temp_message = await channel.send(embed=embed, view=view)
            
            # Delete the message after 30 seconds
            async def delete_message():
                await asyncio.sleep(30)
                try:
                    await temp_message.delete()
                except discord.NotFound:
                    # Message already deleted by user interaction
                    pass
                except Exception as e:
                    logger.error(f"Error deleting temporary bump role message: {e}")
            
            # Start the deletion task
            asyncio.create_task(delete_message())
            
        except Exception as e:
            logger.error(f"Error sending bump role offer message: {e}")

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        """Check and send bump reminders every minute"""
        try:
            current_time = datetime.now()
            reminder_threshold = current_time - timedelta(hours=self.reminder_interval)
            
            # Get all servers with bump data for logging
            all_servers = await self.bot.db.query(
                """SELECT DISTINCT guild_id, 
                          (SELECT channel_id FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) as channel_id,
                          (SELECT bump_time FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) as last_bump
                   FROM disboard_bumps db
                   WHERE (SELECT bump_time FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) IS NOT NULL""",
                fetchall=True
            )
            
            for server_data in all_servers:
                guild_id = server_data['guild_id']
                channel_id = server_data['channel_id']
                last_bump = server_data['last_bump']
                
                # Skip if any required data is missing or None
                if not guild_id or not channel_id or not last_bump:
                    logger.debug(f"Skipping server {guild_id}: missing data (channel_id={channel_id}, last_bump={last_bump})")
                    continue
                
                # Get guild name for logging
                guild = self.bot.get_guild(guild_id)
                guild_name = guild.name if guild else f"Guild {guild_id}"
                
                # Calculate time since last bump
                time_since_bump = current_time - last_bump
                minutes_since_bump = int(time_since_bump.total_seconds() / 60)
                
                # Check if reminder is needed
                needs_reminder = last_bump < reminder_threshold
                
                # Check if reminder was already sent for this bump
                last_reminder = await self.bot.db.query(
                    "SELECT reminder_time FROM disboard_reminders WHERE guild_id = %s ORDER BY reminder_time DESC LIMIT 1",
                    (guild_id,),
                    fetchone=True
                )
                
                reminder_already_sent = False
                if last_reminder and last_reminder['reminder_time'] > last_bump:
                    # A reminder was sent after the last bump, so no more reminders until next bump
                    reminder_already_sent = True
                
                # Calculate next reminder time
                if reminder_already_sent:
                    # No more reminders until next bump
                    minutes_until_next_reminder = 0
                else:
                    # Next reminder will be exactly 2h after last bump
                    next_reminder_time = last_bump + timedelta(hours=2)
                    minutes_until_next_reminder = int((next_reminder_time - current_time).total_seconds() / 60)
                    if minutes_until_next_reminder <= 0:
                        minutes_until_next_reminder = 0
                
                # Log status
                if needs_reminder and not reminder_already_sent:
                    logger.info(f"⏰ Last bump for \"{guild_name}\" {minutes_since_bump} minutes ago. REMINDER SENT!")
                else:
                    if reminder_already_sent:
                        logger.info(f"⏰ Last bump for \"{guild_name}\" {minutes_since_bump} minutes ago. Reminder already sent, waiting for next bump.")
                    else:
                        logger.info(f"⏰ Last bump for \"{guild_name}\" {minutes_since_bump} minutes ago. Next reminder in {minutes_until_next_reminder} minutes.")
                
                # Send reminder if needed and not already sent
                if needs_reminder and not reminder_already_sent:
                    await self._send_bump_reminder(guild_id, channel_id, last_bump)
                
        except Exception as e:
            logger.error(f"Error checking bump reminders: {e}")

    async def _send_bump_reminder(self, guild_id: int, channel_id: int, last_bump: datetime):
        """Send bump reminder to specified channel"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
                
            channel = guild.get_channel(channel_id)
            if not channel:
                return
            
            # Get server configuration for bump role
            config = await self.bot.db.query(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            
            # Send short reminder message
            reminder_message = _("disboard.reminder.message", guild_id=guild_id)
            
            # Send reminder with role ping if configured
            if config and config['bump_role_id']:
                bump_role = guild.get_role(config['bump_role_id'])
                if bump_role:
                    await channel.send(f"{bump_role.mention} {reminder_message}")
                else:
                    await channel.send(reminder_message)
            else:
                await channel.send(reminder_message)
            
            # Log reminder in database
            await self.bot.db.query(
                "INSERT INTO disboard_reminders (guild_id, channel_id, reminder_time) VALUES (%s, %s, %s)",
                (guild_id, channel_id, datetime.now())
            )
            
            logger.info(f"Bump reminder sent to {guild.name} (ID: {guild_id})")
            
        except Exception as e:
            logger.error(f"Error sending bump reminder: {e}")

    @app_commands.command(name="bumptop", description="Display server bump leaderboard")
    @app_commands.describe(
        period="Period for the leaderboard (week/month/all)"
    )
    async def bumptop(self, interaction: discord.Interaction, period: str = "all"):
        """Display bump leaderboard for the server"""
        try:
            guild_id = interaction.guild.id
            
            # Validate period parameter
            if period not in ["week", "month", "all"]:
                period = "all"
            
            # Build query based on period
            if period == "week":
                time_filter = "AND bump_time >= DATE_SUB(NOW(), INTERVAL 1 WEEK)"
                period_name = _("disboard.leaderboard.this_week", interaction.user.id, guild_id)
            elif period == "month":
                time_filter = "AND bump_time >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
                period_name = _("disboard.leaderboard.this_month", interaction.user.id, guild_id)
            else:
                time_filter = ""
                period_name = _("disboard.leaderboard.all_time", interaction.user.id, guild_id)
            
            # Get top bumpers
            top_bumpers = await self.bot.db.query(
                f"""SELECT bumper_id, bumper_name, COUNT(*) as bump_count, 
                           MAX(bump_time) as last_bump
                    FROM disboard_bumps 
                    WHERE guild_id = %s {time_filter}
                    GROUP BY bumper_id, bumper_name
                    ORDER BY bump_count DESC, last_bump DESC
                    LIMIT 10""",
                (guild_id,),
                fetchall=True
            )
            
            if not top_bumpers:
                embed = discord.Embed(
                    title=f"{TROPHY} {_('disboard.leaderboard.title', interaction.user.id, guild_id)}",
                    description=_("disboard.leaderboard.no_bumps", interaction.user.id, guild_id, period=period_name),
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=f"{TROPHY} {_('disboard.leaderboard.title', interaction.user.id, guild_id)}",
                description=_("disboard.leaderboard.description", interaction.user.id, guild_id, period=period_name),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            # Add top bumpers
            for i, bumper in enumerate(top_bumpers, 1):
                medal = GOLD_MEDAL if i == 1 else SILVER_MEDAL if i == 2 else BRONZE_MEDAL if i == 3 else f"**{i}.**"
                
                embed.add_field(
                    name=f"{medal} {bumper['bumper_name']}",
                    value=f"**{bumper['bump_count']}** {_('disboard.leaderboard.bumps', interaction.user.id, guild_id)}\n{CLOCK} {_('disboard.leaderboard.last_bump', interaction.user.id, guild_id)}: <t:{int(bumper['last_bump'].timestamp())}:R>",
                    inline=False
                )
            
            # Add server stats
            total_bumps = await self.bot.db.query(
                f"SELECT COUNT(*) as total FROM disboard_bumps WHERE guild_id = %s {time_filter}",
                (guild_id,),
                fetchone=True
            )
            
            embed.set_footer(text=_("disboard.leaderboard.footer", interaction.user.id, guild_id, total=total_bumps['total'], period=period_name))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bumptop command: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('disboard.error.leaderboard_error', interaction.user.id, guild_id)}",
                ephemeral=True
            )

    @app_commands.command(name="bumpstats", description="Display server bump statistics")
    @log_command_usage
    async def bumpstats(self, interaction: discord.Interaction):
        """Display server bump statistics"""
        try:
            guild_id = interaction.guild.id
            
            # Get overall stats
            stats = await self.bot.db.query(
                """SELECT 
                       COUNT(*) as total_bumps,
                       COUNT(DISTINCT bumper_id) as unique_bumpers,
                       MAX(bump_time) as last_bump,
                       MIN(bump_time) as first_bump
                   FROM disboard_bumps 
                   WHERE guild_id = %s""",
                (guild_id,),
                fetchone=True
            )
            
            # Calculate average time between bumps (simplified approach)
            if stats and stats['total_bumps'] > 1:
                # Get all bumps ordered by time to calculate intervals
                all_bumps = await self.bot.db.query(
                    "SELECT bump_time FROM disboard_bumps WHERE guild_id = %s ORDER BY bump_time",
                    (guild_id,),
                    fetchall=True
                )
                
                if len(all_bumps) > 1:
                    total_hours = 0
                    intervals = 0
                    for i in range(len(all_bumps) - 1):
                        time_diff = all_bumps[i+1]['bump_time'] - all_bumps[i]['bump_time']
                        total_hours += time_diff.total_seconds() / 3600
                        intervals += 1
                    
                    if intervals > 0:
                        stats['avg_hours_between'] = total_hours / intervals
                    else:
                        stats['avg_hours_between'] = None
                else:
                    stats['avg_hours_between'] = None
            else:
                stats['avg_hours_between'] = None
            
            if not stats or not stats['total_bumps']:
                embed = discord.Embed(
                    title=f"{STATS} {_('disboard.stats.title', interaction.user.id, guild_id)}",
                    description=_("disboard.stats.no_stats", interaction.user.id, guild_id),
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Calculate time since last bump
            time_since_last = datetime.now() - stats['last_bump']
            hours_since_last = int(time_since_last.total_seconds() / 3600)
            minutes_since_last = int(time_since_last.total_seconds() / 60)
            
            # Create stats embed
            embed = discord.Embed(
                title=f"{STATS} {_('disboard.stats.title', interaction.user.id, guild_id)}",
                description=_("disboard.stats.description", interaction.user.id, guild_id, server=interaction.guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name=f"{FIRE} {_('disboard.stats.total_bumps', interaction.user.id, guild_id)}", value=f"**{stats['total_bumps']}**", inline=True)
            embed.add_field(name=f"{USERS} {_('disboard.stats.unique_bumpers', interaction.user.id, guild_id)}", value=f"**{stats['unique_bumpers']}**", inline=True)
            embed.add_field(name=f"{CLOCK} {_('disboard.stats.last_bump', interaction.user.id, guild_id)}", value=f"<t:{int(stats['last_bump'].timestamp())}:R>", inline=True)
            
            embed.add_field(name=f"{ARROW_UP} {_('disboard.stats.first_bump', interaction.user.id, guild_id)}", value=f"<t:{int(stats['first_bump'].timestamp())}:R>", inline=True)
            embed.add_field(name=f"{CLOCK} {_('disboard.stats.time_elapsed', interaction.user.id, guild_id)}", value=f"**{hours_since_last}h**", inline=True)
            
            if stats['avg_hours_between']:
                embed.add_field(name=f"{CLOCK} {_('disboard.stats.avg_between', interaction.user.id, guild_id)}", value=f"**{stats['avg_hours_between']:.1f}h**", inline=True)
            
            # Add bump frequency indicator
            if minutes_since_last >= 120:  # 2 hours or more (120 minutes)
                status = _("disboard.stats.status.ready", interaction.user.id, guild_id)
            elif minutes_since_last >= 60:  # 1 hour or more (60 minutes)
                status = _("disboard.stats.status.soon", interaction.user.id, guild_id)
            else:
                status = _("disboard.stats.status.waiting", interaction.user.id, guild_id)
            
            embed.add_field(name=f"{INFO} {_('disboard.stats.status.title', interaction.user.id, guild_id)}", value=status, inline=False)
            
            embed.set_footer(text=_("disboard.stats.footer", interaction.user.id, guild_id))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bumpstats command: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('disboard.error.stats_error', interaction.user.id, guild_id)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(DisboardReminder(bot))
