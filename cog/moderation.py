import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
import asyncio
from datetime import datetime, timedelta
from i18n import _
from .command_logger import log_command_usage
# Validation module removed during cleanup
import logging
from custom_emojis import (
    SHIELD, SUCCESS, ERROR, WARNING, TRASH, CHECK, CROSS, 
    CLOCK, USERS, INFO, CHART_BAR
)

logger = logging.getLogger(__name__)

class MemberSelectView(discord.ui.View):
    """View pour sélectionner un membre avec un menu déroulant"""
    
    def __init__(self, action_type: str, bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.action_type = action_type
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer les options du menu déroulant
        self.create_member_options()
    
    def create_member_options(self):
        """Crée les options du menu déroulant avec les membres"""
        # Récupérer tous les membres du serveur
        members = self.original_interaction.guild.members
        
        # Filtrer les bots et trier par nom
        human_members = [m for m in members if not m.bot]
        human_members.sort(key=lambda x: x.display_name.lower())
        
        # Limiter à 25 membres (limite Discord)
        members_to_show = human_members[:25]
        
        # Créer les options
        options = []
        for member in members_to_show:
            # Créer une description avec le statut
            status_emoji = {
                discord.Status.online: "🟢",
                discord.Status.idle: "🟡", 
                discord.Status.dnd: "🔴",
                discord.Status.offline: "⚫"
            }.get(member.status, "⚫")
            
            description = f"{status_emoji} {member.status.name.title()}"
            if len(member.roles) > 1:  # Plus que @everyone
                top_role = member.top_role.name if member.top_role.name != "@everyone" else _("common.none", self.user_id, self.guild_id)
                description += f" • {top_role}"
            
            options.append(discord.SelectOption(
                label=member.display_name,
                value=str(member.id),
                description=description[:100],  # Limite Discord
                emoji="👤"
            ))
        
        # Ajouter l'option de recherche manuelle
        options.append(discord.SelectOption(
            label=_("moderation.member_select.manual_search", self.user_id, self.guild_id),
            value="manual_search",
            description=_("moderation.member_select.manual_search_desc", self.user_id, self.guild_id),
            emoji="🔍"
        ))
        
        # Créer le select menu
        self.member_select = discord.ui.Select(
            placeholder=_("moderation.member_select.placeholder", self.user_id, self.guild_id),
            options=options,
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.on_member_select
        self.add_item(self.member_select)
    
    async def on_member_select(self, interaction: discord.Interaction):
        """Gestionnaire pour la sélection de membre"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(_("moderation.member_select.unauthorized", self.user_id, self.guild_id), ephemeral=True)
            return
        
        selected_value = self.member_select.values[0]
        
        if selected_value == "manual_search":
            # Afficher un modal pour la recherche manuelle
            modal = MemberSearchModal(self.action_type, self.bot, interaction)
            await interaction.response.send_modal(modal)
            return
        
        try:
            member_id = int(selected_value)
            member = interaction.guild.get_member(member_id)
            
            if not member:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.member_select.member_not_found', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Rediriger vers l'action appropriée
            await self.execute_action(interaction, member)
                
        except Exception as e:
            logger.error(f"Error in member selection: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.member_select.selection_error', self.user_id, self.guild_id)}",
                ephemeral=True
            )
    
    async def execute_action(self, interaction: discord.Interaction, member: discord.Member):
        """Exécute l'action appropriée avec le membre sélectionné"""
        if self.action_type == "timeout":
            await self.show_timeout_modal(interaction, member)
        elif self.action_type == "kick":
            await self.show_kick_modal(interaction, member)
        elif self.action_type == "ban":
            await self.show_ban_modal(interaction, member)
        elif self.action_type == "warn":
            await self.show_warn_modal(interaction, member)
        elif self.action_type == "role_add":
            await self.show_role_add_modal(interaction, member)
        elif self.action_type == "role_remove":
            await self.show_role_remove_modal(interaction, member)
        elif self.action_type == "view_warnings":
            await self.show_member_warnings(interaction, member)
    
    async def show_warn_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal d'avertissement"""
        modal = WarnModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)
    
    async def show_timeout_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal de timeout"""
        modal = TimeoutModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)
    
    async def show_kick_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal de kick"""
        modal = KickModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)
    
    async def show_ban_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal de ban"""
        modal = BanModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

class MemberSearchModal(discord.ui.Modal):
    """Modal pour rechercher un membre manuellement"""
    
    def __init__(self, action_type: str, bot, interaction: discord.Interaction):
        super().__init__()
        self.action_type = action_type
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer le champ de saisie avec traduction
        self.member_input = discord.ui.TextInput(
            label=_("moderation.modals.member_input_label", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.member_input_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=100
        )
        self.add_item(self.member_input)
    
    @property
    def title(self):
        return _("moderation.modals.manual_search_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Extraire l'ID du membre
            member_text = self.member_input.value.strip()
            member_id = None
            
            # Si c'est une mention
            if member_text.startswith('<@') and member_text.endswith('>'):
                member_id = int(member_text[2:-1].replace('!', ''))
            # Si c'est un ID numérique
            elif member_text.isdigit():
                member_id = int(member_text)
            else:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.member_select.invalid_format', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Récupérer le membre
            member = interaction.guild.get_member(member_id)
            if not member:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.member_select.member_not_found', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Rediriger vers l'action appropriée
            view = MemberSelectView(self.action_type, self.bot, interaction)
            await view.execute_action(interaction, member)
                
        except Exception as e:
            logger.error(f"Error in member search: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.member_select.search_error', self.user_id, self.guild_id)}",
                ephemeral=True
            )

    async def show_timeout_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal pour timeout"""
        modal = TimeoutModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

    async def show_kick_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal pour kick"""
        modal = KickModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

    async def show_ban_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal pour ban"""
        modal = BanModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

    async def show_warn_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal pour warn"""
        modal = WarnModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

    async def show_role_add_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal pour ajouter un rôle"""
        modal = RoleAddModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

    async def show_role_remove_modal(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche le modal pour retirer un rôle"""
        modal = RoleRemoveModal(member, self.bot, interaction)
        await interaction.response.send_modal(modal)

    async def show_member_warnings(self, interaction: discord.Interaction, member: discord.Member):
        """Affiche les avertissements d'un membre"""
        try:
            # Récupérer les avertissements depuis la base de données
            warnings = await self.bot.db.query(
                """SELECT moderator_id, reason, timestamp FROM warnings 
                   WHERE guild_id = %s AND user_id = %s 
                   ORDER BY timestamp DESC LIMIT 10""",
                (self.guild_id, member.id),
                fetchall=True
            )
            
            embed = discord.Embed(
                title=f"{WARNING} {_('moderation.warnings.embed_title', self.user_id, self.guild_id, user=member.display_name)}",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            if not warnings:
                embed.description = _('moderation.warnings.no_warnings', self.user_id, self.guild_id, user=member.mention)
            else:
                for i, warning in enumerate(warnings, 1):
                    moderator = self.bot.get_user(warning['moderator_id'])
                    moderator_name = moderator.display_name if moderator else _("common.unknown", self.user_id, self.guild_id)
                    
                    embed.add_field(
                        name=_('moderation.warnings.warning_field', self.user_id, self.guild_id, number=i),
                        value=_('moderation.warnings.warning_value', self.user_id, self.guild_id, 
                               moderator=moderator_name, reason=warning['reason'], 
                               timestamp=warning['timestamp'].strftime('%d/%m/%Y %H:%M')),
                        inline=False
                    )
                
                embed.set_footer(text=f"Total: {len(warnings)} avertissement(s)")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error fetching warnings: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.warnings_fetch_error', self.user_id, self.guild_id)}",
                ephemeral=True
            )

class TimeoutModal(discord.ui.Modal):
    """Modal pour timeout un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer les champs avec traduction
        self.duration = discord.ui.TextInput(
            label=_("moderation.modals.timeout_duration_label", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.timeout_duration_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=10
        )
        self.reason = discord.ui.TextInput(
            label=_("common.reason", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.timeout_reason_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.duration)
        self.add_item(self.reason)
    
    @property
    def title(self):
        return _("moderation.modals.timeout_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            duration = int(self.duration.value)
            reason = self.reason.value
            
            # Vérifier la durée
            if duration < 1 or duration > 2880:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.timeout.invalid_duration', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.permissions.no_moderate_permission', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut timeout ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.timeout.cannot_timeout_higher_role', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Appliquer le timeout
            timeout_until = datetime.utcnow() + timedelta(minutes=duration)
            await self.member.edit(timed_out_until=timeout_until, reason=reason)
            
            # Log en base de données
            await self.bot.db.execute(
                """INSERT INTO timeouts (guild_id, user_id, moderator_id, duration, reason, timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (self.guild_id, self.member.id, self.user_id, duration, reason, datetime.utcnow())
            )
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{WARNING} {_('moderation.timeout.embed_title', self.user_id, self.guild_id)}",
                description=_('moderation.timeout.embed_description', self.user_id, self.guild_id, user=self.member.mention, duration=duration),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name=_("common.reason", self.user_id, self.guild_id), value=reason, inline=False)
            embed.add_field(name=_("moderation.timeout.moderator_field", self.user_id, self.guild_id), value=interaction.user.mention, inline=True)
            embed.add_field(name=_("moderation.timeout.duration_field", self.user_id, self.guild_id), value=_('moderation.timeout.duration_value', self.user_id, self.guild_id, duration=duration), inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.invalid_duration_number', self.user_id, self.guild_id)}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in timeout: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.timeout_error', self.user_id, self.guild_id, error=str(e))}",
                ephemeral=True
            )

