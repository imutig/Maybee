import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
import asyncio
from datetime import datetime, timedelta
from i18n import _
from .command_logger import log_command_usage
from validation import InputValidator
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
                top_role = member.top_role.name if member.top_role.name != "@everyone" else "Aucun rôle"
                description += f" • {top_role}"
            
            options.append(discord.SelectOption(
                label=member.display_name,
                value=str(member.id),
                description=description[:100],  # Limite Discord
                emoji="👤"
            ))
        
        # Ajouter l'option de recherche manuelle
        options.append(discord.SelectOption(
            label="🔍 Recherche manuelle...",
            value="manual_search",
            description="Tapez l'ID ou la mention du membre",
            emoji="🔍"
        ))
        
        # Créer le select menu
        self.member_select = discord.ui.Select(
            placeholder="👥 Sélectionnez un membre...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.on_member_select
        self.add_item(self.member_select)
    
    async def on_member_select(self, interaction: discord.Interaction):
        """Gestionnaire pour la sélection de membre"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Seul l'utilisateur qui a lancé la commande peut interagir.", ephemeral=True)
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
                    f"{ERROR} Membre introuvable sur ce serveur.",
                    ephemeral=True
                )
                return
            
            # Rediriger vers l'action appropriée
            await self.execute_action(interaction, member)
                
        except Exception as e:
            logger.error(f"Error in member selection: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de la sélection du membre.",
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

class MemberSearchModal(discord.ui.Modal, title="Recherche manuelle"):
    """Modal pour rechercher un membre manuellement"""
    
    member_input = discord.ui.TextInput(
        label="ID ou mention du membre",
        placeholder="Ex: @membre ou 123456789012345678",
        required=True,
        max_length=100
    )
    
    def __init__(self, action_type: str, bot, interaction: discord.Interaction):
        super().__init__()
        self.action_type = action_type
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

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
                    f"{ERROR} Format invalide. Utilisez @membre ou l'ID numérique.",
                    ephemeral=True
                )
                return
            
            # Récupérer le membre
            member = interaction.guild.get_member(member_id)
            if not member:
                await interaction.response.send_message(
                    f"{ERROR} Membre introuvable sur ce serveur.",
                    ephemeral=True
                )
                return
            
            # Rediriger vers l'action appropriée
            view = MemberSelectView(self.action_type, self.bot, interaction)
            await view.execute_action(interaction, member)
                
        except Exception as e:
            logger.error(f"Error in member search: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de la recherche du membre.",
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
                title=f"{WARNING} Avertissements de {member.display_name}",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            if not warnings:
                embed.description = f"{member.mention} n'a aucun avertissement."
            else:
                for i, warning in enumerate(warnings, 1):
                    moderator = self.bot.get_user(warning['moderator_id'])
                    moderator_name = moderator.display_name if moderator else "Inconnu"
                    
                    embed.add_field(
                        name=f"Avertissement #{i}",
                        value=f"**Modérateur:** {moderator_name}\n"
                              f"**Raison:** {warning['reason']}\n"
                              f"**Date:** {warning['timestamp'].strftime('%d/%m/%Y %H:%M')}",
                        inline=False
                    )
                
                embed.set_footer(text=f"Total: {len(warnings)} avertissement(s)")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error fetching warnings: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de la récupération des avertissements.",
                ephemeral=True
            )

class TimeoutModal(discord.ui.Modal, title="Mettre en timeout"):
    """Modal pour timeout un membre"""
    
    duration = discord.ui.TextInput(
        label="Durée (en minutes)",
        placeholder="Ex: 60 (maximum 2880 = 48h)",
        required=True,
        max_length=10
    )
    
    reason = discord.ui.TextInput(
        label="Raison",
        placeholder="Raison du timeout",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            duration = int(self.duration.value)
            reason = self.reason.value
            
            # Vérifier la durée
            if duration < 1 or duration > 2880:
                await interaction.response.send_message(
                    f"{ERROR} La durée doit être entre 1 et 2880 minutes (48h).",
                    ephemeral=True
                )
                return
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    f"{ERROR} Vous n'avez pas la permission de modérer les membres.",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut timeout ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} Vous ne pouvez pas timeout un membre avec un rôle égal ou supérieur au vôtre.",
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
                title=f"{WARNING} Membre mis en timeout",
                description=f"{self.member.mention} a été mis en timeout pour {duration} minutes.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.add_field(name="Durée", value=f"{duration} minutes", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(
                f"{ERROR} La durée doit être un nombre valide.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in timeout: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors du timeout: {str(e)}",
                ephemeral=True
            )

class KickModal(discord.ui.Modal, title="Expulser un membre"):
    """Modal pour kick un membre"""
    
    reason = discord.ui.TextInput(
        label="Raison",
        placeholder="Raison de l'expulsion",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason.value
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.kick_members:
                await interaction.response.send_message(
                    f"{ERROR} Vous n'avez pas la permission d'expulser des membres.",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut kick ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} Vous ne pouvez pas expulser un membre avec un rôle égal ou supérieur au vôtre.",
                    ephemeral=True
                )
                return
            
            # Expulser le membre
            await self.member.kick(reason=reason)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} Membre expulsé",
                description=f"{self.member.display_name} a été expulsé du serveur.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in kick: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de l'expulsion: {str(e)}",
                ephemeral=True
            )

class BanModal(discord.ui.Modal, title="Bannir un membre"):
    """Modal pour ban un membre"""
    
    reason = discord.ui.TextInput(
        label="Raison",
        placeholder="Raison du bannissement",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason.value
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    f"{ERROR} Vous n'avez pas la permission de bannir des membres.",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut ban ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} Vous ne pouvez pas bannir un membre avec un rôle égal ou supérieur au vôtre.",
                    ephemeral=True
                )
                return
            
            # Bannir le membre
            await self.member.ban(reason=reason)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} Membre banni",
                description=f"{self.member.display_name} a été banni du serveur.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in ban: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors du bannissement: {str(e)}",
                ephemeral=True
            )

class WarnModal(discord.ui.Modal, title="Avertir un membre"):
    """Modal pour avertir un membre"""
    
    reason = discord.ui.TextInput(
        label="Raison de l'avertissement",
        placeholder="Raison de l'avertissement",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason = self.reason.value
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    f"{ERROR} Vous n'avez pas la permission de modérer les membres.",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut warn ce membre
            if self.member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} Vous ne pouvez pas avertir un membre avec un rôle égal ou supérieur au vôtre.",
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
                title=f"{WARNING} Avertissement donné",
                description=f"{self.member.mention} a reçu un avertissement.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Essayer d'envoyer un DM au membre
            try:
                dm_embed = discord.Embed(
                    title=f"{WARNING} Avertissement reçu",
                    description=f"Vous avez reçu un avertissement sur **{interaction.guild.name}**",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="Raison", value=reason, inline=False)
                await self.member.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # L'utilisateur a les DM désactivés
            
        except Exception as e:
            logger.error(f"Error in warn: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de l'avertissement: {str(e)}",
                ephemeral=True
            )

class RoleAddModal(discord.ui.Modal, title="Ajouter un rôle"):
    """Modal pour ajouter un rôle à un membre"""
    
    role_input = discord.ui.TextInput(
        label="Nom ou ID du rôle",
        placeholder="Ex: @rôle ou 123456789012345678",
        required=True,
        max_length=100
    )
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

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
                    f"{ERROR} Rôle introuvable.",
                    ephemeral=True
                )
                return
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    f"{ERROR} Vous n'avez pas la permission de gérer les rôles.",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut gérer ce rôle
            if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} Vous ne pouvez pas gérer un rôle égal ou supérieur au vôtre.",
                    ephemeral=True
                )
                return
            
            # Ajouter le rôle
            if role in self.member.roles:
                await interaction.response.send_message(
                    f"{WARNING} {self.member.mention} a déjà le rôle {role.mention}.",
                    ephemeral=True
                )
                return
            
            await self.member.add_roles(role)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CHECK} Rôle ajouté",
                description=f"Le rôle {role.mention} a été ajouté à {self.member.mention}.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in role add: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de l'ajout du rôle: {str(e)}",
                ephemeral=True
            )

class RoleRemoveModal(discord.ui.Modal, title="Retirer un rôle"):
    """Modal pour retirer un rôle d'un membre"""
    
    role_input = discord.ui.TextInput(
        label="Nom ou ID du rôle",
        placeholder="Ex: @rôle ou 123456789012345678",
        required=True,
        max_length=100
    )
    
    def __init__(self, member: discord.Member, bot, interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.bot = bot
        self.original_interaction = interaction
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id

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
                    f"{ERROR} Rôle introuvable.",
                    ephemeral=True
                )
                return
            
            # Vérifier les permissions
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    f"{ERROR} Vous n'avez pas la permission de gérer les rôles.",
                    ephemeral=True
                )
                return
            
            # Vérifier si on peut gérer ce rôle
            if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    f"{ERROR} Vous ne pouvez pas gérer un rôle égal ou supérieur au vôtre.",
                    ephemeral=True
                )
                return
            
            # Retirer le rôle
            if role not in self.member.roles:
                await interaction.response.send_message(
                    f"{WARNING} {self.member.mention} n'a pas le rôle {role.mention}.",
                    ephemeral=True
                )
                return
            
            await self.member.remove_roles(role)
            
            # Embed de confirmation
            embed = discord.Embed(
                title=f"{CROSS} Rôle retiré",
                description=f"Le rôle {role.mention} a été retiré de {self.member.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in role remove: {e}")
            await interaction.response.send_message(
                f"{ERROR} Erreur lors de la suppression du rôle: {str(e)}",
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
            await interaction.response.send_message("❌ Seul l'utilisateur qui a lancé la commande peut interagir.", ephemeral=True)
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
            title=f"{SHIELD} Gestion des membres",
            description="Choisissez l'action à effectuer sur un membre",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔨 Actions disponibles",
            value="• **Timeout** - Mettre en sourdine temporairement\n"
                  "• **Kick** - Expulser du serveur\n"
                  "• **Ban** - Bannir du serveur",
            inline=False
        )
        
        view = MemberManagementView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_warnings_system(self, interaction: discord.Interaction):
        """Affiche le système d'avertissements"""
        embed = discord.Embed(
            title=f"{WARNING} Système d'avertissements",
            description="Gérez les avertissements des membres",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 Actions disponibles",
            value="• **Avertir** - Donner un avertissement\n"
                  "• **Voir les avertissements** - Consulter l'historique",
            inline=False
        )
        
        view = WarningsSystemView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_cleanup_options(self, interaction: discord.Interaction):
        """Affiche les options de nettoyage"""
        embed = discord.Embed(
            title=f"{TRASH} Nettoyage des messages",
            description="Supprimez des messages en masse",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🧹 Options de nettoyage",
            value="• **Messages récents** - Supprimer les derniers messages\n"
                  "• **Messages d'un utilisateur** - Supprimer les messages d'un membre\n"
                  "• **Messages de bots** - Supprimer tous les messages de bots",
            inline=False
        )
        
        view = CleanupView(self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_role_management(self, interaction: discord.Interaction):
        """Affiche la gestion des rôles"""
        embed = discord.Embed(
            title=f"🔒 Gestion des rôles",
            description="Ajoutez ou retirez des rôles aux membres",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔧 Actions disponibles",
            value="• **Ajouter un rôle** - Donner un rôle à un membre\n"
                  "• **Retirer un rôle** - Enlever un rôle d'un membre",
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
                title=f"{CHART_BAR} Statistiques de modération",
                description=f"Statistiques du serveur **{interaction.guild.name}**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Avertissements",
                value=f"• Total: {stats['total_warnings']}\n"
                      f"• Ce mois: {stats['warnings_this_month']}\n"
                      f"• Cette semaine: {stats['warnings_this_week']}",
                inline=True
            )
            
            embed.add_field(
                name="🔨 Actions de modération",
                value=f"• Timeouts: {stats['total_timeouts']}\n"
                      f"• Kicks: {stats['total_kicks']}\n"
                      f"• Bans: {stats['total_bans']}",
                inline=True
            )
            
            embed.add_field(
                name="👥 Membres",
                value=f"• Total: {interaction.guild.member_count}\n"
                      f"• En ligne: {len([m for m in interaction.guild.members if m.status != discord.Status.offline])}\n"
                      f"• Bots: {len([m for m in interaction.guild.members if m.bot])}",
                inline=True
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error showing moderation stats: {e}")
            await interaction.response.edit_message(
                content=f"{ERROR} Erreur lors du chargement des statistiques.",
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
            title=f"🔇 Sélectionner un membre à timeout",
            description="Choisissez un membre dans la liste ci-dessous :",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("timeout", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary, emoji="👢")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"👢 Sélectionner un membre à expulser",
            description="Choisissez un membre dans la liste ci-dessous :",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("kick", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"🔨 Sélectionner un membre à bannir",
            description="Choisissez un membre dans la liste ci-dessous :",
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
            title=f"⚠️ Sélectionner un membre à avertir",
            description="Choisissez un membre dans la liste ci-dessous :",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("warn", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Voir les avertissements", style=discord.ButtonStyle.primary, emoji="📋")
    async def view_warnings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"📋 Consulter les avertissements d'un membre",
            description="Choisissez un membre dans la liste ci-dessous :",
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
            f"{INFO} Fonctionnalité de nettoyage en cours de développement. Utilisez `/clear nombre` pour l'instant.",
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
            title=f"➕ Ajouter un rôle à un membre",
            description="Choisissez un membre dans la liste ci-dessous :",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("role_add", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Retirer un rôle", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"➖ Retirer un rôle d'un membre",
            description="Choisissez un membre dans la liste ci-dessous :",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        view = MemberSelectView("role_remove", self.bot, interaction)
        await interaction.response.edit_message(embed=embed, view=view)

class Moderation(commands.Cog):
    """Système de modération complet avec menu interactif"""
    
    def __init__(self, bot):
        self.bot = bot
        self.validator = InputValidator()
        
    @app_commands.command(name="moderation", description="Menu de modération complet")
    @log_command_usage
    async def moderation(self, interaction: discord.Interaction):
        """Commande principale de modération avec menu interactif"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Vérifier les permissions
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                f"{ERROR} Vous n'avez pas la permission de modérer les membres.",
                ephemeral=True
            )
            return
        
        # Créer l'embed principal
        embed = discord.Embed(
            title=f"{SHIELD} Centre de Modération",
            description=f"Bienvenue dans le centre de modération de **{interaction.guild.name}**\n"
                       f"Sélectionnez une catégorie d'action ci-dessous.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔧 Actions disponibles",
            value="• **Gestion des membres** - Timeout, kick, ban\n"
                  "• **Système d'avertissements** - Avertir et consulter\n"
                  "• **Nettoyage** - Supprimer des messages\n"
                  "• **Gestion des rôles** - Ajouter/retirer des rôles\n"
                  "• **Statistiques** - Voir les stats de modération",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value="Ce menu vous donne accès à toutes les fonctionnalités\n"
                  "de modération du bot en un seul endroit.",
            inline=False
        )
        
        embed.set_footer(
            text=f"Modérateur: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        view = ModerationView(self.bot, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))