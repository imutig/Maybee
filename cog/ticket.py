import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from i18n import _
from .command_logger import log_command_usage
import json
import os
import logging
from datetime import datetime
from cloud_storage import CloudTicketLogger, GoogleDriveStorage
from custom_emojis import TICKET, TICKET_CREATE, TICKET_CLOSE, TICKET_DELETE, SUCCESS, ERROR, WARNING, CLOCK, TRASH, CHECK, CROSS

logger = logging.getLogger(__name__)


class Ticket(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # Initialiser le stockage cloud
        self.cloud_storage = GoogleDriveStorage()
        self.ticket_logger = CloudTicketLogger(bot, self.cloud_storage)
        self.cloud_enabled = False  # Sera défini à True si l'initialisation réussit
    
    async def log_ticket_event(self, guild: discord.Guild, event_type: str, ticket_channel: discord.TextChannel, 
                               user: discord.Member, details: str = ""):
        """Log un événement de ticket dans le channel configuré"""
        try:
            # Récupérer le channel de logs configuré
            config = await self.bot.db.query(
                "SELECT ticket_events_log_channel_id FROM server_config WHERE guild_id = %s",
                (str(guild.id),),
                fetchone=True
            )
            
            if not config or not config.get('ticket_events_log_channel_id'):
                return  # Pas de channel configuré, on ne log pas
            
            log_channel_id = int(config['ticket_events_log_channel_id'])
            log_channel = guild.get_channel(log_channel_id)
            
            if not log_channel:
                return
            
            # Créer l'embed selon le type d'événement
            color_map = {
                "created": discord.Color.green(),
                "claimed": discord.Color.blue(),
                "closed": discord.Color.orange(),
                "deleted": discord.Color.red(),
                "reopened": discord.Color.purple(),
                "verified": discord.Color.gold()
            }
            
            emoji_map = {
                "created": "🎫",
                "claimed": "🙋",
                "closed": "🔒",
                "deleted": "🗑️",
                "reopened": "🔓",
                "verified": "✅"
            }
            
            title_map = {
                "created": "Ticket créé",
                "claimed": "Ticket pris en charge",
                "closed": "Ticket fermé",
                "deleted": "Ticket supprimé",
                "reopened": "Ticket rouvert",
                "verified": "Utilisateur vérifié"
            }
            
            embed = discord.Embed(
                title=f"{emoji_map.get(event_type, '📋')} {title_map.get(event_type, 'Événement')}",
                color=color_map.get(event_type, discord.Color.blue()),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Canal", value=ticket_channel.mention, inline=True)
            embed.add_field(name="Utilisateur", value=user.mention, inline=True)
            
            if details:
                embed.add_field(name="Détails", value=details, inline=False)
            
            embed.set_footer(text=f"ID: {ticket_channel.id}")
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors du log d'événement de ticket: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions from dashboard-created ticket panels"""
        if interaction.type != discord.InteractionType.component:
            return
            
        if not interaction.data.get('custom_id', '').startswith('ticket_button_'):
            return
            
        # Extract button ID from custom_id
        button_id = interaction.data['custom_id'].replace('ticket_button_', '')
        
        try:
            # Get button configuration from database
            button_data = await self.bot.db.query("""
                SELECT tb.id, tb.panel_id, tb.button_label, tb.button_emoji, tb.button_style, 
                       tb.category_id, tb.ticket_name_format, tb.ping_roles, tb.initial_message, 
                       tb.button_order, tp.panel_name, tp.guild_id 
                FROM ticket_buttons tb 
                JOIN ticket_panels tp ON tb.panel_id = tp.id 
                WHERE tb.id = %s
            """, (button_id,), fetchone=True)
            
            if not button_data:
                await interaction.response.send_message(_('ticket_system.button_config_not_found', interaction.user.id, interaction.guild.id), ephemeral=True)
                return
            
            # Debug logging
            print(f"DEBUG: Retrieved button data: {button_data}")
            
            # Extract values from dictionary result
            btn_id = button_data['id']
            panel_id = button_data['panel_id']
            button_label = button_data['button_label']
            button_emoji = button_data['button_emoji']
            button_style = button_data['button_style']
            category_id = button_data['category_id']
            ticket_name_format = button_data['ticket_name_format']
            ping_roles_json = button_data['ping_roles']
            initial_message = button_data['initial_message']
            button_order = button_data['button_order']
            panel_name = button_data['panel_name']
            guild_id = button_data['guild_id']
            
            # Debug logging
            print(f"DEBUG: Category ID: {category_id} (type: {type(category_id)})")
            
            # Validate category_id - handle both integer and string types
            try:
                category_id = int(category_id) if category_id is not None else None
                if not category_id or category_id <= 0:
                    print(f"DEBUG: Category ID validation failed - value: {category_id}")
                    await interaction.response.send_message(_('ticket_system.invalid_category_config', interaction.user.id, interaction.guild.id), ephemeral=True)
                    return
            except (ValueError, TypeError):
                print(f"DEBUG: Category ID conversion failed - original value: {category_id}")
                await interaction.response.send_message(_('ticket_system.invalid_category_config', interaction.user.id, interaction.guild.id), ephemeral=True)
                return
            
            # Parse ping roles - handle empty string, None, and valid JSON
            ping_roles = []
            if ping_roles_json and ping_roles_json.strip():
                try:
                    ping_roles = json.loads(ping_roles_json)
                except json.JSONDecodeError:
                    print(f"Invalid JSON in ping_roles: {ping_roles_json}")
                    ping_roles = []
            
            # Create ticket
            await self.create_dashboard_ticket(
                interaction, category_id, ticket_name_format, 
                initial_message, ping_roles, button_label, btn_id, panel_id
            )
            
        except Exception as e:
            print(f"Error handling ticket button interaction: {e}")
            await interaction.response.send_message(_('ticket_system.creation_error', interaction.user.id, interaction.guild.id), ephemeral=True)

    async def create_dashboard_ticket(self, interaction, category_id, name_format, initial_message, ping_roles, button_label, button_id, panel_id=None):
        """Create a ticket from dashboard button click"""
        guild = interaction.guild
        user = interaction.user
        
        # Get category
        category = guild.get_channel(int(category_id)) if category_id else None
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(_('ticket_system.invalid_category', interaction.user.id, interaction.guild.id), ephemeral=True)
            return
        
        # Format ticket name
        ticket_name = name_format.replace("{user}", user.name.lower()).replace("{username}", user.name.lower())
        if not ticket_name:
            ticket_name = f"ticket-{user.name.lower()}"
        
        # Check if user already has a ticket in this category
        existing = discord.utils.get(category.channels, name=ticket_name)
        if existing:
            await interaction.response.send_message(_('ticket_system.already_exists', interaction.user.id, interaction.guild.id, channel=existing.mention), ephemeral=True)
            return
        
        # Set up permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        }
        
        # Add ping roles to permissions
        for role_id in ping_roles:
            role = guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        # Create ticket channel
        try:
            channel = await guild.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                category=category,
                reason=f"Ticket created by {user} via {button_label} button"
            )
            
            # Create initial message
            embed = discord.Embed(
                title=f"🎫 {button_label}",
                description=initial_message or f"Hello {user.mention}! Please describe your issue and someone will help you soon.",
                color=0x5865F2
            )
            embed.set_footer(text=f"Ticket created by {user}", icon_url=user.display_avatar.url)
            
            # Mention roles if specified
            mentions = []
            for role_id in ping_roles:
                role = guild.get_role(int(role_id))
                if role:
                    mentions.append(role.mention)
            
            mention_content = " ".join(mentions) if mentions else ""
            
            # Fetch panel data to check if this is a verification ticket
            panel_data = None
            if panel_id:
                panel_data = await self.bot.db.query(
                    "SELECT * FROM ticket_panels WHERE id = %s AND guild_id = %s",
                    (panel_id, str(guild.id)),
                    fetchone=True
                )
            
            # Add close button (and claim button if verification ticket)
            view = TicketCloseView(panel_data)
            
            await channel.send(content=f"{user.mention} {mention_content}".strip(), embed=embed, view=view)
            
            # Store ticket in database
            await self.bot.db.execute("""
                INSERT INTO active_tickets (guild_id, channel_id, user_id, button_id, panel_id, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (str(guild.id), str(channel.id), str(user.id), button_id, panel_id))
            
            # Enregistrer l'événement de création
            await self.log_ticket_event(guild, "created", channel, user, f"Ticket créé via {button_label}")
            
            await interaction.response.send_message(_('ticket_system.created_success', interaction.user.id, interaction.guild.id, channel=channel.mention), ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message(_('ticket_system.no_permission_create', interaction.user.id, interaction.guild.id), ephemeral=True)
        except Exception as e:
            print(f"Error creating ticket: {e}")
            await interaction.response.send_message(_('ticket_system.creation_error', interaction.user.id, interaction.guild.id), ephemeral=True)

    # cleanup_ticket_data command removed - no longer needed
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Enregistrer les messages de tickets dans le cache temporaire"""
        if message.author.bot or not message.guild:
            return
        
        # Enregistrer le message dans le cache temporaire
        await self.ticket_logger.log_message(message)
    
    @app_commands.command(name="ticket_logs", description=_('ticket_system.ticket_logs.command_description', 0, 0))
    @app_commands.describe(user=_('ticket_system.ticket_logs.user_description', 0, 0))
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_logs(self, interaction: discord.Interaction, user: discord.Member):
        """Afficher les logs de tickets d'un utilisateur avec dropdown"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                _('ticket_system.ticket_logs.no_permission', user_id, guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Récupérer les logs de l'utilisateur depuis Google Drive
            user_logs = await self.ticket_logger.get_user_ticket_logs(guild_id, user.id)
            
            if not user_logs:
                await interaction.followup.send(
                    _('ticket_system.ticket_logs.no_logs_found', user_id, guild_id, user=user.mention), ephemeral=True)
                return
            
            # Créer l'embed principal
            embed = discord.Embed(
                title=_('ticket_system.ticket_logs.title', user_id, guild_id, user=user.display_name),
                description=_('ticket_system.ticket_logs.description', user_id, guild_id, 
                             count=len(user_logs), user=user.mention),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('ticket_system.ticket_logs.statistics', user_id, guild_id),
                value=_('ticket_system.ticket_logs.stats_content', user_id, guild_id, 
                       count=len(user_logs), user=user.mention, user_id=user.id),
                inline=False
            )
            
            embed.set_footer(text=_('ticket_system.ticket_logs.requested_by', user_id, guild_id, user=interaction.user.display_name))
            
            # Créer la vue avec dropdown
            view = TicketLogsView(user_logs, user, page=0)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error retrieving ticket logs: {e}")
            await interaction.followup.send(
                _('ticket_system.ticket_logs.retrieval_error', user_id, guild_id), ephemeral=True)
    
    @app_commands.command(name="new_ticket", description=_('ticket_system.new_ticket.command_description', 0, 0))
    @app_commands.describe(
        user=_('ticket_system.new_ticket.user_description', 0, 0),
        category=_('ticket_system.new_ticket.category_description', 0, 0),
        reason=_('ticket_system.new_ticket.reason_description', 0, 0)
    )
    @app_commands.default_permissions(manage_channels=True)
    async def new_ticket(self, interaction: discord.Interaction, user: discord.Member, category: discord.CategoryChannel, reason: str):
        """Créer un ticket pour un autre utilisateur"""
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Déférer l'interaction immédiatement pour éviter les timeouts
        await interaction.response.defer(ephemeral=True)
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send(
                _("ticket_system.new_ticket.no_permission", interaction.user.id, guild_id), ephemeral=True)
            return
        
        # Vérifier que l'utilisateur n'est pas un bot
        if user.bot:
            await interaction.followup.send(
                _("ticket_system.new_ticket.bot_user", interaction.user.id, guild_id), ephemeral=True)
            return
        
        # Vérifier que l'utilisateur n'est pas soi-même
        if user.id == interaction.user.id:
            await interaction.followup.send(
                _("ticket_system.new_ticket.self_user", interaction.user.id, guild_id), ephemeral=True)
            return
        
        try:
            # Récupérer la configuration des logs (optionnel)
            ticket_config = await self.bot.db.query(
                "SELECT ticket_logs_channel_id FROM server_config WHERE guild_id = %s",
                (str(guild_id),),
                fetchone=True
            )
            
            logs_channel_id = None
            if ticket_config:
                logs_channel_id = ticket_config.get('ticket_logs_channel_id')
            
            # Générer un ID de ticket unique
            ticket_id = await self._generate_ticket_id(guild_id)
            
            # Créer le canal de ticket
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            }
            
            # Ajouter les permissions pour les modérateurs
            for role in interaction.guild.roles:
                if role.permissions.manage_channels:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            # Créer un nom de canal basé sur le nom d'utilisateur
            username = user.display_name.lower().replace(" ", "-").replace("_", "-")
            # Nettoyer le nom pour qu'il soit compatible avec Discord (max 100 caractères, pas de caractères spéciaux)
            import re
            username = re.sub(r'[^a-z0-9\-]', '', username)[:50]  # Limiter à 50 caractères
            if not username:  # Si le nom est vide après nettoyage, utiliser "user"
                username = "user"
            
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{username}",
                category=category,
                overwrites=overwrites,
                reason=f"Ticket créé par {interaction.user.display_name} pour {user.display_name}"
            )
            
            # Créer l'embed de bienvenue
            embed = discord.Embed(
                title=_('ticket_system.new_ticket.embed_title', user.id, guild_id, ticket_id=ticket_id),
                description=_('ticket_system.new_ticket.embed_description', user.id, guild_id, 
                             user=user.mention, creator=interaction.user.mention, category=category.name, reason=reason),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('ticket_system.new_ticket.ticket_info', user.id, guild_id),
                value=_('ticket_system.new_ticket.ticket_info_content', user.id, guild_id,
                       creator=interaction.user.display_name, user=user.display_name, category=category.name, ticket_id=ticket_id),
                inline=False
            )
            
            embed.set_footer(text=_('ticket_system.new_ticket.footer', user.id, guild_id, creator=interaction.user.display_name))
            
            # Créer la vue avec le bouton de fermeture
            view = TicketCloseView()
            
            # Envoyer le message dans le canal de ticket
            await channel.send(content=user.mention, embed=embed, view=view)
            
            # Enregistrer le ticket dans la base de données (utiliser la même structure que les tickets existants)
            # Utiliser NULL pour button_id et panel_id car ce ticket ne provient pas d'un bouton dashboard
            await self.bot.db.execute("""
                INSERT INTO active_tickets (guild_id, channel_id, user_id, button_id, panel_id, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (str(guild_id), str(channel.id), str(user.id), None, None))
            
            # Enregistrer l'événement de création
            await self.ticket_logger.log_ticket_event(
                guild_id, channel.id, "created", interaction.user.id, interaction.user.display_name,
                f"Ticket créé par {interaction.user.display_name} pour {user.display_name} - Raison: {reason}"
            )
            
            # Envoyer un message de confirmation à l'utilisateur qui a créé le ticket
            await interaction.followup.send(
                _('ticket_system.new_ticket.confirmation', interaction.user.id, guild_id,
                 channel=channel.mention, user=user.mention, category=category.name, reason=reason, ticket_id=ticket_id), ephemeral=True)
            
            # Envoyer un message dans le canal de logs si configuré
            if logs_channel_id:
                logs_channel = interaction.guild.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title=f"{TICKET_CREATE} Nouveau ticket créé",
                        description=f"**ID :** #{ticket_id}\n**Créateur :** {interaction.user.mention}\n**Utilisateur :** {user.mention}\n**Canal :** {channel.mention}\n**Catégorie :** {category.name}\n**Raison :** {reason}",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    await logs_channel.send(embed=log_embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du ticket: {e}")
            await interaction.followup.send(
                _("ticket_system.new_ticket.error", interaction.user.id, guild_id), ephemeral=True)
    
    async def _generate_ticket_id(self, guild_id: int) -> int:
        """Générer un ID de ticket unique pour le serveur"""
        try:
            # Compter le nombre de tickets existants pour ce serveur
            result = await self.bot.db.query(
                "SELECT COUNT(*) as count FROM active_tickets WHERE guild_id = %s",
                (str(guild_id),),
                fetchone=True
            )
            
            if result and result.get('count') is not None:
                return result['count'] + 1
            else:
                return 1
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'ID de ticket: {e}")
            return 1
    
    # Commande ticket_details supprimée - remplacée par le système de dropdown


class TicketCreateButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Create a ticket",
                         custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            await interaction.response.send_message(
                _("ticket_system.create.category_not_found", user_id, guild_id), ephemeral=True)
            return

        existing = discord.utils.get(category.channels,
                                     name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                _("ticket_system.create.already_exists", user_id, guild_id), ephemeral=True)
            return

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(view_channel=False),
            user:
            discord.PermissionOverwrite(view_channel=True,
                                        send_messages=True,
                                        read_message_history=True),
            guild.me:
            discord.PermissionOverwrite(view_channel=True)
        }
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            overwrites=overwrites,
            category=category,
            reason=f"Ticket created by {user}")
        embed = discord.Embed(
            title=_("ticket_system.create.embed_title", user_id, guild_id),
            description=_("ticket_system.create.embed_description", user_id, guild_id, user=user.mention),
            color=discord.Color.blue())
        view = TicketCloseView()
        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            _("ticket_system.create.success", user_id, guild_id, channel=channel.mention), ephemeral=True)


class TicketCloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red,
                         label=_('ticket_system.close_button', 0, 0),
                         custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        channel = interaction.channel
        
        # Vérifier si c'est un ticket
        ticket_data = await interaction.client.db.query(
            "SELECT * FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(channel.id), str(guild_id)),
            fetchone=True
        )
        
        # Debug: Afficher les données du ticket
        print(f"DEBUG TicketCloseButton: ticket_data = {ticket_data}")
        
        if not ticket_data:
            await interaction.response.send_message(_('ticket_system.not_a_ticket', user_id, guild_id), ephemeral=True)
            return
        
        # Récupérer les données du panel pour les options de vérification
        panel_data = None
        if ticket_data.get('panel_id'):
            panel_data = await interaction.client.db.query(
                "SELECT * FROM ticket_panels WHERE id = %s AND guild_id = %s",
                (ticket_data['panel_id'], str(guild_id)),
                fetchone=True
            )
            # Debug: Afficher les données du panel récupérées
            if panel_data:
                print(f"DEBUG: Panel data récupéré pour le ticket: {panel_data}")
                print(f"DEBUG: verification_enabled = {panel_data.get('verification_enabled')}")
                print(f"DEBUG: verifier_role_id = {panel_data.get('verifier_role_id')}")
        
        # Retirer les permissions du créateur du ticket
        ticket_creator_id = int(ticket_data['user_id'])
        ticket_creator = interaction.guild.get_member(ticket_creator_id)
        
        if ticket_creator:
            # Modifier les permissions pour retirer l'accès au créateur
            overwrites = channel.overwrites
            overwrites[ticket_creator] = discord.PermissionOverwrite(
                view_channel=False,
                send_messages=False,
                read_message_history=False
            )
            await channel.edit(overwrites=overwrites)
        
        # Créer l'embed de fermeture
        embed = discord.Embed(
            title=_('ticket_system.ticket_closed', user_id, guild_id),
            description=_('ticket_system.ticket_closed_description', user_id, guild_id, user=interaction.user.display_name),
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=_('ticket_system.closed_by', user_id, guild_id, user=interaction.user), icon_url=interaction.user.display_avatar.url)
        
        # Créer un embed informatif pour les logs
        info_embed = discord.Embed(
            title="📋 Récupération des logs",
            description="Vous pouvez consulter l'historique des tickets de plusieurs façons :",
            color=discord.Color.blue()
        )
        info_embed.add_field(
            name="📝 Via commande",
            value=f"Utilisez `/ticket_logs` pour voir tous les tickets d'un utilisateur",
            inline=False
        )
        info_embed.add_field(
            name="🌐 Via le dashboard",
            value="Rendez-vous sur le [dashboard web](https://web-production-448ba.up.railway.app/dashboard) dans la section **Logs de Tickets**",
            inline=False
        )
        info_embed.add_field(
            name="💾 Transcripts",
            value="Les transcripts complets seront envoyés dans le canal de logs configuré (si activé)",
            inline=False
        )
        info_embed.set_footer(text="Ce message disparaîtra après 30 secondes")
        
        # Créer la vue de confirmation avec les données du panel
        view = TicketConfirmCloseView(interaction.user.id, panel_data)
        
        await interaction.response.send_message(embeds=[embed, info_embed], view=view)
        
        # Supprimer le message informatif après 30 secondes
        try:
            await asyncio.sleep(30)
            response_message = await interaction.original_response()
            # Récréer l'embed sans l'info
            await response_message.edit(embeds=[embed], view=view)
        except:
            pass  # Ignore si le message a déjà été supprimé ou le ticket fermé
        
        # Enregistrer l'événement de fermeture
        ticket_cog = interaction.client.get_cog('Ticket')
        if ticket_cog and ticket_creator:
            await ticket_cog.log_ticket_event(
                interaction.guild, "closed", channel, interaction.user,
                f"Ticket fermé par {interaction.user.display_name}"
            )