class KickModal(discord.ui.Modal):
    """Modal pour kick un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer le champ avec traduction
        self.reason = discord.ui.TextInput(
            label=_("common.reason", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.kick_reason_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)
    
    @property
    def title(self):
        return _("moderation.modals.kick_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason.value
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.kick_members:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.permissions.no_kick_permission', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut kick ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.kick.cannot_kick_higher_role', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Expulser le membre
            await self.member.kick(reason=reason)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} {_('moderation.kick.embed_title', self.user_id, self.guild_id)}",
                description=_('moderation.kick.embed_description', self.user_id, self.guild_id, user=self.member.display_name),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name=_("moderation.kick.reason_field", self.user_id, self.guild_id), value=reason, inline=False)
            embed.add_field(name=_("moderation.kick.moderator_field", self.user_id, self.guild_id), value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in kick: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.kick_error', self.user_id, self.guild_id, error=str(e))}",
                ephemeral=True
            )

class BanModal(discord.ui.Modal):
    """Modal pour ban un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer le champ avec traduction
        self.reason = discord.ui.TextInput(
            label=_("common.reason", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.ban_reason_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)
    
    @property
    def title(self):
        return _("moderation.modals.ban_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason.value
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.permissions.no_ban_permission', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut ban ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.ban.cannot_ban_higher_role', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Bannir le membre
            await self.member.ban(reason=reason)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} {_('moderation.ban.embed_title', self.user_id, self.guild_id)}",
                description=_('moderation.ban.embed_description', self.user_id, self.guild_id, user=self.member.display_name),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name=_("moderation.ban.reason_field", self.user_id, self.guild_id), value=reason, inline=False)
            embed.add_field(name=_("moderation.ban.moderator_field", self.user_id, self.guild_id), value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in ban: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.ban_error', self.user_id, self.guild_id, error=str(e))}",
                ephemeral=True
            )

