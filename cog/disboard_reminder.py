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
        self.disboard_id = 302050872383242240  # Disboard bot ID
        self.reminder_interval = 2  # Hours between bumps
        self.bump_role_messages = {}  # Store message info for button handling
        self.check_reminders.start()
        
    def cog_unload(self):
        self.check_reminders.cancel()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect Disboard bumps automatically"""
        # Debug: Log every message for debugging
        logger.debug(f"🔍 Message reçu - Auteur: {message.author.name} (ID: {message.author.id}) | Contenu: '{message.content}' | Serveur: {message.guild.name if message.guild else 'DM'}")
        
        # Check if message is from Disboard
        is_disboard = message.author.id == self.disboard_id
        logger.debug(f"🤖 Ce message provient-t-il de Disboard ? {'✅ Oui' if is_disboard else '❌ Non'} (ID attendu: {self.disboard_id}, ID reçu: {message.author.id})")
        
        # Debug: Check for embeds
        if is_disboard and message.embeds:
            logger.debug(f"📋 Message Disboard avec {len(message.embeds)} embed(s)")
            for i, embed in enumerate(message.embeds):
                logger.debug(f"📋 Embed {i+1}: Title='{embed.title}', Description='{embed.description}'")
        
        if not is_disboard or not message.guild:
            if not is_disboard:
                logger.debug("❌ Message ignoré: pas de Disboard")
            if not message.guild:
                logger.debug("❌ Message ignoré: pas de serveur (DM)")
            return
            
        # Check if message contains bump confirmation
        is_bump_message = False
        
        # Check if message contains bump confirmation (text or embed)
        if message.content:
            # Check text content for bump keywords
            bump_keywords = ['bump', 'bumped', 'server bumped', 'successfully bumped', 'bump effectué', 'effectué']
            if any(keyword.lower() in message.content.lower() for keyword in bump_keywords):
                is_bump_message = True
                logger.debug(f"🎯 Bump détecté dans le contenu texte")
        
        # If no text match, try to detect from embeds
        if not is_bump_message and message.embeds:
            logger.debug(f"🔍 Recherche de bump dans les embeds...")
            for embed in message.embeds:
                # Check embed title and description for bump indicators
                embed_text = f"{embed.title or ''} {embed.description or ''}"
                logger.debug(f"📋 Contenu de l'embed: '{embed_text}'")
                
                # Look for bump-related keywords in embed (English and French)
                bump_keywords = ['bump', 'bumped', 'server bumped', 'successfully bumped', 'bump effectué', 'effectué']
                if any(keyword.lower() in embed_text.lower() for keyword in bump_keywords):
                    logger.debug(f"🎯 Bump détecté dans l'embed via keywords")
                    is_bump_message = True
                    break
        
        if not is_bump_message:
            logger.debug(f"🎯 S'agit-il d'un message de bump ? ❌ Non | Contenu: '{message.content}'")
            return
        
        # Since Disboard doesn't include user mentions, we need to find the user who used /bump
        # We'll use audit logs to find the most recent /bump command usage
        logger.debug(f"🔍 Recherche de l'utilisateur qui a utilisé /bump via audit log...")
        bumper = await self._find_bump_user(message.guild, message.channel)
        
        if bumper:
            logger.info(f"🚀 Bump détecté ! Utilisateur: {bumper.display_name} (ID: {bumper.id}) | Serveur: {message.guild.name}")
            await self._handle_bump_detected(message.guild, bumper, message.channel)
        else:
            logger.warning(f"⚠️ Bump détecté mais utilisateur introuvable dans le serveur {message.guild.name}")
    
    async def _find_bump_user(self, guild: discord.Guild, channel: discord.TextChannel) -> Optional[discord.Member]:
        """Find the user who used /bump command by checking audit logs"""
        try:
            logger.debug(f"🔍 Recherche dans les audit logs pour le serveur {guild.name}...")
            
            # Get audit logs for the last few minutes to find /bump usage
            async for entry in guild.audit_logs(action=discord.AuditLogAction.application_command_permissions, limit=10):
                # Calculate time difference
                time_diff = (datetime.utcnow() - entry.created_at).total_seconds()
                
                # Check if this is a recent command usage (within last 30 seconds)
                if time_diff > 30:
                    logger.debug(f"⏰ Audit log ignoré (trop ancien): {time_diff:.1f}s - Utilisateur: {entry.user.display_name}")
                    continue
                
                # Debug: Log all audit log entries
                command_name = entry.target.name if hasattr(entry, 'target') and entry.target else "Inconnu"
                logger.debug(f"📋 Audit log trouvé: Commande='{command_name}' | Utilisateur: {entry.user.display_name} | Temps: {time_diff:.1f}s")
                
                # Check if the command was /bump
                if hasattr(entry, 'target') and entry.target and entry.target.name == 'bump':
                    logger.debug(f"🎯 ✅ Commande /bump trouvée dans l'audit log - Utilisateur: {entry.user.display_name}")
                    return entry.user
                else:
                    logger.debug(f"❌ Pas un bump: Commande '{command_name}' - Utilisateur: {entry.user.display_name}")
            
            logger.debug(f"🔍 Aucune commande /bump trouvée dans les audit logs, recherche dans l'historique du canal...")
            
            # Alternative: Check recent messages in the channel for /bump usage
            logger.debug(f"🔍 Recherche de messages /bump récents dans le canal {channel.name}...")
            async for msg in channel.history(limit=20, before=datetime.utcnow()):
                # Skip bot messages
                if msg.author.bot:
                    continue
                
                # Calculate time difference
                time_diff = (datetime.utcnow() - msg.created_at).total_seconds()
                
                # Debug: Log all recent messages
                logger.debug(f"📋 Message trouvé: Contenu='{msg.content[:50]}...' | Auteur: {msg.author.display_name} | Temps: {time_diff:.1f}s")
                
                # Check if message contains /bump
                if msg.content and '/bump' in msg.content.lower():
                    # Check if this message is recent (within last 30 seconds)
                    if time_diff <= 30:
                        logger.debug(f"🎯 ✅ Message /bump trouvé - Utilisateur: {msg.author.display_name}")
                        return msg.author
                    else:
                        logger.debug(f"⏰ Message /bump trop ancien: {time_diff:.1f}s - Utilisateur: {msg.author.display_name}")
                else:
                    logger.debug(f"❌ Pas un message /bump: '{msg.content[:30]}...' - Utilisateur: {msg.author.display_name}")
            
            logger.warning("❌ Aucun utilisateur trouvé pour le bump")
            return None
            
        except discord.Forbidden:
            logger.error("❌ Pas de permission pour accéder aux audit logs")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la recherche de l'utilisateur bump: {e}")
            return None
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for bump role assignment"""
        if interaction.type == discord.InteractionType.component:
            # Only handle bump role buttons, ignore other component interactions
            custom_id = interaction.custom_id
            if custom_id and custom_id.startswith("bump_role_"):
                await self._handle_bump_role_button(interaction)
    
    async def _handle_bump_detected(self, guild: discord.Guild, bumper: discord.Member, channel: discord.TextChannel):
        """Handle detected bump and update database"""
        try:
            logger.info(f"🔄 Traitement du bump détecté - Serveur: {guild.name} | Utilisateur: {bumper.display_name} | Canal: {channel.name}")
            current_time = datetime.utcnow()
            
            # Get or create bump record
            logger.debug(f"📊 Recherche du dernier bump pour le serveur {guild.id}")
            existing_bump = await self.bot.db.query(
                "SELECT * FROM disboard_bumps WHERE guild_id = %s ORDER BY bump_time DESC LIMIT 1",
                (guild.id,),
                fetchone=True
            )
            
            if existing_bump:
                # Update existing record
                logger.debug(f"📝 Mise à jour du bump existant (ID: {existing_bump['id']}) - Ancien count: {existing_bump['bumps_count']}")
                await self.bot.db.query(
                    """UPDATE disboard_bumps 
                       SET bumper_id = %s, bumper_name = %s, channel_id = %s, bump_time = %s, 
                           bumps_count = bumps_count + 1, updated_at = %s
                       WHERE id = %s""",
                    (bumper.id, bumper.display_name, channel.id, current_time, 
                     current_time, existing_bump['id'])
                )
                bump_count = existing_bump['bumps_count'] + 1
                logger.info(f"✅ Bump mis à jour - Nouveau count: {bump_count}")
            else:
                # Create new record
                logger.debug(f"📝 Création d'un nouveau bump pour le serveur {guild.id}")
                await self.bot.db.query(
                    """INSERT INTO disboard_bumps 
                       (guild_id, bumper_id, bumper_name, channel_id, bump_time, bumps_count, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, 1, %s, %s)""",
                    (guild.id, bumper.id, bumper.display_name, channel.id, current_time, current_time, current_time)
                )
                bump_count = 1
                logger.info(f"✅ Nouveau bump créé - Count: {bump_count}")
            
            # Send bump confirmation
            logger.debug(f"📤 Envoi de l'embed de confirmation de bump")
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
            logger.info(f"✅ Embed de confirmation envoyé dans #{channel.name}")
            
            # Send thank you message with role offer
            logger.debug(f"📤 Envoi du message de remerciement")
            await self._send_thank_you_message(guild, bumper, channel)
            
            logger.info(f"🎉 Bump traité avec succès dans {guild.name} par {bumper.display_name} (ID: {bumper.id})")
            
        except Exception as e:
            logger.error(f"Error handling bump detection: {e}")
    
    async def _send_thank_you_message(self, guild: discord.Guild, bumper: discord.Member, channel: discord.TextChannel):
        """Send thank you message and offer bump role to user"""
        try:
            logger.debug(f"💬 Préparation du message de remerciement pour {bumper.display_name}")
            
            # Get server configuration
            logger.debug(f"🔧 Récupération de la configuration du serveur {guild.id}")
            config = await self.bot.db.query(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild.id,),
                fetchone=True
            )
            
            if not config or not config['bump_role_id']:
                # No bump role configured, just send thank you message
                logger.debug(f"❌ Aucun rôle de bump configuré pour le serveur {guild.id}")
                embed = discord.Embed(
                    title=_("disboard.thank_you.title", guild_id=guild.id),
                    description=_("disboard.thank_you.message", guild_id=guild.id, bumper=bumper.display_name, server=guild.name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logger.info(f"✅ Message de remerciement simple envoyé (pas de rôle configuré)")
                return
            
            bump_role = guild.get_role(config['bump_role_id'])
            if not bump_role:
                # Role not found, send thank you message without role offer
                logger.warning(f"⚠️ Rôle de bump introuvable (ID: {config['bump_role_id']}) dans le serveur {guild.name}")
                embed = discord.Embed(
                    title=_("disboard.thank_you.title", guild_id=guild.id),
                    description=_("disboard.thank_you.message", guild_id=guild.id, bumper=bumper.display_name, server=guild.name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logger.info(f"✅ Message de remerciement envoyé (rôle introuvable)")
                return
            
            # Check if user already has the bump role
            if bump_role in bumper.roles:
                # User already has the role, just send thank you message
                logger.debug(f"✅ L'utilisateur {bumper.display_name} a déjà le rôle {bump_role.name}")
                embed = discord.Embed(
                    title=_("disboard.thank_you.title", guild_id=guild.id),
                    description=_("disboard.thank_you.message", guild_id=guild.id, bumper=bumper.display_name, server=guild.name),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="🎯 Rôle de bump",
                    value=f"Tu as déjà le rôle {bump_role.mention} !",
                    inline=False
                )
                await channel.send(embed=embed)
                logger.info(f"✅ Message de remerciement envoyé (utilisateur a déjà le rôle)")
                return
            
            # Create thank you message with role offer
            logger.debug(f"🎯 Création du message avec proposition de rôle pour {bumper.display_name}")
            embed = discord.Embed(
                title=_("disboard.thank_you.title", guild_id=guild.id),
                description=_("disboard.thank_you.message", guild_id=guild.id, bumper=bumper.display_name, server=guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="🎯 Proposition de rôle",
                value=_("disboard.thank_you.role_offer", guild_id=guild.id),
                inline=False
            )
            
            # Create buttons
            yes_button = discord.ui.Button(
                style=discord.ButtonStyle.green,
                label=_("disboard.thank_you.yes_button", guild_id=guild.id),
                custom_id=f"bump_role_yes_{bumper.id}_{guild.id}"
            )
            no_button = discord.ui.Button(
                style=discord.ButtonStyle.red,
                label=_("disboard.thank_you.no_button", guild_id=guild.id),
                custom_id=f"bump_role_no_{bumper.id}_{guild.id}"
            )
            
            # Create view with buttons
            view = discord.ui.View(timeout=300)  # 5 minutes timeout
            view.add_item(yes_button)
            view.add_item(no_button)
            
            # Send message with buttons
            message = await channel.send(embed=embed, view=view)
            logger.info(f"✅ Message avec proposition de rôle envoyé (Message ID: {message.id})")
            
            # Store message info for button handling
            self.bump_role_messages[bumper.id] = {
                'message_id': message.id,
                'guild_id': guild.id,
                'role_id': config['bump_role_id'],
                'user_id': bumper.id
            }
            logger.debug(f"💾 Informations du message stockées pour {bumper.id}")
            
        except Exception as e:
            logger.error(f"Error sending thank you message: {e}")
    
    async def _handle_bump_role_button(self, interaction: discord.Interaction):
        """Handle bump role button interactions"""
        try:
            custom_id = interaction.custom_id
            if not custom_id or not isinstance(custom_id, str):
                logger.debug(f"❌ custom_id invalide: {custom_id} (type: {type(custom_id)})")
                return
                
            if not custom_id.startswith("bump_role_"):
                return
            
            parts = custom_id.split("_")
            if len(parts) != 5:
                logger.debug(f"❌ Nombre de parties incorrect dans custom_id: {custom_id} (parties: {parts})")
                return
            
            try:
                action = parts[2]
                user_id = int(parts[3])
                guild_id = int(parts[4])
            except (ValueError, IndexError) as e:
                logger.error(f"❌ Erreur lors du parsing du custom_id '{custom_id}': {e}")
                return
            
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
            
            config = await self.bot.db.query(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
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
                        description=_("disboard.thank_you.role_assigned", guild_id=guild.id),
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
                        _("disboard.error.role_assignment_error", guild_id=guild.id),
                        ephemeral=True
                    )
                    
            elif action == "no":
                # User declined the role
                embed = discord.Embed(
                    title="❌ Rôle refusé",
                    description=_("disboard.thank_you.role_declined", guild_id=guild.id),
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
            servers_needing_reminders = await self.bot.db.query(
                """SELECT DISTINCT guild_id, 
                          (SELECT channel_id FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) as channel_id,
                          (SELECT bump_time FROM disboard_bumps WHERE guild_id = db.guild_id ORDER BY bump_time DESC LIMIT 1) as last_bump
                   FROM disboard_bumps db
                   WHERE bump_time < %s""",
                (reminder_threshold,),
                fetchall=True
            )
            
            for server_data in servers_needing_reminders:
                guild_id = server_data['guild_id']
                channel_id = server_data['channel_id']
                last_bump = server_data['bump_time']
                
                if not channel_id:
                    continue
                
                # Check if reminder was already sent recently
                last_reminder = await self.bot.db.query(
                    "SELECT reminder_time FROM disboard_reminders WHERE guild_id = %s ORDER BY reminder_time DESC LIMIT 1",
                    (guild_id,),
                    fetchone=True
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
            config = await self.bot.db.query(
                "SELECT bump_role_id FROM disboard_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            
            # Calculate time since last bump
            time_since_bump = datetime.utcnow() - last_bump
            hours_since_bump = int(time_since_bump.total_seconds() / 3600)
            
            # Create reminder embed
            embed = discord.Embed(
                title=_("disboard.reminder.title", guild_id=guild.id),
                description=_("disboard.reminder.description", guild_id=guild.id),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
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
                    timestamp=datetime.utcnow()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=_("commands.bumptop.embed_title", guild_id=guild_id),
                description=_("commands.bumptop.top_bumpers", guild_id=guild_id, period=period_name),
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
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
                    timestamp=datetime.utcnow()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Calculate time since last bump
            time_since_last = datetime.utcnow() - stats['last_bump']
            hours_since_last = int(time_since_last.total_seconds() / 3600)
            
            # Create stats embed
            embed = discord.Embed(
                title=_("commands.bumpstats.embed_title", guild_id=guild_id),
                description=_("commands.bumpstats.server_stats", guild_id=guild_id, server=interaction.guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name=_("commands.bumpstats.total_bumps", guild_id=guild_id), value=f"**{stats['total_bumps']}**", inline=True)
            embed.add_field(name=_("commands.bumpstats.unique_bumpers", guild_id=guild_id), value=f"**{stats['unique_bumpers']}**", inline=True)
            embed.add_field(name=_("commands.bumpstats.last_bump", guild_id=guild_id), value=f"<t:{int(stats['last_bump'].timestamp())}:R>", inline=True)
            
            embed.add_field(name=_("commands.bumpstats.first_bump", guild_id=guild_id), value=f"<t:{int(stats['first_bump'].timestamp())}:R>", inline=True)
            embed.add_field(name=_("commands.bumpstats.time_elapsed", guild_id=guild_id), value=f"**{hours_since_last}h**", inline=True)
            
            if stats['avg_hours_between']:
                embed.add_field(name=_("commands.bumpstats.avg_between", guild_id=guild_id), value=f"**{stats['avg_hours_between']:.1f}h**", inline=True)
            
            # Add bump frequency indicator
            if hours_since_last <= 2:
                status = _("commands.bumpstats.ready_bump", guild_id=guild_id)
            elif hours_since_last <= 4:
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
