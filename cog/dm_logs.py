import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
from i18n import _


class DMLogsConfigView(discord.ui.View):
    """Vue pour configurer les logs DM"""
    
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.commands = self._get_available_commands()
        self._create_buttons()
    
    def _get_available_commands(self) -> List[str]:
        """Récupère la liste des commandes disponibles"""
        commands = []
        # Récupérer toutes les commandes slash du bot
        for command in self.bot.tree.get_commands():
            if isinstance(command, app_commands.Command):
                commands.append(command.name)
        return sorted(commands)
    
    def _create_buttons(self):
        """Crée les boutons pour chaque commande"""
        # Boutons principaux (ligne 0)
        self.add_item(EnableAllButton(self.bot, self.user_id))
        self.add_item(DisableAllButton(self.bot, self.user_id))
        self.add_item(CloseButton())
        
        # Boutons pour chaque commande (lignes 1-4, max 5 lignes)
        commands_to_show = self.commands[:15]  # 15 commandes max pour éviter la limite de 25 composants
        
        for i, command in enumerate(commands_to_show):
            row = (i // 5) + 1  # 5 boutons par ligne
            if row <= 4:  # Maximum 4 lignes de commandes
                self.add_item(CommandToggleButton(self.bot, self.user_id, command, row))


class EnableAllButton(discord.ui.Button):
    def __init__(self, bot, user_id: int):
        super().__init__(label="✅ Activer Tout", style=discord.ButtonStyle.success, row=0)
        self.bot = bot
        self.user_id = user_id
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Vous n'êtes pas autorisé à utiliser ce menu.", ephemeral=True)
            return
        
        # Activer tous les logs DM
        await self.bot.db.query(
            "INSERT INTO dm_logs_preferences (user_id, enabled) VALUES (%s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
            (self.user_id, True, True)
        )
        
        # Activer toutes les commandes
        for command in self.bot.cogs:
            cog = self.bot.cogs[command]
            if hasattr(cog, 'get_commands'):
                for cmd in cog.get_commands():
                    if isinstance(cmd, app_commands.Command):
                        await self.bot.db.query(
                            "INSERT INTO dm_logs_commands (user_id, command_name, enabled) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
                            (self.user_id, cmd.name, True, True)
                        )
        
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.send_message(_("commands.dmlogs.all_enabled", self.user_id, guild_id), ephemeral=True)


class DisableAllButton(discord.ui.Button):
    def __init__(self, bot, user_id: int):
        super().__init__(label="❌ Désactiver Tout", style=discord.ButtonStyle.danger, row=0)
        self.bot = bot
        self.user_id = user_id
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Vous n'êtes pas autorisé à utiliser ce menu.", ephemeral=True)
            return
        
        # Désactiver tous les logs DM
        await self.bot.db.query(
            "INSERT INTO dm_logs_preferences (user_id, enabled) VALUES (%s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
            (self.user_id, False, False)
        )
        
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.send_message(_("commands.dmlogs.all_disabled", self.user_id, guild_id), ephemeral=True)


class CommandToggleButton(discord.ui.Button):
    def __init__(self, bot, user_id: int, command_name: str, row: int = 1):
        self.bot = bot
        self.user_id = user_id
        self.command_name = command_name
        
        # Déterminer le style et le label basé sur l'état actuel
        super().__init__(label=f"🔄 {command_name}", style=discord.ButtonStyle.secondary, row=row)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            guild_id = interaction.guild.id if interaction.guild else None
            await interaction.response.send_message(_("commands.dmlogs.unauthorized", self.user_id, guild_id), ephemeral=True)
            return
        
        # Vérifier l'état actuel
        result = await self.bot.db.query(
            "SELECT enabled FROM dm_logs_commands WHERE user_id = %s AND command_name = %s",
            (self.user_id, self.command_name),
            fetchone=True
        )
        
        current_state = result['enabled'] if result else False
        new_state = not current_state
        
        # Mettre à jour l'état
        await self.bot.db.query(
            "INSERT INTO dm_logs_commands (user_id, command_name, enabled) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE enabled = %s",
            (self.user_id, self.command_name, new_state, new_state)
        )
        
        # Mettre à jour le bouton
        if new_state:
            self.label = f"✅ {self.command_name}"
            self.style = discord.ButtonStyle.success
        else:
            self.label = f"❌ {self.command_name}"
            self.style = discord.ButtonStyle.danger
        
        # Envoyer une réponse temporaire
        guild_id = interaction.guild.id if interaction.guild else None
        status_text = _("commands.dmlogs.enabled", self.user_id, guild_id) if new_state else _("commands.dmlogs.disabled", self.user_id, guild_id)
        await interaction.response.send_message(f"🔄 Commande `{self.command_name}` {status_text.lower()}", ephemeral=True)
        
        # Mettre à jour la vue
        await interaction.edit_original_response(view=self.view)


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
        self.cooldowns: Dict[int, datetime] = {}  # Anti-spam
    
    @app_commands.command(
        name="dmlogs",
        description="Configure les logs DM pour recevoir des notifications privées"
    )
    async def dmlogs(self, interaction: discord.Interaction):
        """Commande principale pour configurer les logs DM"""
        user_id = interaction.user.id
        
        # Vérifier si l'utilisateur a déjà des préférences
        result = await self.bot.db.query(
            "SELECT enabled FROM dm_logs_preferences WHERE user_id = %s",
            (user_id,),
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
        enabled_commands = await self._get_enabled_commands(user_id)
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
        view = DMLogsConfigView(self.bot, user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _get_enabled_commands(self, user_id: int) -> List[str]:
        """Récupère la liste des commandes activées pour un utilisateur"""
        try:
            results = await self.bot.db.query(
                "SELECT command_name FROM dm_logs_commands WHERE user_id = %s AND enabled = TRUE",
                (user_id,)
            )
            return [result['command_name'] for result in results]
        except Exception:
            return []
    
    async def log_command_usage(self, command_name: str, executor: discord.Member, guild: discord.Guild = None):
        """Log l'utilisation d'une commande pour tous les utilisateurs qui l'ont activée"""
        try:
            # Récupérer tous les utilisateurs qui ont activé cette commande
            results = await self.bot.db.query(
                """SELECT DISTINCT dlp.user_id 
                   FROM dm_logs_preferences dlp
                   JOIN dm_logs_commands dlc ON dlp.user_id = dlc.user_id
                   WHERE dlp.enabled = TRUE 
                   AND dlc.command_name = %s 
                   AND dlc.enabled = TRUE""",
                (command_name,)
            )
            
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
                
                # Vérifier le cooldown anti-spam (5 minutes)
                if user_id in self.cooldowns:
                    if datetime.utcnow() - self.cooldowns[user_id] < timedelta(minutes=5):
                        continue
                
                try:
                    user = self.bot.get_user(user_id)
                    if user:
                        await user.send(embed=embed)
                        self.cooldowns[user_id] = datetime.utcnow()
                        
                        # Enregistrer dans l'historique
                        await self.bot.db.query(
                            "INSERT INTO dm_logs_history (user_id, command_name, executor_id, guild_id) VALUES (%s, %s, %s, %s)",
                            (user_id, command_name, executor.id, guild.id if guild else None)
                        )
                        
                except discord.Forbidden:
                    # L'utilisateur a désactivé les DMs
                    pass
                except Exception as e:
                    print(f"Erreur lors de l'envoi du log DM à {user_id}: {e}")
                    
        except Exception as e:
            print(f"Erreur dans log_command_usage: {e}")


async def setup(bot):
    await bot.add_cog(DMLogsSystem(bot))