class WarnModal(discord.ui.Modal):
    """Modal pour avertir un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer le champ avec traduction
        self.reason = discord.ui.TextInput(
            label=_("moderation.modals.warn_reason_label", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.warn_reason_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)
    
    @property
    def title(self):
        return _("moderation.modals.warn_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason.value
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.permissions.no_moderate_permission', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut warn ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.warn.cannot_warn_higher_role', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Enregistrer l'avertissement en base
            await self.bot.db.execute(
                """INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp)
                   VALUES (%s, %s, %s, %s, %s)""",
                (self.guild_id, self.member.id, self.user_id, reason, datetime.utcnow())
            )
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{WARNING} {_('moderation.warn.embed_title', self.user_id, self.guild_id)}",
                description=_('moderation.warn.embed_description', self.user_id, self.guild_id, user=self.member.mention),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name=_("common.reason", self.user_id, self.guild_id), value=reason, inline=False)
            embed.add_field(name=_("moderation.warn.moderator_field", self.user_id, self.guild_id), value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Essayer d'envoyer un DM au membre
            try:
                dm_embed = discord.Embed(
                    title=f"{WARNING} {_('moderation.warn.dm_title', self.user_id, self.guild_id)}",
                    description=_('moderation.warn.dm_description', self.user_id, self.guild_id, server=interaction.guild.name),
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name=_("common.reason", self.user_id, self.guild_id), value=reason, inline=False)
                await self.member.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # L'utilisateur a les DM désactivés
            
        except Exception as e:
            logger.error(f"Error in warn: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.warn_error', self.user_id, self.guild_id, error=str(e))}",
                ephemeral=True
            )

class RoleAddModal(discord.ui.Modal):
    """Modal pour ajouter un rôle à un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer le champ avec traduction
        self.role_input = discord.ui.TextInput(
            label=_("moderation.modals.role_input_label", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.role_input_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=100
        )
        self.add_item(self.role_input)
    
    @property
    def title(self):
        return _("moderation.modals.role_add_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_text = self.role_input.value.strip()
            role = None
            
            # Chercher le rôle par mention ou ID
            if role_text.startswith('<@&') and role_text.endswith('>'):
                role_id = int(role_text[3:-1])
                role = interaction.guild.get_role(role_id)
            elif role_text.isdigit():
                role_id = int(role_text)
                role = interaction.guild.get_role(role_id)
            else:
                # Chercher par nom
                role = discord.utils.get(interaction.guild.roles, name=role_text)
            
            if not role:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.errors.role_not_found', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.permissions.no_manage_roles_permission', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut gérer ce rôle
            if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.role_add.cannot_manage_role', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Ajouter le rôle
            if role in self.member.roles:
                await interaction.response.send_message(
                    f"{WARNING} {_('moderation.role_add.role_already_has', self.user_id, self.guild_id, user=self.member.mention, role=role.mention)}",
                    ephemeral=True
                )
                return
            
            await self.member.add_roles(role)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CHECK} {_('moderation.role_add.embed_title', self.user_id, self.guild_id)}",
                description=_('moderation.role_add.embed_description', self.user_id, self.guild_id, role=role.mention, user=self.member.mention),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name=_("moderation.role_add.moderator_field", self.user_id, self.guild_id), value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in role add: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.role_add_error', self.user_id, self.guild_id, error=str(e))}",
                ephemeral=True
            )

