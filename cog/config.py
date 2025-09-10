import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from datetime import datetime
from i18n import _
from .command_logger import log_command_usage
from custom_emojis import YELLOW_COG, BLUE_COG, GREEN_COG, SHIELD, TROPHY, USERS, TICKET, CHART_BAR, SUCCESS, ERROR, WARNING, INFO, GLOBE, FIRE, CLOCK, CHECK, CROSS, TRASH

logger = logging.getLogger(__name__)

class ConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
        # We'll create the select options dynamically when needed
        # to use the user's language preference
        
    def create_select_options(self, user_id: int):
        """Create options with user's language preference"""
        return [
            discord.SelectOption(
                label=_("config_system.welcome.title", user_id, self.guild_id).replace("🎉 ", ""),
                value="welcome",
                description=_("config_system.welcome.description", user_id, self.guild_id),
                emoji="👋"
            ),
            discord.SelectOption(
                label=_("config_system.confession.title", user_id, self.guild_id).replace("💬 ", ""),
                value="confession",
                description=_("config_system.confession.description", user_id, self.guild_id),
                emoji="🔒"
            ),
            discord.SelectOption(
                label=_("config_system.role_reactions.title", user_id, self.guild_id).replace("⚡ ", ""),
                value="role_reactions",
                description=_("config_system.role_reactions.description", user_id, self.guild_id),
                emoji="⚡"
            ),
            discord.SelectOption(
                label=_("config_system.xp_system.title", user_id, self.guild_id).replace("📊 ", ""),
                value="xp_system",
                description=_("config_system.xp_system.description", user_id, self.guild_id),
                emoji="⬆️"
            ),
            discord.SelectOption(
                label=_("config_system.language.title", user_id, self.guild_id).replace("🌍 ", ""),
                value="language",
                description=_("config_system.language.description", user_id, self.guild_id),
                emoji="🗣️"
            ),
            discord.SelectOption(
                label=_("config_system.server_logs.title", user_id, self.guild_id).replace("📋 ", ""),
                value="server_logs",
                description=_("config_system.server_logs.description", user_id, self.guild_id),
                emoji="📋"
            )
        ]
    
    def setup_select_for_user(self, user_id: int):
        """Setup the select component for a specific user"""
        if hasattr(self, 'config_select') and self.config_select in self.children:
            self.remove_item(self.config_select)
        
        # Create the select component with user's language
        self.config_select = discord.ui.Select(
            placeholder=_("config_system.select_placeholder", user_id, self.guild_id),
            options=self.create_select_options(user_id)
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
        elif select_value == "role_reactions":
            await self.show_role_reactions_config(interaction)
        elif select_value == "xp_system":
            await self.show_xp_system_config(interaction)
        elif select_value == "language":
            await self.show_language_config(interaction)
        elif select_value == "server_logs":
            await self.show_server_logs_config(interaction)

    async def show_welcome_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{USERS} {_('config_system.welcome.title', interaction.user.id, self.guild_id)}",
            description=f"{GLOBE} **{_('config_system.welcome.use_dashboard', interaction.user.id, self.guild_id)}**\n\n{_('config_system.welcome.dashboard_description', interaction.user.id, self.guild_id)}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name=f"{GLOBE} {_('config_system.welcome.dashboard_access', interaction.user.id, self.guild_id)}",
            value=_("config_system.welcome.dashboard_features", interaction.user.id, self.guild_id),
            inline=False
        )
        
        embed.add_field(
            name=f"{INFO} {_('config_system.welcome.dashboard_benefits', interaction.user.id, self.guild_id)}",
            value=_("config_system.welcome.dashboard_benefits_list", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = DashboardRedirectView("welcome")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_confession_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{TICKET} {_('config_system.confession.title', interaction.user.id, self.guild_id)}",
            description=_("config_system.confession.description", interaction.user.id, self.guild_id),
            color=discord.Color.purple()
        )
        
        # Get current confession settings
        result = await self.bot.db.query("SELECT channel_id FROM confession_config WHERE guild_id = %s", (self.guild_id,), fetchone=True)
        confession_channel = result["channel_id"] if result else None
        
        if confession_channel:
            channel = self.bot.get_channel(confession_channel)
            embed.add_field(
                name=f"{TICKET} {_('config_system.confession.current_channel', interaction.user.id, self.guild_id)}",
                value=channel.mention if channel else _("config_system.confession.channel_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        
        view = ConfessionConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_role_reactions_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{TROPHY} {_('config_system.role_reactions.title', interaction.user.id, self.guild_id)}",
            description=f"{GLOBE} **{_('config_system.role_reactions.use_dashboard', interaction.user.id, self.guild_id)}**\n\n{_('config_system.role_reactions.dashboard_description', interaction.user.id, self.guild_id)}",
            color=discord.Color.yellow()
        )
        
        embed.add_field(
            name=f"{GLOBE} {_('config_system.role_reactions.dashboard_features', interaction.user.id, self.guild_id)}",
            value=_("config_system.role_reactions.dashboard_features_list", interaction.user.id, self.guild_id),
            inline=False
        )
        
        embed.add_field(
            name=f"{INFO} {_('config_system.role_reactions.dashboard_benefits', interaction.user.id, self.guild_id)}",
            value=_("config_system.role_reactions.dashboard_benefits_list", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = DashboardRedirectView("role_reactions")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_xp_system_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{CHART_BAR} {_('config_system.xp_system.title', interaction.user.id, self.guild_id)}",
            description=f"{GLOBE} **{_('config_system.xp_system.use_dashboard', interaction.user.id, self.guild_id)}**\n\n{_('config_system.xp_system.dashboard_description', interaction.user.id, self.guild_id)}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name=f"{GLOBE} {_('config_system.xp_system.dashboard_features', interaction.user.id, self.guild_id)}",
            value=_("config_system.xp_system.dashboard_features_list", interaction.user.id, self.guild_id),
            inline=False
        )
        
        embed.add_field(
            name=f"{WARNING} {_('config_system.xp_system.xp_reset_warning', interaction.user.id, self.guild_id)}",
            value=_("config_system.xp_system.xp_reset_description", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = DashboardRedirectView("xp_system")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_language_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{GLOBE} {_('config_system.language.title', interaction.user.id, self.guild_id)}",
            description=_("config_system.language.description", interaction.user.id, self.guild_id),
            color=discord.Color.blurple()
        )
        
        # Get current language
        result = await self.bot.db.query("SELECT language_code FROM guild_languages WHERE guild_id = %s", (self.guild_id,), fetchone=True)
        current_language = result["language_code"] if result else "en"
        
        embed.add_field(
            name=f"{GLOBE} {_('config_system.language.current_language', interaction.user.id, self.guild_id)}",
            value=_("config_system.language.english", interaction.user.id, self.guild_id) if current_language == "en" else _("config_system.language.french", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = LanguageConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_server_logs_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{CHART_BAR} {_('config_system.server_logs.title', interaction.user.id, self.guild_id)}",
            description=f"{GLOBE} **{_('config_system.server_logs.use_dashboard', interaction.user.id, self.guild_id)}**\n\n{_('config_system.server_logs.dashboard_description', interaction.user.id, self.guild_id)}",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name=f"{GLOBE} {_('config_system.server_logs.dashboard_features', interaction.user.id, self.guild_id)}",
            value=_("config_system.server_logs.dashboard_features_list", interaction.user.id, self.guild_id),
            inline=False
        )
        
        embed.add_field(
            name=f"{INFO} {_('config_system.server_logs.dashboard_benefits', interaction.user.id, self.guild_id)}",
            value=_("config_system.server_logs.dashboard_benefits_list", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = DashboardRedirectView("server_logs")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# Configuration views for each system
class DashboardRedirectView(discord.ui.View):
    def __init__(self, system_name: str):
        super().__init__(timeout=300)
        self.system_name = system_name
        
        # Add a link button for the dashboard
        dashboard_button = discord.ui.Button(
            label="Open Dashboard",
            style=discord.ButtonStyle.link,
            emoji="🌐",
            url="https://web-production-448ba.up.railway.app/"
        )
        self.add_item(dashboard_button)
    
    @discord.ui.button(label="Get Dashboard Link", style=discord.ButtonStyle.secondary, emoji="🔗")
    async def get_dashboard_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"🌐 {_('config_system.dashboard.access_title', interaction.user.id, interaction.guild.id)}",
            description=_('config_system.dashboard.access_description', interaction.user.id, interaction.guild.id, system=self.system_name.replace('_', ' ').title()),
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name=f"📱 {_('config_system.dashboard.url_title', interaction.user.id, interaction.guild.id)}",
            value=f"[{_('config_system.dashboard.click_here', interaction.user.id, interaction.guild.id)}](https://web-production-448ba.up.railway.app/)",
            inline=False
        )
        
        embed.add_field(
            name=f"🔐 {_('config_system.dashboard.login_title', interaction.user.id, interaction.guild.id)}",
            value=_('config_system.dashboard.login_description', interaction.user.id, interaction.guild.id),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfessionConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.primary, emoji="📢")
    async def set_confession_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ConfessionChannelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🚫")
    async def disable_confession(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query("DELETE FROM confession_config WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(_("config_system.confession.disabled", interaction.user.id, self.guild_id), ephemeral=True)



class LanguageConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="English", style=discord.ButtonStyle.primary, emoji="🇺🇸")
    async def set_english(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.i18n.set_guild_language_db(self.guild_id, 'en', self.bot.db)
        await interaction.response.send_message(_("config_system.language.changed_to_english", interaction.user.id, self.guild_id), ephemeral=True)
    
    @discord.ui.button(label="Français", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def set_french(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.i18n.set_guild_language_db(self.guild_id, 'fr', self.bot.db)
        await interaction.response.send_message(_("config_system.language.changed_to_french", interaction.user.id, self.guild_id), ephemeral=True)

# Modal classes for configuration inputs (kept for systems still using /config)
class ConfessionChannelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set Confession Channel")
        self.bot = bot
        self.guild_id = guild_id
        
        self.channel_input = discord.ui.TextInput(
            label="Channel ID or Name",
            placeholder="Enter channel ID or #channel-name",
            required=True
        )
        self.add_item(self.channel_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        channel_input = self.channel_input.value.strip()
        
        # Try to find the channel
        channel = None
        if channel_input.startswith('<#') and channel_input.endswith('>'):
            channel_id = int(channel_input[2:-1])
            channel = interaction.guild.get_channel(channel_id)
        elif channel_input.startswith('#'):
            channel = discord.utils.get(interaction.guild.channels, name=channel_input[1:])
        elif channel_input.isdigit():
            channel = interaction.guild.get_channel(int(channel_input))
        else:
            channel = discord.utils.get(interaction.guild.channels, name=channel_input)
        
        if not channel:
            await interaction.response.send_message(_("config_system.confession.channel_not_found", interaction.user.id, self.guild_id), ephemeral=True)
            return
        
        await self.bot.db.query("INSERT INTO confession_config (guild_id, channel_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE channel_id = %s", (self.guild_id, channel.id, channel.id))
        await interaction.response.send_message(_("config_system.confession.channel_set", interaction.user.id, self.guild_id, channel=channel.mention), ephemeral=True)


class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Config cog initialized")

    @app_commands.command(name="config", description="Configure bot settings")
    @log_command_usage
    async def config(self, interaction: discord.Interaction):
        """Unified configuration command for all bot systems"""
        
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                f"{ERROR} {_('config_system.permissions.no_admin_permission', interaction.user.id, interaction.guild.id)}",
                ephemeral=True
            )
            return
        
        # Create main config view
        view = ConfigView(self.bot, interaction.guild_id)
        view.setup_select_for_user(interaction.user.id)
        
        embed = discord.Embed(
            title=f"{YELLOW_COG} {_('config_system.main.title', interaction.user.id, interaction.guild.id)}",
            description=_('config_system.main.description', interaction.user.id, interaction.guild.id),
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