class ClaimTicketButton(discord.ui.Button):
    """Bouton pour prendre en charge un ticket de vérification"""
    
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary,
                         label="Prendre en charge",
                         emoji="🙋",
                         custom_id="claim_ticket")
    
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        channel = interaction.channel
        
        # Récupérer les données du ticket
        ticket_data = await interaction.client.db.query(
            "SELECT * FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(channel.id), str(guild_id)),
            fetchone=True
        )
        
        if not ticket_data:
            await interaction.response.send_message("❌ Ticket introuvable.", ephemeral=True)
            return
        
        # Récupérer les données du panel
        panel_data = None
        if ticket_data.get('panel_id'):
            panel_data = await interaction.client.db.query(
                "SELECT * FROM ticket_panels WHERE id = %s AND guild_id = %s",
                (ticket_data['panel_id'], str(guild_id)),
                fetchone=True
            )
        
        # Vérifier si l'utilisateur a le rôle vérificateur
        if panel_data and panel_data.get('verifier_role_id'):
            verifier_role_id = int(panel_data['verifier_role_id'])
            has_role = any(role.id == verifier_role_id for role in interaction.user.roles)
            if not has_role and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Vous n'avez pas le rôle nécessaire pour prendre en charge ce ticket.", 
                    ephemeral=True
                )
                return
        
        # Mettre à jour le ticket avec le claimer
        await interaction.client.db.execute(
            "UPDATE active_tickets SET claimed_by = %s WHERE channel_id = %s AND guild_id = %s",
            (str(user_id), str(channel.id), str(guild_id))
        )
        
        # Enregistrer l'événement
        ticket_cog = interaction.client.get_cog('Ticket')
        if ticket_cog:
            await ticket_cog.log_ticket_event(
                interaction.guild, "claimed", channel, interaction.user,
                f"Ticket pris en charge par {interaction.user.display_name}"
            )
        
        # Créer l'embed de confirmation
        embed = discord.Embed(
            title="✅ Ticket pris en charge",
            description=f"{interaction.user.mention} a pris en charge ce ticket.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())


class TicketConfirmCloseView(discord.ui.View):
    """Vue de confirmation pour la suppression définitive du ticket"""
    
    def __init__(self, closer_id: int, panel_data: dict = None):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.closer_id = closer_id
        self.panel_data = panel_data
        
        # Debug: Afficher les informations du panel
        print(f"DEBUG TicketConfirmCloseView: panel_data = {panel_data}")
        if panel_data:
            verification_enabled = panel_data.get('verification_enabled')
            print(f"DEBUG TicketConfirmCloseView: verification_enabled = {verification_enabled}")
            print(f"DEBUG TicketConfirmCloseView: Type de verification_enabled = {type(verification_enabled)}")
            print(f"DEBUG TicketConfirmCloseView: Bool test = {bool(verification_enabled)}")
        
        self.add_item(TicketConfirmDeleteButton())
        
        # Ajouter le bouton de vérification si le panel a l'option de vérification activée
        # Vérifier explicitement si verification_enabled est True ou 1
        if panel_data:
            verification_enabled = panel_data.get('verification_enabled')
            # Gérer les cas où verification_enabled peut être 0, 1, True, False, ou None
            is_verification_enabled = verification_enabled in (1, True, '1')
            print(f"DEBUG TicketConfirmCloseView: is_verification_enabled = {is_verification_enabled}")
            
            if is_verification_enabled:
                print("DEBUG TicketConfirmCloseView: Ajout du bouton de vérification")
                self.add_item(TicketCloseAndVerifyButton(panel_data))
            else:
                print("DEBUG TicketConfirmCloseView: Pas de bouton de vérification ajouté")
        
        self.add_item(TicketReopenButton())

class TicketConfirmDeleteButton(discord.ui.Button):
    """Bouton pour confirmer la suppression définitive"""
    
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger,
                         label="Fermer définitivement",
                         custom_id="confirm_delete_ticket")
    
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                _('ticket_system.no_permission_delete', user_id, guild_id), ephemeral=True)
            return
        
        channel = interaction.channel
        
        # Enregistrer l'événement de suppression
        ticket_cog = interaction.client.get_cog('Ticket')
        if ticket_cog:
            await ticket_cog.log_ticket_event(
                interaction.guild, "deleted", channel, interaction.user,
                f"Ticket supprimé définitivement par {interaction.user.display_name}"
            )
        
        # Récupérer les informations du ticket depuis la base de données
        ticket_data = await interaction.client.db.query(
            "SELECT * FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(channel.id), str(guild_id)),
            fetchone=True
        )
        
        # Ajouter les informations utilisateur aux logs si disponibles
        if ticket_data:
            ticket_cog = interaction.client.get_cog('Ticket')
            ticket_key = f"{guild_id}_{channel.id}"
            
            if ticket_key in ticket_cog.ticket_logger.ticket_cache:
                logs_data = ticket_cog.ticket_logger.ticket_cache[ticket_key]
                
                # Ajouter les informations utilisateur depuis la base de données
                logs_data["ticket_user_id"] = ticket_data.get("user_id")
                
                # Essayer de récupérer les informations utilisateur depuis Discord
                try:
                    user = interaction.guild.get_member(int(ticket_data["user_id"]))
                    if user:
                        logs_data["ticket_username"] = user.name
                        logs_data["ticket_discriminator"] = user.discriminator
                        logs_data["ticket_display_name"] = user.display_name
                        logs_data["ticket_avatar_url"] = str(user.display_avatar.url) if user.display_avatar else None
                except Exception as e:
                    logger.warning(f"Impossible de récupérer les informations utilisateur: {e}")
        
        # Finaliser et uploader les logs vers Google Drive
        ticket_cog = interaction.client.get_cog('Ticket')
        file_id = await ticket_cog.ticket_logger.finalize_ticket_logs(guild_id, channel.id)
        
        if file_id:
            logger.info(f"Logs du ticket {channel.id} uploadés vers Google Drive: {file_id}")
        else:
            logger.warning(f"Échec de l'upload des logs pour le ticket {channel.id}")
        
        # Supprimer le ticket de la base de données
        await interaction.client.db.execute(
            "DELETE FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(channel.id), str(guild_id))
        )
        
        try:
            await interaction.response.send_message(
                _('ticket_system.ticket_deleted_permanently', user_id, guild_id), ephemeral=True)
        except discord.NotFound:
            # L'interaction a expiré, utiliser followup
            await interaction.followup.send(
                _('ticket_system.ticket_deleted_permanently', user_id, guild_id), ephemeral=True)
        
        # Supprimer le canal
        await asyncio.sleep(2)
        await channel.delete(reason=f"Ticket deleted by {interaction.user}")