class RoleRemoveModal(discord.ui.Modal):
    """Modal pour retirer un rôle d'un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        # Créer le champ avec traduction
        self.role_input = discord.ui.TextInput(
            label=_("moderation.modals.role_input_label", self.user_id, self.guild_id),
            placeholder=_("moderation.modals.role_input_placeholder", self.user_id, self.guild_id),
            required=True,
            max_length=100
        )
        self.add_item(self.role_input)
    
    @property
    def title(self):
        return _("moderation.modals.role_remove_title", self.user_id, self.guild_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_text = self.role_input.value.strip()
            role = None
            
            # Chercher le rôle par mention ou ID
            if role_text.startswith('<@&') and role_text.endswith('>'):
                role_id = int(role_text[3:-1])
                role = interaction.guild.get_role(role_id)
            elif role_text.isdigit():
                role_id = int(role_text)
                role = interaction.guild.get_role(role_id)
            else:
                # Chercher par nom
                role = discord.utils.get(interaction.guild.roles, name=role_text)
            
            if not role:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.errors.role_not_found', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.permissions.no_manage_roles_permission', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut gérer ce rôle
            if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.role_remove.cannot_manage_role', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Retirer le rôle
            if role not in self.member.roles:
                await interaction.response.send_message(
                    f"{WARNING} {_('moderation.role_remove.role_doesnt_have', self.user_id, self.guild_id, user=self.member.mention, role=role.mention)}",
                    ephemeral=True
                )
                return
            
            await self.member.remove_roles(role)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} {_('moderation.role_remove.embed_title', self.user_id, self.guild_id)}",
                description=_('moderation.role_remove.embed_description', self.user_id, self.guild_id, role=role.mention, user=self.member.mention),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name=_("moderation.role_remove.moderator_field", self.user_id, self.guild_id), value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in role remove: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.role_remove_error', self.user_id, self.guild_id, error=str(e))}",
                ephemeral=True
            )

class ModerationView(discord.ui.View):
    """View principale pour le menu de modération"""
    
    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
    @discord.ui.select(
        placeholder="🔧 Choisir une action de modération",
        options=[
            discord.SelectOption(
                label="👥 Gestion des membres",
                description="Timeout, kick, ban des membres",
                value="member_management",
                emoji="👥"
            ),
            discord.SelectOption(
                label="⚠️ Système d'avertissements",
                description="Avertir et consulter les avertissements",
                value="warnings_system",
                emoji="⚠️"
            ),
            discord.SelectOption(
                label="🧹 Nettoyage",
                description="Supprimer des messages en masse",
                value="cleanup",
                emoji="🧹"
            ),
            discord.SelectOption(
                label="🔒 Gestion des rôles",
                description="Ajouter/retirer des rôles",
                value="role_management",
                emoji="🔒"
            ),
            discord.SelectOption(
                label="📊 Statistiques de modération",
                description="Voir les statistiques du serveur",
                value="moderation_stats",
                emoji="📊"
            )
        ]
    )
    async def moderation_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Gestionnaire pour la sélection d'action de modération"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(_("moderation.member_select.unauthorized", self.user_id, self.guild_id), ephemeral=True)
            return
            
        value = select.values[0]
        
        if value == "member_management":
            await self.show_member_management(interaction)
        elif value == "warnings_system":
            await self.show_warnings_system(interaction)
        elif value == "cleanup":
            await self.show_cleanup_options(interaction)
        elif value == "role_management":
            await self.show_role_management(interaction)
        elif value == "moderation_stats":
            await self.show_moderation_stats(interaction)
    
    async def show_member_management(self, interaction: discord.Interaction):
        """Affiche le menu de gestion des membres"""
        embed = discord.Embed(
            title=f"{SHIELD} {_('moderation.member_management.title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.description', self.user_id, self.guild_id),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔨 Actions disponibles",
            value=_('moderation.member_management.available_actions_list', self.user_id, self.guild_id),
            inline=False
        )
        
        view = MemberManagementView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_warnings_system(self, interaction: discord.Interaction):
        """Affiche le système d'avertissements"""
        embed = discord.Embed(
            title=f"{WARNING} {_('moderation.warnings_system.title', self.user_id, self.guild_id)}",
            description=_('moderation.warnings_system.description', self.user_id, self.guild_id),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 Actions disponibles",
            value=_('moderation.warnings_system.available_actions_list', self.user_id, self.guild_id),
            inline=False
        )
        
        view = WarningsSystemView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_cleanup_options(self, interaction: discord.Interaction):
        """Affiche les options de nettoyage"""
        embed = discord.Embed(
            title=f"{TRASH} {_('moderation.cleanup.title', self.user_id, self.guild_id)}",
            description=_('moderation.cleanup.description', self.user_id, self.guild_id),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🧹 Options de nettoyage",
            value=_('moderation.cleanup.options_list', self.user_id, self.guild_id),
            inline=False
        )
        
        view = CleanupView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_role_management(self, interaction: discord.Interaction):
        """Affiche la gestion des rôles"""
        embed = discord.Embed(
            title=f"🔒 {_('moderation.role_management.title', self.user_id, self.guild_id)}",
            description=_('moderation.role_management.description', self.user_id, self.guild_id),
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔧 Actions disponibles",
            value=_('moderation.role_management.available_actions_list', self.user_id, self.guild_id),
            inline=False
        )
        
        view = RoleManagementView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_moderation_stats(self, interaction: discord.Interaction):
        """Affiche les statistiques de modération"""
        try:
            # Récupérer les statistiques depuis la base de données
            stats = await self.get_moderation_stats()
            
            embed = discord.Embed(
                title=f"{CHART_BAR} {_('moderation.stats.title', self.user_id, self.guild_id)}",
                description=_('moderation.stats.description', self.user_id, self.guild_id, guild_name=interaction.guild.name),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('moderation.stats.warnings_title', self.user_id, self.guild_id),
                value=_('moderation.stats.warnings_stats', self.user_id, self.guild_id, 
                       total_warnings=stats['total_warnings'], warnings_this_month=stats['warnings_this_month'], 
                       warnings_this_week=stats['warnings_this_week']),
                inline=True
            )
            
            embed.add_field(
                name=_('moderation.stats.moderation_actions_title', self.user_id, self.guild_id),
                value=_('moderation.stats.moderation_actions_stats', self.user_id, self.guild_id,
                       total_timeouts=stats['total_timeouts'], total_kicks=stats['total_kicks'], 
                       total_bans=stats['total_bans']),
                inline=True
            )
            
            embed.add_field(
                name=_('moderation.stats.members_title', self.user_id, self.guild_id),
                value=_('moderation.stats.members_stats', self.user_id, self.guild_id,
                       total_members=interaction.guild.member_count, 
                       online_members=len([m for m in interaction.guild.members if m.status != discord.Status.offline]),
                       bot_count=len([m for m in interaction.guild.members if m.bot])),
                inline=True
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error showing moderation stats: {e}")
            await interaction.response.edit_message(
                content=f"{ERROR} {_('moderation.stats.stats_error', self.user_id, self.guild_id)}",
                embed=None, view=None
            )
    
    async def get_moderation_stats(self):
        """Récupère les statistiques de modération depuis la base de données"""
        try:
            # Statistiques des avertissements
            warnings_stats = await self.bot.db.query(
                """SELECT 
                    COUNT(*) as total_warnings,
                    COUNT(CASE WHEN timestamp >= DATE_SUB(NOW(), INTERVAL 1 MONTH) THEN 1 END) as warnings_this_month,
                    COUNT(CASE WHEN timestamp >= DATE_SUB(NOW(), INTERVAL 1 WEEK) THEN 1 END) as warnings_this_week
                   FROM warnings WHERE guild_id = %s""",
                (self.guild_id,),
                fetchone=True
            )
            
            # Statistiques des timeouts
            timeouts_stats = await self.bot.db.query(
                "SELECT COUNT(*) as total_timeouts FROM timeouts WHERE guild_id = %s",
                (self.guild_id,),
                fetchone=True
            )
            
            return {
                'total_warnings': warnings_stats['total_warnings'] if warnings_stats else 0,
                'warnings_this_month': warnings_stats['warnings_this_month'] if warnings_stats else 0,
                'warnings_this_week': warnings_stats['warnings_this_week'] if warnings_stats else 0,
                'total_timeouts': timeouts_stats['total_timeouts'] if timeouts_stats else 0,
                'total_kicks': 0,  # À implémenter si nécessaire
                'total_bans': 0    # À implémenter si nécessaire
            }
            
        except Exception as e:
            logger.error(f"Error getting moderation stats: {e}")
            return {
                'total_warnings': 0,
                'warnings_this_month': 0,
                'warnings_this_week': 0,
                'total_timeouts': 0,
                'total_kicks': 0,
                'total_bans': 0
            }

class MemberManagementView(discord.ui.View):
    """View pour la gestion des membres"""
    
    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
    
    @discord.ui.button(label="Timeout", style=discord.ButtonStyle.primary, emoji="🔇")
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"🔇 {_('moderation.member_management.timeout_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("timeout", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary, emoji="👢")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"👢 {_('moderation.member_management.kick_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("kick", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"🔨 {_('moderation.member_management.ban_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("ban", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)

class WarningsSystemView(discord.ui.View):
    """View pour le système d'avertissements"""
    
    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
    
    @discord.ui.button(label="Avertir", style=discord.ButtonStyle.secondary, emoji="⚠️")
    async def warn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"⚠️ {_('moderation.warnings_system.warn_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("warn", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Voir les avertissements", style=discord.ButtonStyle.primary, emoji="📋")
    async def view_warnings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"📋 {_('moderation.warnings_system.view_warnings_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("view_warnings", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)

class CleanupView(discord.ui.View):
    """View pour le nettoyage"""
    
    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
    
    @discord.ui.button(label="Nettoyer les messages", style=discord.ButtonStyle.danger, emoji="🧹")
    async def cleanup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"{INFO} {_('moderation.cleanup.development_message', self.user_id, self.guild_id)}",
            ephemeral=True
        )

class RoleManagementView(discord.ui.View):
    """View pour la gestion des rôles"""
    
    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
    
    @discord.ui.button(label="Ajouter un rôle", style=discord.ButtonStyle.success, emoji="➕")
    async def add_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"➕ {_('moderation.role_management.add_role_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("role_add", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Retirer un rôle", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"➖ {_('moderation.role_management.remove_role_title', self.user_id, self.guild_id)}",
            description=_('moderation.member_management.select_member_description', self.user_id, self.guild_id),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("role_remove", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)

class WarnModal(discord.ui.Modal):
    """Modal pour avertir un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__(title=_('moderation.modals.warn.title', interaction.user.id, interaction.guild.id))
        self.member = member
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        self.reason = discord.ui.TextInput(
            label=_('moderation.modals.warn.reason_label', self.user_id, self.guild_id),
            placeholder=_('moderation.modals.warn.reason_placeholder', self.user_id, self.guild_id),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Gestionnaire de soumission du modal"""
        try:
            # Enregistrer l'action dans la base de données
            moderation_cog = self.bot.get_cog('Moderation')
            await moderation_cog.log_moderation_action(
                guild_id=self.guild_id,
                user_id=self.member.id,
                moderator_id=self.user_id,
                action_type='warn',
                reason=self.reason.value,
                channel_id=interaction.channel.id,
                message_id=interaction.message.id if interaction.message else None
            )
            
            # Créer l'embed de confirmation
            embed = discord.Embed(
                title=f"{WARNING} {_('moderation.actions.warn_success', self.user_id, self.guild_id)}",
                description=_('moderation.actions.warn_success_description', self.user_id, self.guild_id, 
                            user=self.member.display_name, reason=self.reason.value),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('moderation.actions.user', self.user_id, self.guild_id),
                value=f"{self.member.mention} ({self.member.display_name})",
                inline=True
            )
            
            embed.add_field(
                name=_('moderation.actions.moderator', self.user_id, self.guild_id),
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=True
            )
            
            embed.set_footer(
                text=_('moderation.actions.footer', self.user_id, self.guild_id),
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in WarnModal: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.action_failed', self.user_id, self.guild_id)}",
                ephemeral=True
            )

class TimeoutModal(discord.ui.Modal):
    """Modal pour timeout un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__(title=_('moderation.modals.timeout.title', interaction.user.id, interaction.guild.id))
        self.member = member
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        self.duration = discord.ui.TextInput(
            label=_('moderation.modals.timeout.duration_label', self.user_id, self.guild_id),
            placeholder=_('moderation.modals.timeout.duration_placeholder', self.user_id, self.guild_id),
            style=discord.TextStyle.short,
            required=True,
            max_length=10
        )
        self.add_item(self.duration)
        
        self.reason = discord.ui.TextInput(
            label=_('moderation.modals.timeout.reason_label', self.user_id, self.guild_id),
            placeholder=_('moderation.modals.timeout.reason_placeholder', self.user_id, self.guild_id),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Gestionnaire de soumission du modal"""
        try:
            # Parser la durée
            duration_text = self.duration.value.lower()
            duration_minutes = 0
            
            if 'h' in duration_text:
                hours = int(''.join(filter(str.isdigit, duration_text.split('h')[0])))
                duration_minutes += hours * 60
            if 'm' in duration_text:
                minutes = int(''.join(filter(str.isdigit, duration_text.split('m')[0])))
                duration_minutes += minutes
            elif duration_text.isdigit():
                duration_minutes = int(duration_text)
            
            if duration_minutes <= 0 or duration_minutes > 10080:  # Max 7 jours
                await interaction.response.send_message(
                    f"{ERROR} {_('moderation.errors.invalid_duration', self.user_id, self.guild_id)}",
                    ephemeral=True
                )
                return
            
            # Appliquer le timeout
            timeout_until = datetime.now() + timedelta(minutes=duration_minutes)
            await self.member.timeout(timeout_until, reason=self.reason.value)
            
            # Enregistrer l'action dans la base de données
            moderation_cog = self.bot.get_cog('Moderation')
            await moderation_cog.log_moderation_action(
                guild_id=self.guild_id,
                user_id=self.member.id,
                moderator_id=self.user_id,
                action_type='timeout',
                reason=self.reason.value,
                duration_minutes=duration_minutes,
                channel_id=interaction.channel.id,
                message_id=interaction.message.id if interaction.message else None
            )
            
            # Créer l'embed de confirmation
            embed = discord.Embed(
                title=f"{CLOCK} {_('moderation.actions.timeout_success', self.user_id, self.guild_id)}",
                description=_('moderation.actions.timeout_success_description', self.user_id, self.guild_id, 
                            user=self.member.display_name, duration=duration_minutes, reason=self.reason.value),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('moderation.actions.user', self.user_id, self.guild_id),
                value=f"{self.member.mention} ({self.member.display_name})",
                inline=True
            )
            
            embed.add_field(
                name=_('moderation.actions.duration', self.user_id, self.guild_id),
                value=f"{duration_minutes} minutes",
                inline=True
            )
            
            embed.add_field(
                name=_('moderation.actions.moderator', self.user_id, self.guild_id),
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=True
            )
            
            embed.set_footer(
                text=_('moderation.actions.footer', self.user_id, self.guild_id),
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in TimeoutModal: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.action_failed', self.user_id, self.guild_id)}",
                ephemeral=True
            )

class KickModal(discord.ui.Modal):
    """Modal pour kick un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__(title=_('moderation.modals.kick.title', interaction.user.id, interaction.guild.id))
        self.member = member
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        self.reason = discord.ui.TextInput(
            label=_('moderation.modals.kick.reason_label', self.user_id, self.guild_id),
            placeholder=_('moderation.modals.kick.reason_placeholder', self.user_id, self.guild_id),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Gestionnaire de soumission du modal"""
        try:
            # Kick le membre
            await self.member.kick(reason=self.reason.value)
            
            # Enregistrer l'action dans la base de données
            moderation_cog = self.bot.get_cog('Moderation')
            await moderation_cog.log_moderation_action(
                guild_id=self.guild_id,
                user_id=self.member.id,
                moderator_id=self.user_id,
                action_type='kick',
                reason=self.reason.value,
                channel_id=interaction.channel.id,
                message_id=interaction.message.id if interaction.message else None
            )
            
            # Créer l'embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} {_('moderation.actions.kick_success', self.user_id, self.guild_id)}",
                description=_('moderation.actions.kick_success_description', self.user_id, self.guild_id, 
                            user=self.member.display_name, reason=self.reason.value),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('moderation.actions.user', self.user_id, self.guild_id),
                value=f"{self.member.display_name} (ID: {self.member.id})",
                inline=True
            )
            
            embed.add_field(
                name=_('moderation.actions.moderator', self.user_id, self.guild_id),
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=True
            )
            
            embed.set_footer(
                text=_('moderation.actions.footer', self.user_id, self.guild_id),
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in KickModal: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.action_failed', self.user_id, self.guild_id)}",
                ephemeral=True
            )

