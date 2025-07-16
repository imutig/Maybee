import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from i18n import _

logger = logging.getLogger(__name__)

class ConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
        # Function to get translated text
        def _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key: str, **kwargs):
            return _(key, 0, guild_id, **kwargs)
        
        # Create select options with translations
        self.select_options = [
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.welcome.title").replace("🎉 ", ""),
                value="welcome",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.welcome.description"),
                emoji="👋"
            ),
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.confession.title").replace("💬 ", ""),
                value="confession",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.confession.description"),
                emoji="🔒"
            ),
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.role_requests.title").replace("🎭 ", ""),
                value="role_requests",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.role_requests.description"),
                emoji="📋"
            ),
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.role_reactions.title").replace("⚡ ", ""),
                value="role_reactions",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.role_reactions.description"),
                emoji="⚡"
            ),
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.xp_system.title").replace("📊 ", ""),
                value="xp_system",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.xp_system.description"),
                emoji="⬆️"
            ),
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.ticket_system.title").replace("🎫 ", ""),
                value="ticket_system",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.ticket_system.description"),
                emoji="🔧"
            ),
            discord.SelectOption(
                label=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.language.title").replace("🌍 ", ""),
                value="language",
                description=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.language.description"),
                emoji="🗣️"
            )
        ]
        
        # Create the select component
        self.config_select = discord.ui.Select(
            placeholder=_(key, 0, self.guild_id, **kwargs) if "key" in locals() else _("config_system.select_placeholder"),
            options=self.select_options
        )
        self.config_select.callback = self.config_select_callback
        self.add_item(self.config_select)
        
    async def config_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        select_value = self.config_select.values[0]
        
        if select_value == "welcome":
            await self.show_welcome_config(interaction)
        elif select_value == "confession":
            await self.show_confession_config(interaction)
        elif select_value == "role_requests":
            await self.show_role_requests_config(interaction)
        elif select_value == "role_reactions":
            await self.show_role_reactions_config(interaction)
        elif select_value == "xp_system":
            await self.show_xp_system_config(interaction)
        elif select_value == "ticket_system":
            await self.show_ticket_system_config(interaction)
        elif select_value == "language":
            await self.show_language_config(interaction)

    async def show_welcome_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.welcome.title"),
            description=_("config_system.welcome.description"),
            color=discord.Color.green()
        )
        
        # Get current config
        try:
            config = await self.bot.db.query(
                "SELECT welcome_channel, welcome_message, goodbye_channel, goodbye_message FROM welcome_config WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            if config:
                welcome_channel = self.bot.get_channel(config[0]) if config[0] else None
                goodbye_channel = self.bot.get_channel(config[2]) if config[2] else None
                
                embed.add_field(
                    name=_("config_system.welcome.welcome_channel"),
                    value=welcome_channel.mention if welcome_channel else _("config_system.welcome.not_configured"),
                    inline=True
                )
                embed.add_field(
                    name=_("config_system.welcome.welcome_message"),
                    value=config[1] if config[1] else _("config_system.welcome.not_configured"),
                    inline=False
                )
                embed.add_field(
                    name=_("config_system.welcome.goodbye_channel"),
                    value=goodbye_channel.mention if goodbye_channel else _("config_system.welcome.not_configured"),
                    inline=True
                )
                embed.add_field(
                    name=_("config_system.welcome.goodbye_message"),
                    value=config[3] if config[3] else _("config_system.welcome.not_configured"),
                    inline=False
                )
            else:
                embed.add_field(
                    name="État",
                    value=_("config_system.welcome.not_configured"),
                    inline=False
                )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la config welcome: {e}")
            embed.add_field(name=_("common.error"), value=_("config_system.welcome.error"), inline=False)
        
        view = WelcomeConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_confession_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.confession.title"),
            description=_("config_system.confession.description"),
            color=discord.Color.purple()
        )
        
        # Get current config
        try:
            config = await self.bot.db.query(
                "SELECT confession_channel FROM confession_config WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            if config and config[0]:
                channel = self.bot.get_channel(config[0])
                embed.add_field(
                    name=_("config_system.confession.confession_channel"),
                    value=channel.mention if channel else _("config_system.confession.channel_not_found"),
                    inline=False
                )
            else:
                embed.add_field(
                    name="État",
                    value=_("config_system.confession.not_configured"),
                    inline=False
                )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la config confession: {e}")
            embed.add_field(name=_("common.error"), value=_("config_system.confession.error"), inline=False)
        
        view = ConfessionConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_role_requests_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.role_requests.title"),
            description=_("config_system.role_requests.description"),
            color=discord.Color.orange()
        )
        
        # Get current config
        try:
            config = await self.bot.db.query(
                "SELECT role_request_channel FROM role_request_config WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            if config and config[0]:
                channel = self.bot.get_channel(config[0])
                embed.add_field(
                    name=_("config_system.role_requests.role_request_channel"),
                    value=channel.mention if channel else _("config_system.role_requests.channel_not_found"),
                    inline=False
                )
            else:
                embed.add_field(
                    name="État",
                    value=_("config_system.role_requests.not_configured"),
                    inline=False
                )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la config role requests: {e}")
            embed.add_field(name=_("common.error"), value=_("config_system.role_requests.error"), inline=False)
        
        view = RoleRequestsConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_role_reactions_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.role_reactions.title"),
            description=_("config_system.role_reactions.description"),
            color=discord.Color.yellow()
        )
        
        # Get current config
        try:
            count = await self.bot.db.query(
                "SELECT COUNT(*) as count FROM role_reactions WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            embed.add_field(
                name=_("config_system.role_reactions.active_configs"),
                value=_("config_system.role_reactions.configs_count", count=count['count']) if count['count'] > 0 else _("config_system.role_reactions.no_configs"),
                inline=False
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la config role reactions: {e}")
            embed.add_field(name=_("common.error"), value=_("config_system.role_reactions.error"), inline=False)
        
        view = RoleReactionsConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_xp_system_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.xp_system.title"),
            description=_("config_system.xp_system.description"),
            color=discord.Color.blue()
        )
        
        # Get current config
        try:
            config = await self.bot.db.query(
                "SELECT xp_channel FROM xp_config WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            if config and config[0]:
                channel = self.bot.get_channel(config[0])
                embed.add_field(
                    name=_("config_system.xp_system.xp_channel"),
                    value=channel.mention if channel else _("config_system.xp_system.channel_not_found"),
                    inline=False
                )
            else:
                embed.add_field(
                    name=_("config_system.xp_system.xp_channel"),
                    value=_("config_system.xp_system.not_configured"),
                    inline=False
                )
            
            # Count level roles
            count = await self.bot.db.query(
                "SELECT COUNT(*) as count FROM level_roles WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            embed.add_field(
                name=_("config_system.xp_system.level_roles"),
                value=_("config_system.xp_system.roles_count", count=count['count']) if count['count'] > 0 else _("config_system.xp_system.no_roles"),
                inline=False
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la config XP: {e}")
            embed.add_field(name=_("common.error"), value=_("config_system.xp_system.error"), inline=False)
        
        view = XPSystemConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_ticket_system_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.ticket_system.title"),
            description=_("config_system.ticket_system.description"),
            color=discord.Color.red()
        )
        
        # Check if ticket category exists
        guild = self.bot.get_guild(self.guild_id)
        ticket_category = discord.utils.get(guild.categories, name="Tickets 🔖")
        
        if ticket_category:
            embed.add_field(
                name=_("config_system.ticket_system.ticket_category"),
                value=_("config_system.ticket_system.configured", name=ticket_category.name),
                inline=False
            )
        else:
            embed.add_field(
                name=_("config_system.ticket_system.ticket_category"),
                value=_("config_system.ticket_system.not_configured"),
                inline=False
            )
        
        view = TicketSystemConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_language_config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        embed = discord.Embed(
            title=_("config_system.language.title"),
            description=_("config_system.language.description"),
            color=discord.Color.green()
        )
        
        # Get current config
        try:
            config = await self.bot.db.query(
                "SELECT language_code FROM guild_languages WHERE guild_id = ?",
                (self.guild_id,),
                fetchone=True
            )
            
            current_lang = config['language_code'] if config else "en"
            language_names = {"en": "🇺🇸 English", "fr": "🇫🇷 Français"}
            
            embed.add_field(
                name=_("config_system.language.current_language"),
                value=language_names.get(current_lang, current_lang),
                inline=False
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la config language: {e}")
            embed.add_field(name=_("common.error"), value=_("config_system.language.error"), inline=False)
        
        view = LanguageConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class WelcomeConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Configurer bienvenue", style=discord.ButtonStyle.green, emoji="👋")
    async def configure_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update button label with translation
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.welcome.configure_welcome_button")
        
        modal = WelcomeConfigModal(self.bot, self.guild_id, "welcome")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configurer au revoir", style=discord.ButtonStyle.red, emoji="👋")
    async def configure_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update button label with translation
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.welcome.configure_goodbye_button")
        
        modal = WelcomeConfigModal(self.bot, self.guild_id, "goodbye")
        await interaction.response.send_modal(modal)


class WelcomeConfigModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int, config_type: str):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=guild_id, **kwargs)
            
        title = _("config_system.welcome.welcome_modal_title") if config_type == "welcome" else _("config_system.welcome.goodbye_modal_title")
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.config_type = config_type

        self.channel_input = discord.ui.TextInput(
            label=_("config_system.welcome.channel_id_label"),
            placeholder=_("config_system.welcome.channel_id_placeholder"),
            required=True
        )
        self.add_item(self.channel_input)

        placeholder = _("config_system.welcome.message_placeholder_welcome") if config_type == "welcome" else _("config_system.welcome.message_placeholder_goodbye")
        self.message_input = discord.ui.TextInput(
            label=_("config_system.welcome.message_label"),
            placeholder=placeholder,
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        try:
            channel_id = int(self.channel_input.value)
            channel = self.bot.get_channel(channel_id)
            
            if not channel or channel.guild.id != self.guild_id:
                await interaction.response.send_message(_("config_system.welcome.channel_not_found"), ephemeral=True)
                return

            if self.config_type == "welcome":
                await self.bot.db.query(
                    "INSERT INTO welcome_config (guild_id, welcome_channel, welcome_message) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE welcome_channel = VALUES(welcome_channel), welcome_message = VALUES(welcome_message)",
                    (self.guild_id, channel_id, self.message_input.value)
                )
                success_msg = _("config_system.welcome.success_welcome")
            else:
                await self.bot.db.query(
                    "INSERT INTO welcome_config (guild_id, goodbye_channel, goodbye_message) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE goodbye_channel = VALUES(goodbye_channel), goodbye_message = VALUES(goodbye_message)",
                    (self.guild_id, channel_id, self.message_input.value)
                )
                success_msg = _("config_system.welcome.success_goodbye")
            await interaction.response.send_message(success_msg, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(_("config_system.welcome.channel_id_invalid"), ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la configuration welcome: {e}")
            await interaction.response.send_message(_("config_system.welcome.error"), ephemeral=True)


class ConfessionConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Configurer canal", style=discord.ButtonStyle.primary, emoji="💬")
    async def configure_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update button label with translation
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.confession.configure_button")
        
        modal = ConfessionConfigModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)


class ConfessionConfigModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=guild_id, **kwargs)
            
        super().__init__(title=_("config_system.confession.modal_title"))
        self.bot = bot
        self.guild_id = guild_id

        self.channel_input = discord.ui.TextInput(
            label=_("config_system.confession.channel_id_label"),
            placeholder=_("config_system.confession.channel_id_placeholder"),
            required=True
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        try:
            channel_id = int(self.channel_input.value)
            channel = self.bot.get_channel(channel_id)
            
            if not channel or channel.guild.id != self.guild_id:
                await interaction.response.send_message(_("config_system.confession.channel_not_found"), ephemeral=True)
                return

            await self.bot.db.query(
                "INSERT INTO confession_config (guild_id, channel_id) VALUES (?, ?) ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id)",
                (self.guild_id, channel_id)
            )
            
            await interaction.response.send_message(_("config_system.confession.success", channel=channel.mention), ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(_("config_system.welcome.channel_id_invalid"), ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la configuration confession: {e}")
            await interaction.response.send_message(_("config_system.confession.error"), ephemeral=True)


class RoleRequestsConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Configurer canal", style=discord.ButtonStyle.primary, emoji="🎭")
    async def configure_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update button label with translation
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.role_requests.configure_button")
        
        modal = RoleRequestsConfigModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)


class RoleRequestsConfigModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=guild_id, **kwargs)
            
        super().__init__(title=_("config_system.role_requests.modal_title"))
        self.bot = bot
        self.guild_id = guild_id

        self.channel_input = discord.ui.TextInput(
            label=_("config_system.role_requests.channel_id_label"),
            placeholder=_("config_system.role_requests.channel_id_placeholder"),
            required=True
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        try:
            channel_id = int(self.channel_input.value)
            channel = self.bot.get_channel(channel_id)
            
            if not channel or channel.guild.id != self.guild_id:
                await interaction.response.send_message(_("config_system.role_requests.channel_not_found"), ephemeral=True)
                return

            await self.bot.db.query(
                "INSERT INTO role_request_config (guild_id, channel_id) VALUES (?, ?) ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id)",
                (self.guild_id, channel_id)
            )
            
            await interaction.response.send_message(_("config_system.role_requests.success", channel=channel.mention), ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(_("config_system.welcome.channel_id_invalid"), ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la configuration role requests: {e}")
            await interaction.response.send_message(_("config_system.role_requests.error"), ephemeral=True)


class RoleReactionsConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Configurer rôles par réaction", style=discord.ButtonStyle.primary, emoji="⚡")
    async def configure_role_reactions(self, interaction: discord.Interaction, button: discord.ui.Button):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.role_reactions.configure_button")
        
        await interaction.response.send_message(
            _("config_system.role_reactions.interactive_warning"),
            ephemeral=True
        )


class XPSystemConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Configurer canal XP", style=discord.ButtonStyle.green, emoji="📢")
    async def configure_xp_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.xp_system.configure_channel_button")
        
        modal = XPChannelConfigModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configurer rôle de niveau", style=discord.ButtonStyle.blue, emoji="🎖️")
    async def configure_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.xp_system.configure_role_button")
        
        modal = LevelRoleConfigModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)


class XPChannelConfigModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=guild_id, **kwargs)
            
        super().__init__(title=_("config_system.xp_system.channel_modal_title"))
        self.bot = bot
        self.guild_id = guild_id

        self.channel_input = discord.ui.TextInput(
            label=_("config_system.xp_system.channel_id_label"),
            placeholder=_("config_system.xp_system.channel_id_placeholder"),
            required=True
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        try:
            channel_id = int(self.channel_input.value)
            channel = self.bot.get_channel(channel_id)
            
            if not channel or channel.guild.id != self.guild_id:
                await interaction.response.send_message(_("config_system.xp_system.channel_not_found"), ephemeral=True)
                return

            await self.bot.db.query(
                "INSERT INTO xp_config (guild_id, xp_channel) VALUES (?, ?) ON DUPLICATE KEY UPDATE xp_channel = VALUES(xp_channel)",
                (self.guild_id, channel_id)
            )
            
            await interaction.response.send_message(_("config_system.xp_system.channel_success", channel=channel.mention), ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(_("config_system.xp_system.invalid_numbers"), ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la configuration XP channel: {e}")
            await interaction.response.send_message(_("config_system.xp_system.error"), ephemeral=True)


class LevelRoleConfigModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=guild_id, **kwargs)
            
        super().__init__(title=_("config_system.xp_system.role_modal_title"))
        self.bot = bot
        self.guild_id = guild_id

        self.level_input = discord.ui.TextInput(
            label=_("config_system.xp_system.level_label"),
            placeholder=_("config_system.xp_system.level_placeholder"),
            required=True
        )
        self.add_item(self.level_input)

        self.role_input = discord.ui.TextInput(
            label=_("config_system.xp_system.role_id_label"),
            placeholder=_("config_system.xp_system.role_id_placeholder"),
            required=True
        )
        self.add_item(self.role_input)

    async def on_submit(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        try:
            level = int(self.level_input.value)
            role_id = int(self.role_input.value)
            
            guild = self.bot.get_guild(self.guild_id)
            role = guild.get_role(role_id)
            
            if not role:
                await interaction.response.send_message(_("config_system.xp_system.role_not_found"), ephemeral=True)
                return

            await self.bot.db.query(
                "INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE role_id = VALUES(role_id)",
                (self.guild_id, level, role_id)
            )
            
            await interaction.response.send_message(_("config_system.xp_system.role_success", role=role.mention, level=level), ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(_("config_system.xp_system.invalid_numbers"), ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur lors de la configuration level role: {e}")
            await interaction.response.send_message(_("config_system.xp_system.error"), ephemeral=True)


class TicketSystemConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Configurer système", style=discord.ButtonStyle.red, emoji="🔧")
    async def configure_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
        button.label = _("config_system.ticket_system.configure_button")
        
        await interaction.response.send_message(
            _("config_system.ticket_system.setup_warning"),
            ephemeral=True
        )


class LanguageConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=guild_id, **kwargs)

        self.language_select = discord.ui.Select(
            placeholder=_("config_system.language.select_placeholder"),
            options=[
                discord.SelectOption(label="English", value="en", emoji="🇺🇸"),
                discord.SelectOption(label="Français", value="fr", emoji="🇫🇷")
            ]
        )
        self.language_select.callback = self.language_select_callback
        self.add_item(self.language_select)

    async def language_select_callback(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=self.guild_id, **kwargs)
            
        try:
            language_code = self.language_select.values[0]
            
            await self.bot.db.query(
                "INSERT INTO guild_languages (guild_id, language_code) VALUES (?, ?) ON DUPLICATE KEY UPDATE language_code = VALUES(language_code)",
                (self.guild_id, language_code)
            )
            
            language_names = {"en": "🇺🇸 English", "fr": "🇫🇷 Français"}
            await interaction.response.send_message(
                _("config_system.language.success", language=language_names[language_code]),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration language: {e}")
            await interaction.response.send_message(_("config_system.language.error"), ephemeral=True)


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="config", description="Configuration unifiée de tous les systèmes du bot")
    async def config(self, interaction: discord.Interaction):
        def _(key: str, **kwargs):
            return _(key, 0, self.guild_id, **kwargs) if "key" in locals() else _(key, guild_id=interaction.guild.id, **kwargs)
            
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("config_system.no_permission"),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=_("config_system.title"),
            description=_("config_system.description_text"),
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name=_("config_system.systems_available"),
            value=_("config_system.systems_list"),
            inline=False
        )
        
        view = ConfigView(self.bot, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Config(bot))