class TicketCloseAndVerifyButton(discord.ui.Button):
    """Bouton pour fermer le ticket et vérifier le membre"""
    
    def __init__(self, panel_data: dict):
        super().__init__(style=discord.ButtonStyle.primary,
                         label="Fermer et vérifier le membre",
                         custom_id="close_and_verify_ticket")
        self.panel_data = panel_data
    
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Vérifier si l'utilisateur a le rôle vérificateur
        verifier_role_id = self.panel_data.get('verifier_role_id')
        if verifier_role_id:
            has_role = any(role.id == int(verifier_role_id) for role in interaction.user.roles)
            if not has_role and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Vous n'avez pas le rôle nécessaire pour vérifier des membres.", 
                    ephemeral=True
                )
                return
        
        channel = interaction.channel
        
        # Récupérer les données du ticket
        ticket_data = await interaction.client.db.query(
            "SELECT * FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(channel.id), str(guild_id)),
            fetchone=True
        )
        
        if not ticket_data:
            await interaction.response.send_message("❌ Ticket introuvable dans la base de données.", ephemeral=True)
            return
        
        # Récupérer le membre du ticket
        ticket_user_id = int(ticket_data['user_id'])
        ticket_member = interaction.guild.get_member(ticket_user_id)
        
        if not ticket_member:
            await interaction.response.send_message("❌ Le membre du ticket est introuvable.", ephemeral=True)
            return
        
        try:
            # Retirer les rôles spécifiés
            roles_to_remove = self.panel_data.get('roles_to_remove', [])
            if roles_to_remove:
                try:
                    roles_to_remove = json.loads(roles_to_remove) if isinstance(roles_to_remove, str) else roles_to_remove
                except:
                    roles_to_remove = []
                
                for role_id in roles_to_remove:
                    role = interaction.guild.get_role(int(role_id))
                    if role and role in ticket_member.roles:
                        await ticket_member.remove_roles(role)
            
            # Ajouter les rôles spécifiés
            roles_to_add = self.panel_data.get('roles_to_add', [])
            if roles_to_add:
                try:
                    roles_to_add = json.loads(roles_to_add) if isinstance(roles_to_add, str) else roles_to_add
                except:
                    roles_to_add = []
                
                for role_id in roles_to_add:
                    role = interaction.guild.get_role(int(role_id))
                    if role and role not in ticket_member.roles:
                        await ticket_member.add_roles(role)
            
            # Envoyer le message de vérification
            verification_channel_id = self.panel_data.get('verification_channel')
            verification_message = self.panel_data.get('verification_message', '{user} a été vérifié avec succès !')
            verification_image_url = self.panel_data.get('verification_image_url')
            
            print(f"DEBUG: verification_channel_id = {verification_channel_id}")
            print(f"DEBUG: verification_message = {verification_message}")
            print(f"DEBUG: verification_image_url = {verification_image_url}")
            
            if verification_channel_id:
                verification_channel = interaction.guild.get_channel(int(verification_channel_id))
                print(f"DEBUG: verification_channel = {verification_channel}")
                
                if verification_channel:
                    message = verification_message.replace('{user}', ticket_member.mention)
                    message = message.replace('{server}', interaction.guild.name)
                    message = message.replace('{channel}', channel.mention)
                    
                    print(f"DEBUG: Message formaté = {message}")
                    
                    embed = discord.Embed(
                        title="✅ Membre vérifié",
                        description=message,
                        color=0xFFD700,  # Couleur or
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text=f"Vérifié par {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
                    
                    # Ajouter l'image si une URL est fournie
                    if verification_image_url:
                        embed.set_image(url=verification_image_url)
                    
                    try:
                        # Envoyer le message avec mention du membre vérifié
                        await verification_channel.send(content=ticket_member.mention, embed=embed)
                        print("DEBUG: Message de vérification envoyé avec succès")
                    except Exception as send_error:
                        print(f"DEBUG: Erreur lors de l'envoi du message: {send_error}")
                else:
                    print("DEBUG: Canal de vérification introuvable")
            else:
                print("DEBUG: Pas de canal de vérification configuré")
            
            # Enregistrer l'événement
            ticket_cog = interaction.client.get_cog('Ticket')
            if ticket_cog:
                await ticket_cog.log_ticket_event(
                    interaction.guild, "verified", channel, interaction.user,
                    f"Membre {ticket_member.display_name} vérifié et ticket fermé par {interaction.user.display_name}"
                )
            
            # Supprimer le ticket de la base de données
            await interaction.client.db.execute(
                "DELETE FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
                (str(channel.id), str(guild_id))
            )
            
            # Finaliser et uploader les logs
            ticket_cog = interaction.client.get_cog('Ticket')
            file_id = await ticket_cog.ticket_logger.finalize_ticket_logs(guild_id, channel.id)
            
            await interaction.response.send_message(
                f"✅ Membre {ticket_member.mention} vérifié avec succès ! Le ticket sera supprimé dans 5 secondes.", 
                ephemeral=True
            )
            
            # Supprimer le canal après 5 secondes
            await asyncio.sleep(5)
            await channel.delete(reason=f"Ticket fermé et membre vérifié par {interaction.user}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du membre: {e}")
            await interaction.response.send_message(f"❌ Erreur lors de la vérification: {str(e)}", ephemeral=True)

class TicketReopenButton(discord.ui.Button):
    """Bouton pour rouvrir le ticket"""
    
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Réouvrir le ticket",
                         custom_id="reopen_ticket")
    
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                _('ticket_system.no_permission_manage', user_id, guild_id), ephemeral=True)
            return
        
        channel = interaction.channel
        
        # Récupérer les données du ticket
        ticket_data = await interaction.client.db.query(
            "SELECT * FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(channel.id), str(guild_id)),
            fetchone=True
        )
        
        if not ticket_data:
            await interaction.response.send_message(_('ticket_system.ticket_data_not_found', user_id, guild_id), ephemeral=True)
            return
        
        # Restaurer les permissions du créateur
        ticket_creator_id = int(ticket_data['user_id'])
        ticket_creator = interaction.guild.get_member(ticket_creator_id)
        
        if ticket_creator:
            overwrites = channel.overwrites
            overwrites[ticket_creator] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
            await channel.edit(overwrites=overwrites)
        
        # Créer l'embed de réouverture
        embed = discord.Embed(
            title=_('ticket_system.ticket_reopened', user_id, guild_id),
            description=_('ticket_system.ticket_reopened_description', user_id, guild_id, user=interaction.user.display_name),
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=_('ticket_system.reopened_by', user_id, guild_id, user=interaction.user), icon_url=interaction.user.display_avatar.url)
        
        # Ajouter le bouton de fermeture
        view = TicketCloseView()
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Enregistrer l'événement de réouverture
        ticket_cog = interaction.client.get_cog('Ticket')
        if ticket_cog and ticket_creator:
            await ticket_cog.log_ticket_event(
                interaction.guild, "reopened", channel, interaction.user,
                f"Ticket rouvert par {interaction.user.display_name}"
            )

