import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from i18n import _


class DMLogsConfigView(discord.ui.View):
    """Vue pour configurer les logs DM"""
    
    def __init__(self, bot, user_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
        self.commands = self._get_available_commands()
    
    async def initialize(self):
        """Initialise la vue de manière asynchrone"""
        await self._create_buttons()
    
    def _get_available_commands(self) -> List[str]:
        """Récupère la liste des commandes disponibles (exclut les commandes privées)"""
        commands = []
        
        # Commandes à exclure pour maintenir la confidentialité
        excluded_commands = {'confession'}
        
        # Récupérer toutes les commandes slash du bot (commandes globales)
        for command in self.bot.tree.get_commands():
            if isinstance(command, app_commands.Command) and command.name not in excluded_commands:
                commands.append(command.name)
        
        # Récupérer aussi les commandes des cogs
        for cog_name, cog in self.bot.cogs.items():
            # Essayer différentes méthodes pour récupérer les commandes
            if hasattr(cog, 'get_app_commands'):
                try:
                    cog_commands = cog.get_app_commands()
                    for command in cog_commands:
                        if isinstance(command, app_commands.Command) and command.name not in excluded_commands:
                            commands.append(command.name)
                except Exception as e:
                    print(f"❌ [DM LOGS] Erreur get_app_commands() pour {cog_name}: {e}")
            
            # Essayer de parcourir les attributs du cog
            for attr_name in dir(cog):
                if attr_name in excluded_commands:
                    continue  # Exclure les commandes privées
                    
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__name__') and hasattr(attr, '__annotations__'):
                    # Vérifier si c'est une commande app_commands
                    if hasattr(attr, '_callback') or (hasattr(attr, '__wrapped__') and 'interaction' in str(attr.__annotations__)):
                        commands.append(attr_name)
        
        # Supprimer les doublons et trier
        unique_commands = sorted(list(set(commands)))
        print(f"🔍 [DM LOGS] {len(unique_commands)} commandes détectées (confession exclue): {unique_commands}")
        return unique_commands
    
    async def _create_buttons(self):
        """Crée les boutons pour chaque commande"""
        # Boutons principaux (ligne 0)
        self.add_item(EnableAllButton(self.bot, self.user_id, self.guild_id))
        self.add_item(DisableAllButton(self.bot, self.user_id, self.guild_id))
        self.add_item(CloseButton())
        
        # S'assurer que toutes les commandes détectées sont dans la base de données
        await self._ensure_commands_in_db()
        
        # Récupérer les états des commandes
        enabled_commands = await self.bot.get_cog('DMLogsSystem')._get_enabled_commands(self.user_id, self.guild_id)
        
        # Boutons pour chaque commande (lignes 1-4, max 5 lignes)
        # Limite à 22 commandes pour laisser de la place aux 3 boutons principaux (25 max total)
        commands_to_show = self.commands[:22]  # 22 commandes max pour éviter la limite de 25 composants
        print(f"🔍 [DM LOGS] Commandes à afficher ({len(commands_to_show)}): {commands_to_show}")
        
        for i, command in enumerate(commands_to_show):
            row = (i // 5) + 1  # 5 boutons par ligne
            if row <= 4:  # Maximum 4 lignes de commandes
                initial_state = command in enabled_commands
                self.add_item(CommandToggleButton(self.bot, self.user_id, self.guild_id, command, row, initial_state))
    
    async def _ensure_commands_in_db(self):
        """S'assure que toutes les commandes détectées sont dans la base de données"""
        try:
            for command_name in self.commands:
                # Vérifier si la commande existe déjà pour cet utilisateur et ce serveur
                existing = await self.bot.db.query(
                    "SELECT id FROM dm_logs_commands WHERE user_id = %s AND command_name = %s AND guild_id = %s",
                    (self.user_id, command_name, self.guild_id),
                    fetchone=True
                )
                
                # Si elle n'existe pas, l'ajouter avec l'état par défaut (désactivée)
                if not existing:
                    await self.bot.db.query(
                        "INSERT INTO dm_logs_commands (user_id, command_name, guild_id, enabled) VALUES (%s, %s, %s, FALSE)",
                        (self.user_id, command_name, self.guild_id)
                    )
                    print(f"🔍 [DM LOGS] Commande '{command_name}' ajoutée à la DB pour l'utilisateur {self.user_id} et le serveur {self.guild_id}")
        except Exception as e:
            print(f"❌ [DM LOGS] Erreur lors de l'ajout des commandes à la DB: {e}")


class EnableAllButton(discord.ui.Button):
    def __init__(self, bot, user_id: int, guild_id: int):
        super().__init__(label="🔔 Activer", style=discord.ButtonStyle.success, row=0)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Vous n'êtes pas autorisé à utiliser ce menu.", ephemeral=True)
            return
        
        # Activer tous les logs DM pour ce serveur
        await self.bot.db.query(
            "INSERT INTO dm_logs_preferences (user_id, guild_id, enabled) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
            (self.user_id, self.guild_id, True, True)
        )
        
        # Activer toutes les commandes pour ce serveur (sauf les commandes privées)
        excluded_commands = {'confession'}
        
        for command in self.bot.cogs:
            cog = self.bot.cogs[command]
            if hasattr(cog, 'get_commands'):
                for cmd in cog.get_commands():
                    if isinstance(cmd, app_commands.Command) and cmd.name not in excluded_commands:
                        await self.bot.db.query(
                            "INSERT INTO dm_logs_commands (user_id, command_name, guild_id, enabled) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
                            (self.user_id, cmd.name, self.guild_id, True, True)
                        )
        
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.send_message(_("commands.dmlogs.all_enabled", self.user_id, guild_id), ephemeral=True)


class DisableAllButton(discord.ui.Button):
    def __init__(self, bot, user_id: int, guild_id: int):
        super().__init__(label="🔕 Désactiver", style=discord.ButtonStyle.danger, row=0)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Vous n'êtes pas autorisé à utiliser ce menu.", ephemeral=True)
            return
        
        # Désactiver tous les logs DM pour ce serveur
        await self.bot.db.query(
            "INSERT INTO dm_logs_preferences (user_id, guild_id, enabled) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
            (self.user_id, self.guild_id, False, False)
        )
        
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.send_message(_("commands.dmlogs.all_disabled", self.user_id, guild_id), ephemeral=True)


class CommandToggleButton(discord.ui.Button):
    def __init__(self, bot, user_id: int, guild_id: int, command_name: str, row: int = 1, initial_state: bool = False):
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
        self.command_name = command_name
        
        # Déterminer le style et le label basé sur l'état initial
        if initial_state:
            label = f"✅ {command_name}"
            style = discord.ButtonStyle.success
        else:
            label = f"❌ {command_name}"
            style = discord.ButtonStyle.danger
        
        super().__init__(label=label, style=style, row=row)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            guild_id = interaction.guild.id if interaction.guild else None
            await interaction.response.send_message(_("commands.dmlogs.unauthorized", self.user_id, guild_id), ephemeral=True)
            return
        
        # Vérifier l'état actuel
        result = await self.bot.db.query(
            "SELECT enabled FROM dm_logs_commands WHERE user_id = %s AND command_name = %s AND guild_id = %s",
            (self.user_id, self.command_name, self.guild_id),
            fetchone=True
        )
        
        current_state = result['enabled'] if result else False
        new_state = not current_state
        
        # Mettre à jour l'état
        await self.bot.db.query(
            "INSERT INTO dm_logs_commands (user_id, command_name, guild_id, enabled) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
            (self.user_id, self.command_name, self.guild_id, new_state, new_state)
        )
        
        # Mettre à jour le bouton
        if new_state:
            self.label = f"✅ {self.command_name}"
            self.style = discord.ButtonStyle.success
        else:
            self.label = f"❌ {self.command_name}"
            self.style = discord.ButtonStyle.danger
        
        # Mettre à jour directement le message original
        await interaction.response.edit_message(view=self.view)


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔒 Fermer", style=discord.ButtonStyle.secondary, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.edit_message(content=_("commands.dmlogs.menu_closed", interaction.user.id, guild_id), view=None)


class DMLogsSystem(commands.Cog):
    """Système de logs DM pour les commandes"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="dmlogs",
        description="Configure les logs DM pour recevoir des notifications privées"
    )
    async def dmlogs(self, interaction: discord.Interaction):
        """Commande principale pour configurer les logs DM"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Vérifier que l'utilisateur est admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Vous devez être administrateur pour utiliser cette commande.", 
                ephemeral=True
            )
            return
        
        # Vérifier si l'utilisateur a déjà des préférences pour ce serveur
        result = await self.bot.db.query(
            "SELECT enabled FROM dm_logs_preferences WHERE user_id = %s AND guild_id = %s",
            (user_id, guild_id),
            fetchone=True
        )
        
        is_enabled = result['enabled'] if result else False
        
        # Créer l'embed avec traductions
        guild_id = interaction.guild.id if interaction.guild else None
        
        embed = discord.Embed(
            title=_("commands.dmlogs.embed_title", user_id, guild_id),
            description=_("commands.dmlogs.embed_description", user_id, guild_id),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name=_("commands.dmlogs.current_status", user_id, guild_id),
            value=_("commands.dmlogs.enabled", user_id, guild_id) if is_enabled else _("commands.dmlogs.disabled", user_id, guild_id),
            inline=False
        )
        
        # Afficher quelques commandes populaires activées
        enabled_commands = await self._get_enabled_commands(user_id, guild_id)
        if enabled_commands:
            commands_text = ", ".join([f"`/{cmd}`" for cmd in enabled_commands[:5]])
            if len(enabled_commands) > 5:
                commands_text += f" et {len(enabled_commands) - 5} autres"
            embed.add_field(
                name="📋 Commandes surveillées",
                value=commands_text,
                inline=False
            )
        
        embed.add_field(
            name=_("commands.dmlogs.how_it_works", user_id, guild_id),
            value=_("commands.dmlogs.how_it_works_text", user_id, guild_id),
            inline=False
        )
        
        embed.set_footer(text=_("commands.dmlogs.footer", user_id, guild_id))
        
        # Créer la vue
        view = DMLogsConfigView(self.bot, user_id, guild_id)
        await view.initialize()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _get_enabled_commands(self, user_id: int, guild_id: int) -> List[str]:
        """Récupère la liste des commandes activées pour un utilisateur sur un serveur spécifique"""
        try:
            # D'abord, vérifier toutes les commandes pour cet utilisateur sur ce serveur
            all_results = await self.bot.db.query(
                "SELECT command_name, enabled FROM dm_logs_commands WHERE user_id = %s AND guild_id = %s",
                (user_id, guild_id),
                fetchall=True
            )
            print(f"🔍 [DM LOGS] Toutes les commandes pour {user_id} sur le serveur {guild_id}: {all_results}")
            
            # Ensuite, récupérer seulement celles qui sont activées
            results = await self.bot.db.query(
                "SELECT command_name FROM dm_logs_commands WHERE user_id = %s AND guild_id = %s AND enabled = TRUE",
                (user_id, guild_id),
                fetchall=True
            )
            print(f"🔍 [DM LOGS] Résultats de la requête activée: {results}")
            
            # Vérifier si results n'est pas None
            if results is None:
                print(f"🔍 [DM LOGS] Aucune commande activée pour {user_id} sur le serveur {guild_id}")
                return []
            
            commands = [result['command_name'] for result in results]
            print(f"🔍 [DM LOGS] Commandes activées pour {user_id} sur le serveur {guild_id}: {commands}")
            return commands
        except Exception as e:
            print(f"❌ [DM LOGS] Erreur lors de la récupération des commandes activées: {e}")
            return []
    
    async def log_command_usage(self, command_name: str, executor: discord.Member, guild: discord.Guild = None, extra_details: dict = None):
        """Log l'utilisation d'une commande pour tous les utilisateurs qui l'ont activée"""
        try:
            print(f"🔍 [DM LOGS] Commande '{command_name}' utilisée par {executor.display_name} ({executor.id})")
            
            # Récupérer tous les utilisateurs qui ont activé cette commande pour ce serveur spécifique
            results = await self.bot.db.query(
                """SELECT DISTINCT dlp.user_id 
                   FROM dm_logs_preferences dlp
                   JOIN dm_logs_commands dlc ON dlp.user_id = dlc.user_id AND dlp.guild_id = dlc.guild_id
                   WHERE dlp.enabled = TRUE 
                   AND dlp.guild_id = %s
                   AND dlc.command_name = %s 
                   AND dlc.enabled = TRUE""",
                (guild.id if guild else None, command_name),
                fetchall=True
            )
            
            # Vérifier si results n'est pas None
            if results is None:
                print(f"🔍 [DM LOGS] Aucun utilisateur ne surveille la commande '{command_name}'")
                return
            
            print(f"🔍 [DM LOGS] {len(results)} utilisateurs surveillent cette commande")
            
            # Debug: lister tous les utilisateurs qui surveillent cette commande
            user_ids = [result['user_id'] for result in results]
            print(f"🔍 [DM LOGS] Utilisateurs surveillant '{command_name}': {user_ids}")
            
            if not results:
                return
            
            # Créer l'embed de log
            embed = discord.Embed(
                title=f"📨 Commande utilisée: `/{command_name}`",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="👤 Utilisateur",
                value=f"{executor.mention} ({executor.display_name})",
                inline=True
            )
            
            if guild:
                embed.add_field(
                    name="🏠 Serveur",
                    value=f"{guild.name}",
                    inline=True
                )
            
            # Ajouter les détails supplémentaires spécifiques à la commande
            if extra_details:
                details_text = ""
                for key, value in extra_details.items():
                    if value and value != "N/A":
                        # Traduire les clés en français pour l'affichage
                        key_translated = {
                            "messages_deleted": "Messages supprimés",
                            "channel": "Canal",
                            "channel_id": "ID Canal",
                            "warned_user": "Utilisateur averti",
                            "reason": "Raison",
                            "timed_out_user": "Utilisateur timeout",
                            "duration_minutes": "Durée (minutes)",
                            "target_user": "Utilisateur ciblé",
                            "decision": "Décision",
                            "message_length": "Longueur du message"
                        }.get(key, key)
                        
                        if isinstance(value, int):
                            details_text += f"**{key_translated}:** {value}\n"
                        else:
                            details_text += f"**{key_translated}:** {value}\n"
                
                if details_text:
                    embed.add_field(name="📋 Détails", value=details_text.strip(), inline=False)
            
            embed.add_field(
                name="🆔 IDs",
                value=f"User: {executor.id}\nGuild: {guild.id if guild else 'DM'}",
                inline=False
            )
            
            embed.set_thumbnail(url=executor.display_avatar.url)
            embed.set_footer(text="Log DM automatique")
            
            # Envoyer à tous les utilisateurs concernés
            for result in results:
                user_id = result['user_id']
                print(f"🔍 [DM LOGS] Tentative d'envoi DM à l'utilisateur {user_id}")
                
                try:
                    user = self.bot.get_user(user_id)
                    if user:
                        print(f"🔍 [DM LOGS] Utilisateur {user_id} trouvé: {user.display_name}")
                        await user.send(embed=embed)
                        print(f"✅ [DM LOGS] DM envoyé avec succès à {user.display_name} ({user_id})")
                        
                        # Enregistrer dans l'historique
                        await self.bot.db.query(
                            "INSERT INTO dm_logs_history (user_id, command_name, executor_id, guild_id) VALUES (%s, %s, %s, %s)",
                            (user_id, command_name, executor.id, guild.id if guild else None)
                        )
                    else:
                        print(f"❌ [DM LOGS] Utilisateur {user_id} introuvable dans le cache du bot")
                        # Essayer de fetch l'utilisateur depuis Discord
                        try:
                            user = await self.bot.fetch_user(user_id)
                            await user.send(embed=embed)
                            print(f"✅ [DM LOGS] DM envoyé avec succès à {user.display_name} ({user_id}) via fetch")
                        except Exception as fetch_e:
                            print(f"❌ [DM LOGS] Impossible de fetch l'utilisateur {user_id}: {fetch_e}")
                        
                except discord.Forbidden:
                    print(f"❌ [DM LOGS] Impossible d'envoyer DM à {user_id}: DMs bloqués")
                except Exception as e:
                    print(f"❌ [DM LOGS] Erreur lors de l'envoi du log DM à {user_id}: {e}")
                    
        except Exception as e:
            print(f"Erreur dans log_command_usage: {e}")


async def setup(bot):
    await bot.add_cog(DMLogsSystem(bot))
