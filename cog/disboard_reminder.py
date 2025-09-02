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

from services import handle_errors, rate_limit
from monitoring import logger

class DisboardReminder(commands.Cog):
    """Disboard bump reminder system with automatic detection and reminders"""
    
    def __init__(self, bot):
        self.bot = bot
        self.disboard_id = 302050872383242240  # Disboard bot ID
        self.reminder_interval = 2  # Hours between bumps
        self.bump_role_messages = {}  # Store message info for button handling
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
            logger.info(f"📨 Disboard: /{command_name} par {user.display_name} ({user.id})")
        else:
            logger.info(f"📨 Disboard: /{command_name} par utilisateur inconnu")
        
        # Only process if it's a bump command
        if command_name != 'bump':
            return
        
        # If we have a user and command_name is 'bump', it's a successful bump!
        if user:
            logger.info(f"🚀 Bump confirmé par {user.display_name} ({user.id})")
            await self._handle_bump_detected(message.guild, user, message.channel)
        else:
            logger.warning(f"⚠️ Bump détecté mais utilisateur introuvable")
    

    


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for bump role assignment"""
        # Only handle component interactions (buttons, select menus, etc.)
        if interaction.type == discord.InteractionType.component:
            try:
                custom_id = interaction.custom_id
                if custom_id and custom_id.startswith("bump_role_"):
                    await self._handle_bump_role_button(interaction)
            except AttributeError:
                # Some component interactions might not have custom_id
                pass

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
            
            # Send bump confirmation
            embed = discord.Embed(
                title=_("disboard.bump_detected.title", guild_id=guild.id),
                description=_("disboard.bump_detected.description", guild_id=guild.id, bumper=bumper.display_name),
                color=discord.Color.green(),
                timestamp=current_time
            )
            embed.add_field(name=_("disboard.bump_detected.bump_count", guild_id=guild.id), value=f"**{bump_count}**", inline=True)
            embed.add_field(name=_("disboard.bump_detected.next_bump", guild_id=guild.id), value=f"<t:{int((current_time + timedelta(hours=2)).timestamp())}:R>", inline=True)
            embed.set_footer(text=_("disboard.bump_detected.footer", guild_id=guild.id))
            
            await channel.send(embed=embed)
            
            # Send thank you message with role offer
            await self._send_thank_you_message(guild, bumper, channel)
            
            logger.info(f"✅ Bump enregistré: {bumper.display_name} ({bump_count} total)")
            
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
            
            # Create base embed for role notification
            embed = discord.Embed(
                title="🔔 Notification de bump",
                description=f"**{bumper.display_name}**, vous souhaitez être notifié au prochain bump ?",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if not config or not config['bump_role_id']:
                # No bump role configured
                embed.add_field(
                    name="⚠️ Configuration requise",
                    value="Aucun rôle de bump n'est configuré. Utilisez `/disboard setup role` pour configurer un rôle.",
                    inline=False
                )
                await channel.send(embed=embed)
                return
            
            bump_role = guild.get_role(config['bump_role_id'])
            if not bump_role:
                # Role not found
                embed.add_field(
                    name="⚠️ Rôle introuvable",
                    value="Le rôle de bump configuré n'existe plus. Utilisez `/disboard setup role` pour reconfigurer.",
                    inline=False
                )
                await channel.send(embed=embed)
                return
            
            # Check if user already has the bump role
            if bump_role in bumper.roles:
                # User already has the role
                embed.add_field(
                    name="✅ Déjà notifié",
                    value=f"Vous avez déjà le rôle {bump_role.mention} ! Vous serez notifié pour **TOUS** les prochains bumps.",
                    inline=False
                )
                await channel.send(embed=embed)
                return
            
            # Create role offer message
            embed.add_field(
                name="🎯 Cliquez ici pour être notifié",
                value=f"En acceptant, vous recevrez le rôle {bump_role.mention} et serez notifié pour **TOUS** les prochains bumps.",
                inline=False
            )
            
            # Create buttons
            yes_button = discord.ui.Button(
                style=discord.ButtonStyle.green,
                label="✅ Oui, notifiez-moi",
                custom_id=f"bump_role_yes_{bumper.id}_{guild.id}"
            )
            no_button = discord.ui.Button(
                style=discord.ButtonStyle.red,
                label="❌ Non, merci",
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
            logger.error(f"Error sending bump role offer message: {e}")

    async def _handle_bump_role_button(self, interaction: discord.Interaction):
        """Handle bump role button interactions"""
        try:
            custom_id = interaction.custom_id
            logger.info(f"🔘 Bouton cliqué: custom_id='{custom_id}' par {interaction.user.display_name}")
            
            if not custom_id or not isinstance(custom_id, str):
                logger.error(f"❌ custom_id invalide: {custom_id} (type: {type(custom_id)})")
                await interaction.response.send_message("❌ Erreur: ID de bouton invalide", ephemeral=True)
                return
                
            if not custom_id.startswith("bump_role_"):
                logger.debug(f"❌ custom_id ne commence pas par 'bump_role_': {custom_id}")
                return
            
            parts = custom_id.split("_")
            logger.info(f"🔍 Parts du custom_id: {parts}")
            
            if len(parts) != 5:
                logger.error(f"❌ Nombre de parties incorrect dans custom_id: {custom_id} (parties: {parts}, longueur: {len(parts)})")
                await interaction.response.send_message("❌ Erreur: Format de bouton incorrect", ephemeral=True)
                return
            
            try:
                action = parts[2]
                user_id = int(parts[3])
                guild_id = int(parts[4])
                logger.info(f"🔍 Parsed: action='{action}', user_id={user_id}, guild_id={guild_id}")
            except (ValueError, IndexError) as e:
                logger.error(f"❌ Erreur lors du parsing du custom_id '{custom_id}': {e}")
                await interaction.response.send_message("❌ Erreur: Impossible de lire les données du bouton", ephemeral=True)
                return
            
            # Check if this interaction is from the intended user
            logger.info(f"🔍 Vérification utilisateur: interaction.user.id={interaction.user.id}, expected_user_id={user_id}")
            if interaction.user.id != user_id:
                logger.warning(f"❌ Utilisateur incorrect: {interaction.user.display_name} (ID: {interaction.user.id}) au lieu de l'utilisateur attendu (ID: {user_id})")
                await interaction.response.send_message(
                    "❌ Seul l'utilisateur qui a bumpé peut utiliser ces boutons.",
                    ephemeral=True
                )
                return
            
            # Get guild and role
            guild = interaction.guild
            if not guild or guild.id != guild_id:
                logger.error(f"❌ Guild incorrect: guild_id={guild.id if guild else None}, expected_guild_id={guild_id}")
                await interaction.response.send_message("❌ Erreur: Serveur incorrect", ephemeral=True)
                return
            
            logger.info(f"🔍 Recherche configuration pour guild_id={guild_id}")
            config = await self.bot.db.query(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            
            if not config or not config['bump_role_id']:
                logger.error(f"❌ Configuration de rôle de bump introuvable pour guild_id={guild_id}")
                await interaction.response.send_message(
                    "❌ Configuration de rôle de bump introuvable.",
                    ephemeral=True
                )
                return
            
            logger.info(f"🔍 Rôle configuré: role_id={config['bump_role_id']}")
            bump_role = guild.get_role(config['bump_role_id'])
            if not bump_role:
                logger.error(f"❌ Rôle de bump introuvable: role_id={config['bump_role_id']} dans guild={guild.name}")
                await interaction.response.send_message(
                    "❌ Rôle de bump introuvable.",
                    ephemeral=True
                )
                return
            
            logger.info(f"✅ Rôle trouvé: {bump_role.name} (ID: {bump_role.id})")
            
            if action == "yes":
                # Assign the role
                logger.info(f"🎯 Tentative d'assignation du rôle {bump_role.name} à {interaction.user.display_name}")
                try:
                    await interaction.user.add_roles(bump_role)
                    logger.info(f"✅ Rôle {bump_role.name} assigné avec succès à {interaction.user.display_name}")
                    
                    embed = discord.Embed(
                        title="✅ Rôle assigné !",
                        description=_("disboard.thank_you.role_assigned", guild_id=guild.id),
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    logger.info(f"Bump role {bump_role.name} assigned to {interaction.user.display_name} in {guild.name}")
                    
                except discord.Forbidden:
                    logger.error(f"❌ Permission refusée pour assigner le rôle {bump_role.name} à {interaction.user.display_name}")
                    await interaction.response.send_message(
                        "❌ Je n'ai pas la permission d'assigner ce rôle.",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"❌ Erreur lors de l'assignation du rôle {bump_role.name} à {interaction.user.display_name}: {e}")
                    await interaction.response.send_message(
                        _("disboard.error.role_assignment_error", guild_id=guild.id),
                        ephemeral=True
                    )
                    
            elif action == "no":
                # User declined the role
                embed = discord.Embed(
                    title="❌ Rôle refusé",
                    description=_("disboard.thank_you.role_declined", guild_id=guild.id),
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
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
                    logger.info(f"⏰ Dernier bump pour \"{guild_name}\" il y a {minutes_since_bump} minutes. RAPPEL ENVOYÉ !")
                else:
                    if reminder_already_sent:
                        logger.info(f"⏰ Dernier bump pour \"{guild_name}\" il y a {minutes_since_bump} minutes. Rappel déjà envoyé, en attente du prochain bump.")
                    else:
                        logger.info(f"⏰ Dernier bump pour \"{guild_name}\" il y a {minutes_since_bump} minutes. Prochain rappel dans {minutes_until_next_reminder} minutes.")
                
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
            
            # Calculate time since last bump
            time_since_bump = datetime.now() - last_bump
            hours_since_bump = int(time_since_bump.total_seconds() / 3600)
            
            # Create reminder embed
            embed = discord.Embed(
                title=_("disboard.reminder.title", guild_id=guild.id),
                description=_("disboard.reminder.description", guild_id=guild.id),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name=_("disboard.reminder.last_bump", guild_id=guild.id), 
                value=f"<t:{int(last_bump.timestamp())}:R>", 
                inline=True
            )
            embed.add_field(
                name=_("disboard.reminder.time_elapsed", guild_id=guild.id), 
                value=f"**{hours_since_bump}h**", 
                inline=True
            )
            embed.add_field(
                name=_("disboard.reminder.command", guild_id=guild.id), 
                value="`/bump`", 
                inline=True
            )
            embed.set_footer(text=_("disboard.reminder.footer", guild_id=guild.id))
            
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
            await self.bot.db.query(
                "INSERT INTO disboard_reminders (guild_id, channel_id, reminder_time) VALUES (%s, %s, %s)",
                (guild_id, channel_id, datetime.now())
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
                period_name = "depuis toujours"
            
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
                    title=_("commands.bumptop.embed_title", guild_id=guild_id),
                    description=_("commands.bumptop.no_bumps", guild_id=guild_id, period=period_name),
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=_("commands.bumptop.embed_title", guild_id=guild_id),
                description=_("commands.bumptop.top_bumpers", guild_id=guild_id, period=period_name),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            # Add top bumpers
            for i, bumper in enumerate(top_bumpers, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                
                embed.add_field(
                    name=f"{medal} {bumper['bumper_name']}",
                    value=f"**{bumper['bump_count']}** {_('commands.bumptop.bump_count', guild_id=guild_id)}\n{_('commands.bumptop.last_bump', guild_id=guild_id)}: <t:{int(bumper['last_bump'].timestamp())}:R>",
                    inline=False
                )
            
            # Add server stats
            total_bumps = await self.bot.db.query(
                f"SELECT COUNT(*) as total FROM disboard_bumps WHERE guild_id = %s {time_filter}",
                (guild_id,),
                fetchone=True
            )
            
            embed.set_footer(text=_("commands.bumptop.total_bumps", guild_id=guild_id, count=total_bumps['total'], period=period_name))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bumptop command: {e}")
            await interaction.response.send_message(
                _("disboard.error.bumptop_error", guild_id=guild_id),
                ephemeral=True
            )

    @app_commands.command(name="bumpstats", description="Afficher les statistiques de bump du serveur")
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
                    title=_("commands.bumpstats.embed_title", guild_id=guild_id),
                    description=_("commands.bumpstats.no_stats", guild_id=guild_id),
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
                title=_("commands.bumpstats.embed_title", guild_id=guild_id),
                description=_("commands.bumpstats.server_stats", guild_id=guild_id, server=interaction.guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name=_("commands.bumpstats.total_bumps", guild_id=guild_id), value=f"**{stats['total_bumps']}**", inline=True)
            embed.add_field(name=_("commands.bumpstats.unique_bumpers", guild_id=guild_id), value=f"**{stats['unique_bumpers']}**", inline=True)
            embed.add_field(name=_("commands.bumpstats.last_bump", guild_id=guild_id), value=f"<t:{int(stats['last_bump'].timestamp())}:R>", inline=True)
            
            embed.add_field(name=_("commands.bumpstats.first_bump", guild_id=guild_id), value=f"<t:{int(stats['first_bump'].timestamp())}:R>", inline=True)
            embed.add_field(name=_("commands.bumpstats.time_elapsed", guild_id=guild_id), value=f"**{hours_since_last}h**", inline=True)
            
            if stats['avg_hours_between']:
                embed.add_field(name=_("commands.bumpstats.avg_between", guild_id=guild_id), value=f"**{stats['avg_hours_between']:.1f}h**", inline=True)
            
            # Add bump frequency indicator
            if minutes_since_last >= 120:  # 2 hours or more (120 minutes)
                status = _("commands.bumpstats.ready_bump", guild_id=guild_id)
            elif minutes_since_last >= 60:  # 1 hour or more (60 minutes)
                status = _("commands.bumpstats.soon_bump", guild_id=guild_id)
            else:
                status = _("commands.bumpstats.long_time_bump", guild_id=guild_id)
            
            embed.add_field(name=_("commands.bumpstats.status", guild_id=guild_id), value=status, inline=False)
            
            embed.set_footer(text=_("disboard.bump_detected.footer", guild_id=guild_id))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bumpstats command: {e}")
            await interaction.response.send_message(
                _("disboard.error.bumpstats_error", guild_id=guild_id),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(DisboardReminder(bot))