class TicketLogsDropdown(discord.ui.Select):
    """Dropdown pour sélectionner un ticket dans les logs"""
    
    def __init__(self, tickets: list, page: int = 0):
        self.tickets = tickets
        self.page = page
        self.tickets_per_page = 25  # Limite Discord
        
        # Calculer les tickets à afficher pour cette page
        start_idx = page * self.tickets_per_page
        end_idx = start_idx + self.tickets_per_page
        page_tickets = tickets[start_idx:end_idx]
        
        options = []
        for i, ticket in enumerate(page_tickets):
            ticket_id = ticket.get('ticket_id', 'Inconnu')
            created_at = ticket.get('created_at', 'Inconnu')
            message_count = ticket.get('message_count', 0)
            
            # Formater la date de création
            try:
                if created_at != 'Inconnu':
                    dt = datetime.fromisoformat(created_at)
                    date_str = dt.strftime("%d/%m/%Y %H:%M")
                else:
                    date_str = "Inconnu"
            except:
                date_str = created_at
            
            # Créer l'option
            option = discord.SelectOption(
                label=f"Ticket #{start_idx + i + 1}",
                description=f"{date_str} • {message_count} messages",
                value=str(start_idx + i),  # Index du ticket dans la liste complète
                emoji="🎫"
            )
            options.append(option)
        
        super().__init__(
            placeholder=f"Sélectionnez un ticket (Page {page + 1})",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Appelé quand un ticket est sélectionné"""
        try:
            ticket_index = int(self.values[0])
            selected_ticket = self.tickets[ticket_index]
            
            # Créer la vue pour afficher les détails du ticket
            view = TicketDetailsView(selected_ticket, self.tickets, ticket_index)
            
            # Créer l'embed avec les détails du ticket
            embed = await self.create_ticket_details_embed(selected_ticket)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du ticket: {e}")
            await interaction.response.send_message(
                "❌ Erreur lors de l'affichage des détails du ticket.", ephemeral=True)
    
    async def create_ticket_details_embed(self, ticket_data: dict) -> discord.Embed:
        """Crée l'embed avec les détails d'un ticket"""
        ticket_id = ticket_data.get('ticket_id', 'Inconnu')
        created_at = ticket_data.get('created_at', 'Inconnu')
        messages = ticket_data.get('messages', [])
        events = ticket_data.get('events', [])
        
        embed = discord.Embed(
            title=f"📋 Détails du ticket #{ticket_id}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Informations générales
        created_timestamp = "Inconnu"
        if created_at != 'Inconnu':
            try:
                created_timestamp = f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:F>"
            except (ValueError, TypeError):
                created_timestamp = created_at
        
        embed.add_field(
            name="📊 Informations générales",
            value=f"**ID du ticket :** {ticket_id}\n"
                  f"**Créé le :** {created_timestamp}\n"
                  f"**Messages :** {len(messages)}\n"
                  f"**Événements :** {len(events)}",
            inline=False
        )
        
        # Afficher les derniers messages
        if messages:
            recent_messages = messages[-3:]  # 3 derniers messages
            message_text = ""
            for msg in recent_messages:
                author = msg.get('author_name', 'Inconnu')
                content = msg.get('content', 'Pas de contenu')[:100]
                timestamp = msg.get('timestamp', 'Inconnu')
                message_text += f"**{author}** : {content}...\n"
            
            embed.add_field(
                name="💬 Derniers messages",
                value=message_text or "Aucun message",
                inline=False
            )
        
        # Afficher les événements
        if events:
            event_text = ""
            for event in events[-3:]:  # 3 derniers événements
                event_type = event.get('type', 'Inconnu')
                user_name = event.get('user_name', 'Inconnu')
                timestamp = event.get('timestamp', 'Inconnu')
                event_text += f"**{event_type}** par {user_name}\n"
            
            embed.add_field(
                name="📝 Événements récents",
                value=event_text or "Aucun événement",
                inline=False
            )
        
        embed.set_footer(text="Utilisez les boutons pour naviguer")
        
        return embed

class TicketDetailsView(discord.ui.View):
    """Vue pour afficher les détails d'un ticket avec navigation"""
    
    def __init__(self, ticket_data: dict, all_tickets: list, current_index: int):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.ticket_data = ticket_data
        self.all_tickets = all_tickets
        self.current_index = current_index
        
        # Bouton précédent
        if current_index > 0:
            self.add_item(TicketPreviousButton(ticket_data, all_tickets, current_index))
        
        # Bouton suivant
        if current_index < len(all_tickets) - 1:
            self.add_item(TicketNextButton(ticket_data, all_tickets, current_index))
        
        # Bouton pour voir tous les messages
        if ticket_data.get('messages'):
            self.add_item(TicketMessagesButton(ticket_data))

class TicketPreviousButton(discord.ui.Button):
    """Bouton pour aller au ticket précédent"""
    
    def __init__(self, ticket_data: dict, all_tickets: list, current_index: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="◀️ Précédent", emoji="◀️")
        self.ticket_data = ticket_data
        self.all_tickets = all_tickets
        self.current_index = current_index
    
    async def callback(self, interaction: discord.Interaction):
        try:
            if self.current_index > 0:
                previous_ticket = self.all_tickets[self.current_index - 1]
                
                # Créer l'embed pour le ticket précédent
                embed = await self.create_ticket_details_embed(previous_ticket)
                
                # Créer la nouvelle vue
                view = TicketDetailsView(previous_ticket, self.all_tickets, self.current_index - 1)
                
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message("❌ Aucun ticket précédent.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la navigation vers le ticket précédent: {e}")
            await interaction.response.send_message("❌ Erreur lors de la navigation.", ephemeral=True)
    
    async def create_ticket_details_embed(self, ticket_data: dict) -> discord.Embed:
        """Crée l'embed avec les détails d'un ticket"""
        ticket_id = ticket_data.get('ticket_id', 'Inconnu')
        created_at = ticket_data.get('created_at', 'Inconnu')
        messages = ticket_data.get('messages', [])
        events = ticket_data.get('events', [])
        
        embed = discord.Embed(
            title=f"📋 Détails du ticket #{ticket_id}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Informations générales
        created_timestamp = "Inconnu"
        if created_at != 'Inconnu':
            try:
                created_timestamp = f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:F>"
            except (ValueError, TypeError):
                created_timestamp = created_at
        
        embed.add_field(
            name="📊 Informations générales",
            value=f"**ID du ticket :** {ticket_id}\n"
                  f"**Créé le :** {created_timestamp}\n"
                  f"**Messages :** {len(messages)}\n"
                  f"**Événements :** {len(events)}",
            inline=False
        )
        
        # Afficher les derniers messages
        if messages:
            recent_messages = messages[-3:]  # 3 derniers messages
            message_text = ""
            for msg in recent_messages:
                author = msg.get('author_name', 'Inconnu')
                content = msg.get('content', 'Pas de contenu')[:100]
                timestamp = msg.get('timestamp', 'Inconnu')
                message_text += f"**{author}** : {content}...\n"
            
            embed.add_field(
                name="💬 Derniers messages",
                value=message_text or "Aucun message",
                inline=False
            )
        
        # Afficher les événements
        if events:
            event_text = ""
            for event in events[-3:]:  # 3 derniers événements
                event_type = event.get('type', 'Inconnu')
                user_name = event.get('user_name', 'Inconnu')
                timestamp = event.get('timestamp', 'Inconnu')
                event_text += f"**{event_type}** par {user_name}\n"
            
            embed.add_field(
                name="📝 Événements récents",
                value=event_text or "Aucun événement",
                inline=False
            )
        
        embed.set_footer(text="Utilisez les boutons pour naviguer")
        
        return embed

class TicketNextButton(discord.ui.Button):
    """Bouton pour aller au ticket suivant"""
    
    def __init__(self, ticket_data: dict, all_tickets: list, current_index: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="Suivant ▶️", emoji="▶️")
        self.ticket_data = ticket_data
        self.all_tickets = all_tickets
        self.current_index = current_index
    
    async def callback(self, interaction: discord.Interaction):
        try:
            if self.current_index < len(self.all_tickets) - 1:
                next_ticket = self.all_tickets[self.current_index + 1]
                
                # Créer l'embed pour le ticket suivant
                embed = await self.create_ticket_details_embed(next_ticket)
                
                # Créer la nouvelle vue
                view = TicketDetailsView(next_ticket, self.all_tickets, self.current_index + 1)
                
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message("❌ Aucun ticket suivant.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la navigation vers le ticket suivant: {e}")
            await interaction.response.send_message("❌ Erreur lors de la navigation.", ephemeral=True)
    
    async def create_ticket_details_embed(self, ticket_data: dict) -> discord.Embed:
        """Crée l'embed avec les détails d'un ticket"""
        ticket_id = ticket_data.get('ticket_id', 'Inconnu')
        created_at = ticket_data.get('created_at', 'Inconnu')
        messages = ticket_data.get('messages', [])
        events = ticket_data.get('events', [])
        
        embed = discord.Embed(
            title=f"📋 Détails du ticket #{ticket_id}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Informations générales
        created_timestamp = "Inconnu"
        if created_at != 'Inconnu':
            try:
                created_timestamp = f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:F>"
            except (ValueError, TypeError):
                created_timestamp = created_at
        
        embed.add_field(
            name="📊 Informations générales",
            value=f"**ID du ticket :** {ticket_id}\n"
                  f"**Créé le :** {created_timestamp}\n"
                  f"**Messages :** {len(messages)}\n"
                  f"**Événements :** {len(events)}",
            inline=False
        )
        
        # Afficher les derniers messages
        if messages:
            recent_messages = messages[-3:]  # 3 derniers messages
            message_text = ""
            for msg in recent_messages:
                author = msg.get('author_name', 'Inconnu')
                content = msg.get('content', 'Pas de contenu')[:100]
                timestamp = msg.get('timestamp', 'Inconnu')
                message_text += f"**{author}** : {content}...\n"
            
            embed.add_field(
                name="💬 Derniers messages",
                value=message_text or "Aucun message",
                inline=False
            )
        
        # Afficher les événements
        if events:
            event_text = ""
            for event in events[-3:]:  # 3 derniers événements
                event_type = event.get('type', 'Inconnu')
                user_name = event.get('user_name', 'Inconnu')
                timestamp = event.get('timestamp', 'Inconnu')
                event_text += f"**{event_type}** par {user_name}\n"
            
            embed.add_field(
                name="📝 Événements récents",
                value=event_text or "Aucun événement",
                inline=False
            )
        
        embed.set_footer(text="Utilisez les boutons pour naviguer")
        
        return embed

class TicketMessagesButton(discord.ui.Button):
    """Bouton pour voir tous les messages du ticket"""
    
    def __init__(self, ticket_data: dict):
        super().__init__(style=discord.ButtonStyle.primary, label="💬 Voir tous les messages", emoji="💬")
        self.ticket_data = ticket_data
    
    async def callback(self, interaction: discord.Interaction):
        try:
            messages = self.ticket_data.get('messages', [])
            
            if not messages:
                await interaction.response.send_message("❌ Aucun message trouvé dans ce ticket.", ephemeral=True)
                return
            
            # Créer l'embed avec les premiers messages
            embed = await self.create_messages_embed(messages, 0)
            
            # Créer la vue avec pagination si nécessaire
            view = TicketMessagesView(messages, self.ticket_data, 0)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage des messages: {e}")
            await interaction.response.send_message("❌ Erreur lors de l'affichage des messages.", ephemeral=True)
    
    async def create_messages_embed(self, messages: list, page: int = 0) -> discord.Embed:
        """Crée l'embed avec les messages paginés"""
        ticket_id = self.ticket_data.get('ticket_id', 'Inconnu')
        messages_per_page = 10
        start_idx = page * messages_per_page
        end_idx = start_idx + messages_per_page
        page_messages = messages[start_idx:end_idx]
        
        total_pages = (len(messages) + messages_per_page - 1) // messages_per_page
        
        embed = discord.Embed(
            title=f"💬 Messages du ticket #{ticket_id}",
            description=f"Page {page + 1}/{total_pages} • {len(messages)} messages au total",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Afficher les messages de cette page
        for i, msg in enumerate(page_messages):
            author = msg.get('author_name', 'Inconnu')
            content = msg.get('content', 'Pas de contenu')
            timestamp = msg.get('timestamp', 'Inconnu')
            
            # Formater le timestamp
            try:
                if timestamp != 'Inconnu':
                    dt = datetime.fromisoformat(timestamp)
                    time_str = f"<t:{int(dt.timestamp())}:R>"
                else:
                    time_str = "Inconnu"
            except:
                time_str = timestamp
            
            # Limiter la longueur du contenu
            if len(content) > 300:
                content = content[:300] + "..."
            
            embed.add_field(
                name=f"💬 {author}",
                value=f"{content}\n\n*{time_str}*",
                inline=False
            )
        
        embed.set_footer(text=f"Messages {start_idx + 1}-{min(end_idx, len(messages))} sur {len(messages)}")
        
        return embed

class TicketMessagesView(discord.ui.View):
    """Vue pour afficher les messages avec pagination"""
    
    def __init__(self, messages: list, ticket_data: dict, page: int = 0):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.messages = messages
        self.ticket_data = ticket_data
        self.page = page
        self.messages_per_page = 10
        
        # Calculer le nombre total de pages
        self.total_pages = (len(messages) + self.messages_per_page - 1) // self.messages_per_page
        
        # Boutons de pagination
        if self.total_pages > 1:
            if page > 0:
                self.add_item(TicketMessagesPreviousButton(messages, ticket_data, page))
            
            if page < self.total_pages - 1:
                self.add_item(TicketMessagesNextButton(messages, ticket_data, page))
        
        # Bouton pour revenir aux détails du ticket
        self.add_item(TicketBackToDetailsButton(ticket_data))

class TicketMessagesPreviousButton(discord.ui.Button):
    """Bouton pour aller à la page précédente des messages"""
    
    def __init__(self, messages: list, ticket_data: dict, page: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="◀️ Précédent", emoji="◀️")
        self.messages = messages
        self.ticket_data = ticket_data
        self.page = page
    
    async def callback(self, interaction: discord.Interaction):
        try:
            if self.page > 0:
                new_page = self.page - 1
                view = TicketMessagesView(self.messages, self.ticket_data, new_page)
                embed = await self.create_messages_embed(self.messages, new_page)
                
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message("❌ Vous êtes déjà à la première page.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la navigation vers la page précédente: {e}")
            await interaction.response.send_message("❌ Erreur lors de la navigation.", ephemeral=True)
    
    async def create_messages_embed(self, messages: list, page: int) -> discord.Embed:
        """Crée l'embed avec les messages paginés"""
        ticket_id = self.ticket_data.get('ticket_id', 'Inconnu')
        messages_per_page = 10
        start_idx = page * messages_per_page
        end_idx = start_idx + messages_per_page
        page_messages = messages[start_idx:end_idx]
        
        total_pages = (len(messages) + messages_per_page - 1) // messages_per_page
        
        embed = discord.Embed(
            title=f"💬 Messages du ticket #{ticket_id}",
            description=f"Page {page + 1}/{total_pages} • {len(messages)} messages au total",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Afficher les messages de cette page
        for i, msg in enumerate(page_messages):
            author = msg.get('author_name', 'Inconnu')
            content = msg.get('content', 'Pas de contenu')
            timestamp = msg.get('timestamp', 'Inconnu')
            
            # Formater le timestamp
            try:
                if timestamp != 'Inconnu':
                    dt = datetime.fromisoformat(timestamp)
                    time_str = f"<t:{int(dt.timestamp())}:R>"
                else:
                    time_str = "Inconnu"
            except:
                time_str = timestamp
            
            # Limiter la longueur du contenu
            if len(content) > 300:
                content = content[:300] + "..."
            
            embed.add_field(
                name=f"💬 {author}",
                value=f"{content}\n\n*{time_str}*",
                inline=False
            )
        
        embed.set_footer(text=f"Messages {start_idx + 1}-{min(end_idx, len(messages))} sur {len(messages)}")
        
        return embed

class TicketMessagesNextButton(discord.ui.Button):
    """Bouton pour aller à la page suivante des messages"""
    
    def __init__(self, messages: list, ticket_data: dict, page: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="Suivant ▶️", emoji="▶️")
        self.messages = messages
        self.ticket_data = ticket_data
        self.page = page
    
    async def callback(self, interaction: discord.Interaction):
        try:
            messages_per_page = 10
            total_pages = (len(self.messages) + messages_per_page - 1) // messages_per_page
            
            if self.page < total_pages - 1:
                new_page = self.page + 1
                view = TicketMessagesView(self.messages, self.ticket_data, new_page)
                embed = await self.create_messages_embed(self.messages, new_page)
                
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message("❌ Vous êtes déjà à la dernière page.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la navigation vers la page suivante: {e}")
            await interaction.response.send_message("❌ Erreur lors de la navigation.", ephemeral=True)
    
    async def create_messages_embed(self, messages: list, page: int) -> discord.Embed:
        """Crée l'embed avec les messages paginés"""
        ticket_id = self.ticket_data.get('ticket_id', 'Inconnu')
        messages_per_page = 10
        start_idx = page * messages_per_page
        end_idx = start_idx + messages_per_page
        page_messages = messages[start_idx:end_idx]
        
        total_pages = (len(messages) + messages_per_page - 1) // messages_per_page
        
        embed = discord.Embed(
            title=f"💬 Messages du ticket #{ticket_id}",
            description=f"Page {page + 1}/{total_pages} • {len(messages)} messages au total",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Afficher les messages de cette page
        for i, msg in enumerate(page_messages):
            author = msg.get('author_name', 'Inconnu')
            content = msg.get('content', 'Pas de contenu')
            timestamp = msg.get('timestamp', 'Inconnu')
            
            # Formater le timestamp
            try:
                if timestamp != 'Inconnu':
                    dt = datetime.fromisoformat(timestamp)
                    time_str = f"<t:{int(dt.timestamp())}:R>"
                else:
                    time_str = "Inconnu"
            except:
                time_str = timestamp
            
            # Limiter la longueur du contenu
            if len(content) > 300:
                content = content[:300] + "..."
            
            embed.add_field(
                name=f"💬 {author}",
                value=f"{content}\n\n*{time_str}*",
                inline=False
            )
        
        embed.set_footer(text=f"Messages {start_idx + 1}-{min(end_idx, len(messages))} sur {len(messages)}")
        
        return embed

class TicketBackToDetailsButton(discord.ui.Button):
    """Bouton pour revenir aux détails du ticket"""
    
    def __init__(self, ticket_data: dict):
        super().__init__(style=discord.ButtonStyle.primary, label="🔙 Retour aux détails", emoji="🔙")
        self.ticket_data = ticket_data
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Créer l'embed des détails du ticket
            embed = await self.create_ticket_details_embed(self.ticket_data)
            
            # Créer la vue des détails (sans navigation car on ne connaît pas l'index)
            view = TicketDetailsView(self.ticket_data, [self.ticket_data], 0)
            
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Erreur lors du retour aux détails: {e}")
            await interaction.response.send_message("❌ Erreur lors du retour aux détails.", ephemeral=True)
    
    async def create_ticket_details_embed(self, ticket_data: dict) -> discord.Embed:
        """Crée l'embed avec les détails d'un ticket"""
        ticket_id = ticket_data.get('ticket_id', 'Inconnu')
        created_at = ticket_data.get('created_at', 'Inconnu')
        messages = ticket_data.get('messages', [])
        events = ticket_data.get('events', [])
        
        embed = discord.Embed(
            title=f"📋 Détails du ticket #{ticket_id}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Informations générales
        created_timestamp = "Inconnu"
        if created_at != 'Inconnu':
            try:
                created_timestamp = f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:F>"
            except (ValueError, TypeError):
                created_timestamp = created_at
        
        embed.add_field(
            name="📊 Informations générales",
            value=f"**ID du ticket :** {ticket_id}\n"
                  f"**Créé le :** {created_timestamp}\n"
                  f"**Messages :** {len(messages)}\n"
                  f"**Événements :** {len(events)}",
            inline=False
        )
        
        # Afficher les derniers messages
        if messages:
            recent_messages = messages[-3:]  # 3 derniers messages
            message_text = ""
            for msg in recent_messages:
                author = msg.get('author_name', 'Inconnu')
                content = msg.get('content', 'Pas de contenu')[:100]
                timestamp = msg.get('timestamp', 'Inconnu')
                message_text += f"**{author}** : {content}...\n"
            
            embed.add_field(
                name="💬 Derniers messages",
                value=message_text or "Aucun message",
                inline=False
            )
        
        # Afficher les événements
        if events:
            event_text = ""
            for event in events[-3:]:  # 3 derniers événements
                event_type = event.get('type', 'Inconnu')
                user_name = event.get('user_name', 'Inconnu')
                timestamp = event.get('timestamp', 'Inconnu')
                event_text += f"**{event_type}** par {user_name}\n"
            
            embed.add_field(
                name="📝 Événements récents",
                value=event_text or "Aucun événement",
                inline=False
            )
        
        embed.set_footer(text="Utilisez les boutons pour naviguer")
        
        return embed

class TicketLogsView(discord.ui.View):
    """Vue principale pour les logs de tickets avec pagination"""
    
    def __init__(self, tickets: list, user: discord.Member, page: int = 0):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.tickets = tickets
        self.user = user
        self.page = page
        self.tickets_per_page = 25
        
        # Calculer le nombre total de pages
        self.total_pages = (len(tickets) + self.tickets_per_page - 1) // self.tickets_per_page
        
        # Ajouter le dropdown pour cette page
        if tickets:
            self.add_item(TicketLogsDropdown(tickets, page))
        
        # Boutons de pagination
        if self.total_pages > 1:
            if page > 0:
                self.add_item(TicketPagePreviousButton())
            
            if page < self.total_pages - 1:
                self.add_item(TicketPageNextButton())

class TicketPagePreviousButton(discord.ui.Button):
    """Bouton pour aller à la page précédente"""
    
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="◀️ Page précédente", emoji="◀️")
    
    async def callback(self, interaction: discord.Interaction):
        # Cette logique sera gérée par la vue parent
        await interaction.response.defer()

class TicketPageNextButton(discord.ui.Button):
    """Bouton pour aller à la page suivante"""
    
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Page suivante ▶️", emoji="▶️")
    
    async def callback(self, interaction: discord.Interaction):
        # Cette logique sera gérée par la vue parent
        await interaction.response.defer()

class TicketCloseView(discord.ui.View):

    def __init__(self, panel_data: dict = None):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())
        
        # Ajouter le bouton "Prendre en charge" si c'est un ticket de vérification
        if panel_data and panel_data.get('verification_enabled') in (1, True, '1'):
            self.add_item(ClaimTicketButton())


async def setup(bot):
    ticket_cog = Ticket(bot)
    
    # Initialiser le stockage cloud (optionnel)
    try:
        if await ticket_cog.cloud_storage.initialize():
            logger.info("✅ Stockage cloud Google Drive initialisé avec succès")
            ticket_cog.cloud_enabled = True
        else:
            logger.warning("⚠️ Échec de l'initialisation du stockage cloud - Mode local activé")
            ticket_cog.cloud_enabled = False
    except Exception as e:
        logger.warning(f"⚠️ Stockage cloud désactivé: {e}")
        ticket_cog.cloud_enabled = False
    
    await bot.add_cog(ticket_cog)
