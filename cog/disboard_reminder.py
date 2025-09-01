"""
Disboard Bump Reminder System for Maybee
Automatically detects bumps and sends reminders for server promotion
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import asyncio
import re
from i18n import _

from services import handle_errors, rate_limit
from monitoring import logger

class DisboardReminder(commands.Cog):
    """Disboard bump reminder system with automatic detection and reminders"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bump_patterns = [
            r"<@!?(\d+)> bumped the server!",
            r"<@!?(\d+)> just bumped the server!",
            r"<@!?(\d+)> bumped the server",
            r"<@!?(\d+)> just bumped the server",
            r"<@!?(\d+)> bumped",
            r"<@!?(\d+)> just bumped"
        ]
        self.disboard_id = 302050872383242240  # Disboard bot ID
        self.reminder_interval = 2  # Hours between bumps
        self.bump_role_messages = {}  # Store message info for button handling
        self.check_reminders.start()
        
    def cog_unload(self):
        self.check_reminders.cancel()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect Disboard bumps automatically"""
        if message.author.id != self.disboard_id or not message.guild:
            return
            
        # Check if message contains bump confirmation
        for pattern in self.bump_patterns:
            match = re.search(pattern, message.content, re.IGNORECASE)
            if match:
                # Extract user ID from the bump message
                user_id = int(match.group(1))
                bumper = message.guild.get_member(user_id)
                if bumper:
                    await self._handle_bump_detected(message.guild, bumper, message.channel)
                break
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for bump role assignment"""
        if interaction.type == discord.InteractionType.component:
            await self._handle_bump_role_button(interaction)
    
    async def _handle_bump_detected(self, guild: discord.Guild, bumper: discord.Member, channel: discord.TextChannel):
        """Handle detected bump and update database"""
        try:
            current_time = datetime.utcnow()
            
            # Get or create bump record
            existing_bump = await self.bot.db.fetchone(
                "SELECT * FROM disboard_bumps WHERE guild_id = %s ORDER BY bump_time DESC LIMIT 1",
                (guild.id,)
            )
            
            if existing_bump:
                # Update existing record
                await self.bot.db.execute(
                    """UPDATE disboard_bumps 
                       SET bumper_id = %s, bumper_name = %s, channel_id = %s, bump_time = %s, 
                           bumps_count = bumps_count + 1, updated_at = %s
                       WHERE id = %s""",
                    (bumper.id, bumper.display_name, channel.id, current_time, 
                     current_time, existing_bump['id'])
                )
                bump_count = existing_bump['bumps_count'] + 1
            else:
                # Create new record
                await self.bot.db.execute(
                    """INSERT INTO disboard_bumps 
                       (guild_id, bumper_id, bumper_name, channel_id, bump_time, bumps_count, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, 1, %s, %s)""",
                    (guild.id, bumper.id, bumper.display_name, channel.id, current_time, current_time, current_time)
                )
                bump_count = 1
            
            # Send bump confirmation
            embed = discord.Embed(
                title=_(guild.id, "disboard.bump_detected.title"),
                description=_(guild.id, "disboard.bump_detected.description", bumper=bumper.display_name),
                color=discord.Color.green(),
                timestamp=current_time
            )
            embed.add_field(name=_(guild.id, "disboard.bump_detected.bump_count"), value=f"**{bump_count}**", inline=True)
            embed.add_field(name=_(guild.id, "disboard.bump_detected.next_bump"), value=f"<t:{int((current_time + timedelta(hours=2)).timestamp())}:R>", inline=True)
            embed.set_footer(text=_(guild.id, "disboard.bump_detected.footer"))
            
            await channel.send(embed=embed)
            
            # Send thank you message with role offer
            await self._send_thank_you_message(guild, bumper, channel)
            
            logger.info(f"Bump detected in {guild.name} by {bumper.display_name} (ID: {bumper.id})")
            
        except Exception as e:
            logger.error(f"Error handling bump detection: {e}")
    
    async def _send_thank_you_message(self, guild: discord.Guild, bumper: discord.Member, channel: discord.TextChannel):
        """Send thank you message and offer bump role to user"""
        try:
            # Get server configuration
            config = await self.bot.db.fetchone(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild.id,)
            )
            
            if not config or not config['bump_role_id']:
                # No bump role configured, just send thank you message
                embed = discord.Embed(
                    title=_(guild.id, "disboard.thank_you.title"),
                    description=_(guild.id, "disboard.thank_you.message", bumper=bumper.display_name, server=guild.name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                return
            
            bump_role = guild.get_role(config['bump_role_id'])
            if not bump_role:
                # Role not found, send thank you message without role offer
                embed = discord.Embed(
                    title=_(guild.id, "disboard.thank_you.title"),
                    description=_(guild.id, "disboard.thank_you.message", bumper=bumper.display_name, server=guild.name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                return
            
            # Check if user already has the bump role
            if bump_role in bumper.roles:
                # User already has the role, just send thank you message
                embed = discord.Embed(
                    title=_(guild.id, "disboard.thank_you.title"),
                    description=_(guild.id, "disboard.thank_you.message", bumper=bumper.display_name, server=guild.name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="🎯 Rôle de bump",
                    value=f"Tu as déjà le rôle {bump_role.mention} !",
                    inline=False
                )
                await channel.send(embed=embed)
                return
            
            # Create thank you message with role offer
            embed = discord.Embed(
                title=_(guild.id, "disboard.thank_you.title"),
                description=_(guild.id, "disboard.thank_you.message", bumper=bumper.display_name, server=guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="🎯 Proposition de rôle",
                value=_(guild.id, "disboard.thank_you.role_offer"),
                inline=False
            )
            
            # Create buttons
            yes_button = discord.ui.Button(
                style=discord.ButtonStyle.green,
                label=_(guild.id, "disboard.thank_you.yes_button"),
                custom_id=f"bump_role_yes_{bumper.id}_{guild.id}"
            )
            no_button = discord.ui.Button(
                style=discord.ButtonStyle.red,
                label=_(guild.id, "disboard.thank_you.no_button"),
                custom_id=f"bump_role_no_{bumper.id}_{guild.id}"
            )
            
            # Create view with buttons
            view = discord.ui.View(timeout=300)  # 5 minutes timeout
            view.add_item(yes_button)
            view.add_item(no_button)
            
            # Send message with buttons
            message = await channel.send(embed=embed, view=view)
            
            # Store message info for button handling
            self.bump_role_messages[bumper.id] = {
                'message_id': message.id,
                'guild_id': guild.id,
                'role_id': config['bump_role_id'],
                'user_id': bumper.id
            }
            
        except Exception as e:
            logger.error(f"Error sending thank you message: {e}")
    
    async def _handle_bump_role_button(self, interaction: discord.Interaction):
        """Handle bump role button interactions"""
        try:
            custom_id = interaction.custom_id
            if not custom_id.startswith("bump_role_"):
                return
            
            parts = custom_id.split("_")
            if len(parts) != 4:
                return
            
            action = parts[2]
            user_id = int(parts[3])
            guild_id = int(parts[4])
            
            # Check if this interaction is from the intended user
            if interaction.user.id != user_id:
                await interaction.response.send_message(
                    "❌ Seul l'utilisateur qui a bumpé peut utiliser ces boutons.",
                    ephemeral=True
                )
                return
            
            # Get guild and role
            guild = interaction.guild
            if not guild or guild.id != guild_id:
                return
            
            config = await self.bot.db.fetchone(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild_id,)
            )
            
            if not config or not config['bump_role_id']:
                await interaction.response.send_message(
                    "❌ Configuration de rôle de bump introuvable.",
                    ephemeral=True
                )
                return
            
            bump_role = guild.get_role(config['bump_role_id'])
            if not bump_role:
                await interaction.response.send_message(
                    "❌ Rôle de bump introuvable.",
                    ephemeral=True
                )
                return
            
            if action == "yes":
                # Assign the role
                try:
                    await interaction.user.add_roles(bump_role)
                    
                    embed = discord.Embed(
                        title="✅ Rôle assigné !",
                        description=_(guild.id, "disboard.thank_you.role_assigned"),
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    logger.info(f"Bump role {bump_role.name} assigned to {interaction.user.display_name} in {guild.name}")
                    
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "❌ Je n'ai pas la permission d'assigner ce rôle.",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"Error assigning bump role: {e}")
                    await interaction.response.send_message(
                        _(guild.id, "disboard.error.role_assignment_error"),
                        ephemeral=True
                    )
                    
            elif action == "no":
                # User declined the role
                embed = discord.Embed(
                    title="❌ Rôle refusé",
                    description=_(guild.id, "disboard.thank_you.role_declined"),
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Remove the buttons from the original message
            try:
                original_message = interaction.message
                if original_message:
                    # Create new embed without buttons
                    embed = original_message.embeds[0]
                    embed.add_field(
                        name="🎯 Statut",
                        value="✅ Rôle accepté" if action == "yes" else "❌ Rôle refusé",
                        inline=False
                    )
                    await original_message.edit(embed=embed, view=None)
            except Exception as e:
                logger.error(f"Error updating original message: {e}")
                
        except Exception as e:
            logger.error(f"Error handling bump role button: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors du traitement de la demande.",
                ephemeral=True
            )
    
    @tasks.loop(minutes=5)
    async def check_reminders(self):
        """Check and send bump reminders every 5 minutes"""
        try:
            current_time = datetime.utcnow()
            reminder_threshold = current_time - timedelta(hours=self.reminder_interval)
            
            # Get servers that need reminders
            servers_needing_reminders = await self.bot.db.fetchall(
                """SELECT DISTINCT guild_id, 
                          (SELECT channel_id FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) as channel_id,
                          (SELECT bump_time FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) as last_bump
                   FROM disboard_bumps db
                   WHERE bump_time < %s""",
                (reminder_threshold,)
            )
            
            for server_data in servers_needing_reminders:
                guild_id = server_data['guild_id']
                channel_id = server_data['channel_id']
                last_bump = server_data['bump_time']
                
                if not channel_id:
                    continue
                
                # Check if reminder was already sent recently
                last_reminder = await self.bot.db.fetchone(
                    "SELECT reminder_time FROM disboard_reminders WHERE guild_id = %s ORDER BY reminder_time DESC LIMIT 1",
                    (guild_id,)
                )
                
                if last_reminder and (current_time - last_reminder['reminder_time']).total_seconds() < 3600:  # 1 hour cooldown
                    continue
                
                # Send reminder
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
            config = await self.bot.db.fetchone(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild_id,)
            )
            
            # Calculate time since last bump
            time_since_bump = datetime.utcnow() - last_bump
            hours_since_bump = int(time_since_bump.total_seconds() / 3600)
            
            # Create reminder embed
            embed = discord.Embed(
                title=_(guild.id, "disboard.reminder.title"),
                description=_(guild.id, "disboard.reminder.description"),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name=_(guild.id, "disboard.reminder.last_bump"), 
                value=f"<t:{int(last_bump.timestamp())}:R>", 
                inline=True
            )
            embed.add_field(
                name=_(guild.id, "disboard.reminder.time_elapsed"), 
                value=f"**{hours_since_bump}h**", 
                inline=True
            )
            embed.add_field(
                name=_(guild.id, "disboard.reminder.command"), 
                value="`/bump`", 
                inline=True
            )
            embed.set_footer(text=_(guild.id, "disboard.reminder.footer"))
            
            # Send reminder with role ping if configured
            if config and config['bump_role_id']:
                bump_role = guild.get_role(config['bump_role_id'])
                if bump_role:
                    await channel.send(f"{bump_role.mention}", embed=embed)
                else:
                    await channel.send(embed=embed)
            else:
                await channel.send(embed=embed)
            
            # Log reminder in database
            await self.bot.db.execute(
                "INSERT INTO disboard_reminders (guild_id, channel_id, reminder_time) VALUES (%s, %s, %s)",
                (guild_id, channel_id, datetime.utcnow())
            )
            
            logger.info(f"Bump reminder sent to {guild.name} (ID: {guild_id})")
            
        except Exception as e:
            logger.error(f"Error sending bump reminder: {e}")
    
    @app_commands.command(name="bumptop", description="Afficher la toplist des bumps du serveur")
    @app_commands.describe(
        period="Période pour la toplist (week/month/all)"
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
                period_name = "cette semaine"
            elif period == "month":
                time_filter = "AND bump_time >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
                period_name = "ce mois"
            else:
                time_filter = ""
                period_name = "tous les temps"
            
            # Get top bumpers
            top_bumpers = await self.bot.db.fetchall(
                f"""SELECT bumper_id, bumper_name, COUNT(*) as bump_count, 
                           MAX(bump_time) as last_bump
                    FROM disboard_bumps 
                    WHERE guild_id = %s {time_filter}
                    GROUP BY bumper_id, bumper_name
                    ORDER BY bump_count DESC, last_bump DESC
                    LIMIT 10""",
                (guild_id,)
            )
            
            if not top_bumpers:
                embed = discord.Embed(
                    title=_(guild_id, "commands.bumptop.embed_title"),
                    description=_(guild_id, "commands.bumptop.no_bumps", period=period_name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=_(guild_id, "commands.bumptop.embed_title"),
                description=_(guild_id, "commands.bumptop.top_bumpers", period=period_name),
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            
            # Add top bumpers
            for i, bumper in enumerate(top_bumpers, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                
                embed.add_field(
                    name=f"{medal} {bumper['bumper_name']}",
                    value=f"**{bumper['bump_count']}** {_(guild_id, 'commands.bumptop.bump_count')}\n{_(guild_id, 'commands.bumptop.last_bump')}: <t:{int(bumper['last_bump'].timestamp())}:R>",
                    inline=False
                )
            
            # Add server stats
            total_bumps = await self.bot.db.fetchone(
                f"SELECT COUNT(*) as total FROM disboard_bumps WHERE guild_id = %s {time_filter}",
                (guild_id,)
            )
            
            embed.set_footer(text=_(guild_id, "commands.bumptop.total_bumps", count=total_bumps['total'], period=period_name))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bumptop command: {e}")
            await interaction.response.send_message(
                _(guild_id, "disboard.error.bumptop_error"),
                ephemeral=True
            )
    
    @app_commands.command(name="bumpstats", description="Afficher les statistiques de bump du serveur")
    async def bumpstats(self, interaction: discord.Interaction):
        """Display server bump statistics"""
        try:
            guild_id = interaction.guild.id
            
            # Get overall stats
            stats = await self.bot.db.fetchone(
                """SELECT 
                       COUNT(*) as total_bumps,
                       COUNT(DISTINCT bumper_id) as unique_bumpers,
                       MAX(bump_time) as last_bump,
                       MIN(bump_time) as first_bump,
                       AVG(TIMESTAMPDIFF(HOUR, LAG(bump_time) OVER (ORDER BY bump_time), bump_time)) as avg_hours_between
                   FROM disboard_bumps 
                   WHERE guild_id = %s""",
                (guild_id,)
            )
            
            if not stats or not stats['total_bumps']:
                embed = discord.Embed(
                    title=_(guild_id, "commands.bumpstats.embed_title"),
                    description=_(guild_id, "commands.bumpstats.no_stats"),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Calculate time since last bump
            time_since_last = datetime.utcnow() - stats['last_bump']
            hours_since_last = int(time_since_last.total_seconds() / 3600)
            
            # Create stats embed
            embed = discord.Embed(
                title=_(guild_id, "commands.bumpstats.embed_title"),
                description=_(guild_id, "commands.bumpstats.server_stats", server=interaction.guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name=_(guild_id, "commands.bumpstats.total_bumps"), value=f"**{stats['total_bumps']}**", inline=True)
            embed.add_field(name=_(guild_id, "commands.bumpstats.unique_bumpers"), value=f"**{stats['unique_bumps']}**", inline=True)
            embed.add_field(name=_(guild_id, "commands.bumpstats.last_bump"), value=f"<t:{int(stats['last_bump'].timestamp())}:R>", inline=True)
            
            embed.add_field(name=_(guild_id, "commands.bumpstats.first_bump"), value=f"<t:{int(stats['first_bump'].timestamp())}:R>", inline=True)
            embed.add_field(name=_(guild_id, "commands.bumpstats.time_elapsed"), value=f"**{hours_since_last}h**", inline=True)
            
            if stats['avg_hours_between']:
                embed.add_field(name=_(guild_id, "commands.bumpstats.avg_between"), value=f"**{stats['avg_hours_between']:.1f}h**", inline=True)
            
            # Add bump frequency indicator
            if hours_since_last <= 2:
                status = _(guild_id, "commands.bumpstats.ready_bump")
            elif hours_since_last <= 4:
                status = _(guild_id, "commands.bumpstats.soon_bump")
            else:
                status = _(guild_id, "commands.bumpstats.long_time_bump")
            
            embed.add_field(name=_(guild_id, "commands.bumpstats.status"), value=status, inline=False)
            
            embed.set_footer(text=_(guild_id, "disboard.bump_detected.footer"))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bumpstats command: {e}")
            await interaction.response.send_message(
                _(guild_id, "disboard.error.bumpstats_error"),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(DisboardReminder(bot))