class BanModal(discord.ui.Modal):
    """Modal pour ban un membre"""
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__(title=_('moderation.modals.ban.title', interaction.user.id, interaction.guild.id))
        self.member = member
        self.bot = bot
        self.interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id
        
        self.duration = discord.ui.TextInput(
            label=_('moderation.modals.ban.duration_label', self.user_id, self.guild_id),
            placeholder=_('moderation.modals.ban.duration_placeholder', self.user_id, self.guild_id),
            style=discord.TextStyle.short,
            required=False,
            max_length=10
        )
        self.add_item(self.duration)
        
        self.reason = discord.ui.TextInput(
            label=_('moderation.modals.ban.reason_label', self.user_id, self.guild_id),
            placeholder=_('moderation.modals.ban.reason_placeholder', self.user_id, self.guild_id),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Gestionnaire de soumission du modal"""
        try:
            # Parser la durée si fournie
            duration_minutes = None
            if self.duration.value:
                duration_text = self.duration.value.lower()
                duration_minutes = 0
                
                if 'd' in duration_text:
                    days = int(''.join(filter(str.isdigit, duration_text.split('d')[0])))
                    duration_minutes += days * 24 * 60
                elif 'h' in duration_text:
                    hours = int(''.join(filter(str.isdigit, duration_text.split('h')[0])))
                    duration_minutes += hours * 60
                elif 'm' in duration_text:
                    minutes = int(''.join(filter(str.isdigit, duration_text.split('m')[0])))
                    duration_minutes += minutes
                elif duration_text.isdigit():
                    duration_minutes = int(duration_text)
                
                if duration_minutes <= 0:
                    duration_minutes = None
            
            # Ban le membre
            await self.member.ban(reason=self.reason.value, delete_message_days=0)
            
            # Enregistrer l'action dans la base de données
            moderation_cog = self.bot.get_cog('Moderation')
            await moderation_cog.log_moderation_action(
                guild_id=self.guild_id,
                user_id=self.member.id,
                moderator_id=self.user_id,
                action_type='ban',
                reason=self.reason.value,
                duration_minutes=duration_minutes,
                channel_id=interaction.channel.id,
                message_id=interaction.message.id if interaction.message else None
            )
            
            # Créer l'embed de confirmation
            embed = discord.Embed(
                title=f"{TRASH} {_('moderation.actions.ban_success', self.user_id, self.guild_id)}",
                description=_('moderation.actions.ban_success_description', self.user_id, self.guild_id, 
                            user=self.member.display_name, reason=self.reason.value),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=_('moderation.actions.user', self.user_id, self.guild_id),
                value=f"{self.member.display_name} (ID: {self.member.id})",
                inline=True
            )
            
            if duration_minutes:
                embed.add_field(
                    name=_('moderation.actions.duration', self.user_id, self.guild_id),
                    value=f"{duration_minutes} minutes",
                    inline=True
                )
            
            embed.add_field(
                name=_('moderation.actions.moderator', self.user_id, self.guild_id),
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=True
            )
            
            embed.set_footer(
                text=_('moderation.actions.footer', self.user_id, self.guild_id),
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in BanModal: {e}")
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.errors.action_failed', self.user_id, self.guild_id)}",
                ephemeral=True
            )

class Moderation(commands.Cog):
    """Système de modération complet avec menu interactif"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def log_moderation_action(self, guild_id: int, user_id: int, moderator_id: int, 
                                   action_type: str, reason: str = None, duration_minutes: int = None,
                                   channel_id: int = None, message_id: int = None, 
                                   evidence_urls: list = None):
        """Enregistre une action de modération dans la base de données"""
        try:
            from db import get_database
            db = await get_database()
            
            # Convertir evidence_urls en JSON si fourni
            evidence_json = None
            if evidence_urls:
                import json
                evidence_json = json.dumps(evidence_urls)
            
            # Calculer expires_at pour les actions temporaires
            expires_at = None
            if action_type in ['timeout', 'ban'] and duration_minutes:
                from datetime import datetime, timedelta
                expires_at = datetime.now() + timedelta(minutes=duration_minutes)
            
            query = """
                INSERT INTO moderation_history 
                (guild_id, user_id, moderator_id, action_type, reason, duration_minutes, 
                 evidence_urls, channel_id, message_id, expires_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await db.execute(query, (
                guild_id, user_id, moderator_id, action_type, reason, duration_minutes,
                evidence_json, channel_id, message_id, expires_at, True
            ))
            
            logger.info(f"Moderation action logged: {action_type} by {moderator_id} on {user_id} in {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to log moderation action: {e}")
    
    async def get_moderation_history(self, guild_id: int, user_id: int = None, 
                                   action_type: str = None, limit: int = 50, offset: int = 0):
        """Récupère l'historique de modération avec filtres optionnels"""
        try:
            from db import get_database
            db = await get_database()
            
            # Construire la requête avec filtres
            where_conditions = ["guild_id = %s"]
            params = [guild_id]
            
            if user_id:
                where_conditions.append("user_id = %s")
                params.append(user_id)
            
            if action_type:
                where_conditions.append("action_type = %s")
                params.append(action_type)
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
                SELECT mh.*, 
                       u.username as user_name, u.discriminator as user_discriminator,
                       m.username as moderator_name, m.discriminator as moderator_discriminator
                FROM moderation_history mh
                LEFT JOIN user_cache u ON mh.user_id = u.user_id
                LEFT JOIN user_cache m ON mh.moderator_id = m.user_id
                WHERE {where_clause}
                ORDER BY mh.timestamp DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            
            results = await db.fetch(query, params)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get moderation history: {e}")
            return []
    
    async def get_moderation_stats(self, guild_id: int):
        """Récupère les statistiques de modération pour un serveur"""
        try:
            from db import get_database
            db = await get_database()
            
            # Statistiques générales
            stats_query = """
                SELECT 
                    action_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT moderator_id) as unique_moderators
                FROM moderation_history 
                WHERE guild_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY action_type
            """
            stats = await db.fetch(stats_query, (guild_id,))
            
            # Top modérateurs
            moderators_query = """
                SELECT 
                    moderator_id,
                    COUNT(*) as action_count,
                    m.username as moderator_name,
                    m.discriminator as moderator_discriminator
                FROM moderation_history mh
                LEFT JOIN user_cache m ON mh.moderator_id = m.user_id
                WHERE guild_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY moderator_id
                ORDER BY action_count DESC
                LIMIT 10
            """
            moderators = await db.fetch(moderators_query, (guild_id,))
            
            return {
                'stats': stats,
                'top_moderators': moderators
            }
            
        except Exception as e:
            logger.error(f"Failed to get moderation stats: {e}")
            return {'stats': [], 'top_moderators': []}
        
    @app_commands.command(name="moderation", description="Menu de modération complet")
    @log_command_usage
    async def moderation(self, interaction: discord.Interaction):
        """Commande principale de modération avec menu interactif"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.permissions.no_moderate_permission', user_id, guild_id)}",
                ephemeral=True
            )
            return
        
        # Créer l'embed principal
        embed = discord.Embed(
            title=f"{SHIELD} {_('moderation.main_menu.title', user_id, guild_id)}",
            description=_('moderation.main_menu.description', user_id, guild_id, guild_name=interaction.guild.name),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔧 Actions disponibles",
            value=_('moderation.main_menu.available_actions_list', user_id, guild_id),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value=_('moderation.main_menu.info', user_id, guild_id),
            inline=False
        )
        
        embed.set_footer(
            text=_('moderation.main_menu.footer', user_id, guild_id, moderator=interaction.user.display_name),
            icon_url=interaction.user.display_avatar.url
        )
        
        view = ModerationView(self.bot, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="moderation_history", description="Affiche l'historique des actions de modération")
    @app_commands.describe(
        user="Utilisateur à filtrer (optionnel)",
        action="Type d'action à filtrer (optionnel)",
        limit="Nombre d'entrées à afficher (défaut: 10, max: 50)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Warn", value="warn"),
        app_commands.Choice(name="Timeout", value="timeout"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Ban", value="ban"),
        app_commands.Choice(name="Unban", value="unban"),
        app_commands.Choice(name="Unmute", value="unmute")
    ])
    @log_command_usage
    async def moderation_history(self, interaction: discord.Interaction, 
                               user: discord.Member = None, 
                               action: str = None, 
                               limit: int = 10):
        """Affiche l'historique des actions de modération avec filtres"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                f"{ERROR} {_('moderation.permissions.no_moderate_permission', user_id, guild_id)}",
                ephemeral=True
            )
            return
        
        # Limiter le nombre d'entrées
        limit = min(max(limit, 1), 50)
        
        # Récupérer l'historique
        history = await self.get_moderation_history(
            guild_id=guild_id,
            user_id=user.id if user else None,
            action_type=action,
            limit=limit
        )
        
        if not history:
            embed = discord.Embed(
                title=f"{INFO} {_('moderation.history.no_history', user_id, guild_id)}",
                description=_('moderation.history.no_history_description', user_id, guild_id),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Créer l'embed avec l'historique
        embed = discord.Embed(
            title=f"{CHART_BAR} {_('moderation.history.title', user_id, guild_id)}",
            description=_('moderation.history.description', user_id, guild_id, count=len(history)),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Ajouter les filtres appliqués
        filters = []
        if user:
            filters.append(f"**{_('moderation.history.filter_user', user_id, guild_id)}:** {user.display_name}")
        if action:
            action_names = {
                'warn': _('moderation.actions.warn', user_id, guild_id),
                'timeout': _('moderation.actions.timeout', user_id, guild_id),
                'kick': _('moderation.actions.kick', user_id, guild_id),
                'ban': _('moderation.actions.ban', user_id, guild_id),
                'unban': _('moderation.actions.unban', user_id, guild_id),
                'unmute': _('moderation.actions.unmute', user_id, guild_id)
            }
            filters.append(f"**{_('moderation.history.filter_action', user_id, guild_id)}:** {action_names.get(action, action)}")
        
        if filters:
            embed.add_field(
                name=_('moderation.history.filters_applied', user_id, guild_id),
                value="\n".join(filters),
                inline=False
            )
        
        # Ajouter les entrées d'historique
        for i, entry in enumerate(history[:10]):  # Limiter à 10 pour éviter la limite Discord
            # Formater les noms d'utilisateur
            user_name = f"{entry['user_name']}#{entry['user_discriminator']}" if entry['user_name'] else f"<@{entry['user_id']}>"
            moderator_name = f"{entry['moderator_name']}#{entry['moderator_discriminator']}" if entry['moderator_name'] else f"<@{entry['moderator_id']}>"
            
            # Emoji pour le type d'action
            action_emojis = {
                'warn': WARNING,
                'timeout': CLOCK,
                'kick': CROSS,
                'ban': TRASH,
                'unban': CHECK,
                'unmute': CHECK
            }
            
            action_emoji = action_emojis.get(entry['action_type'], '❓')
            
            # Formater la durée si applicable
            duration_text = ""
            if entry['duration_minutes']:
                hours = entry['duration_minutes'] // 60
                minutes = entry['duration_minutes'] % 60
                if hours > 0:
                    duration_text = f" ({hours}h{minutes}m)"
                else:
                    duration_text = f" ({minutes}m)"
            
            # Formater la date
            timestamp = entry['timestamp']
            date_str = timestamp.strftime("%d/%m/%Y %H:%M")
            
            value = f"**{action_emoji} {entry['action_type'].upper()}{duration_text}**\n"
            value += f"👤 **{_('moderation.history.user', user_id, guild_id)}:** {user_name}\n"
            value += f"🛡️ **{_('moderation.history.moderator', user_id, guild_id)}:** {moderator_name}\n"
            value += f"📅 **{_('moderation.history.date', user_id, guild_id)}:** {date_str}\n"
            if entry['reason']:
                value += f"📝 **{_('moderation.history.reason', user_id, guild_id)}:** {entry['reason'][:100]}{'...' if len(entry['reason']) > 100 else ''}"
            
            embed.add_field(
                name=f"{i+1}. {entry['action_type'].upper()}",
                value=value,
                inline=False
            )
        
        # Ajouter les statistiques si pas de filtres spécifiques
        if not user and not action:
            stats = await self.get_moderation_stats(guild_id)
            if stats['stats']:
                stats_text = ""
                for stat in stats['stats'][:5]:  # Top 5 actions
                    stats_text += f"**{stat['action_type'].upper()}:** {stat['count']}\n"
                
                embed.add_field(
                    name=_('moderation.history.stats_30_days', user_id, guild_id),
                    value=stats_text,
                    inline=True
                )
        
        embed.set_footer(text=_('moderation.history.footer', user_id, guild_id, limit=limit))
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))