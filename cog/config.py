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
        
        # We'll create the select options dynamically when needed
        # to use the user's language preference
        
    def create_select_options(self, user_id: int):
        """Create select options with user's language preference"""
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
                label=_("config_system.role_requests.title", user_id, self.guild_id).replace("🎭 ", ""),
                value="role_requests",
                description=_("config_system.role_requests.description", user_id, self.guild_id),
                emoji="📋"
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
                label=_("config_system.ticket_system.title", user_id, self.guild_id).replace("🎫 ", ""),
                value="ticket_system",
                description=_("config_system.ticket_system.description", user_id, self.guild_id),
                emoji="🔧"
            ),
            discord.SelectOption(
                label=_("config_system.language.title", user_id, self.guild_id).replace("🌍 ", ""),
                value="language",
                description=_("config_system.language.description", user_id, self.guild_id),
                emoji="🗣️"
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
        embed = discord.Embed(
            title=_("config_system.welcome.title", interaction.user.id, self.guild_id),
            description=_("config_system.welcome.description", interaction.user.id, self.guild_id),
            color=discord.Color.green()
        )
        
        # Get current welcome settings
        result = await self.bot.db.query("SELECT welcome_channel, welcome_message FROM welcome_config WHERE guild_id = %s", (self.guild_id,))
        welcome_channel = result[0]["welcome_channel"] if result else None
        welcome_message = result[0]["welcome_message"] if result else None
        
        if welcome_channel:
            channel = self.bot.get_channel(welcome_channel)
            embed.add_field(
                name=_("config_system.welcome.current_channel", interaction.user.id, self.guild_id),
                value=channel.mention if channel else _("config_system.welcome.channel_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        
        if welcome_message:
            embed.add_field(
                name=_("config_system.welcome.current_message", interaction.user.id, self.guild_id),
                value=welcome_message[:1024] + "..." if len(welcome_message) > 1024 else welcome_message,
                inline=False
            )
        
        view = WelcomeConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_confession_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.confession.title", interaction.user.id, self.guild_id),
            description=_("config_system.confession.description", interaction.user.id, self.guild_id),
            color=discord.Color.purple()
        )
        
        # Get current confession settings
        result = await self.bot.db.query("SELECT channel_id FROM confession_config WHERE guild_id = %s", (self.guild_id,))
        confession_channel = result[0]["channel_id"] if result else None
        
        if confession_channel:
            channel = self.bot.get_channel(confession_channel)
            embed.add_field(
                name=_("config_system.confession.current_channel", interaction.user.id, self.guild_id),
                value=channel.mention if channel else _("config_system.confession.channel_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        
        view = ConfessionConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_role_requests_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.role_requests.title", interaction.user.id, self.guild_id),
            description=_("config_system.role_requests.description", interaction.user.id, self.guild_id),
            color=discord.Color.orange()
        )
        
        # Get current role request settings
        result = await self.bot.db.query("SELECT channel_id FROM role_request_config WHERE guild_id = %s", (self.guild_id,))
        role_request_channel = result[0]["channel_id"] if result else None
        
        if role_request_channel:
            channel = self.bot.get_channel(role_request_channel)
            embed.add_field(
                name=_("config_system.role_requests.current_channel", interaction.user.id, self.guild_id),
                value=channel.mention if channel else _("config_system.role_requests.channel_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        
        view = RoleRequestsConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_role_reactions_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.role_reactions.title", interaction.user.id, self.guild_id),
            description=_("config_system.role_reactions.description", interaction.user.id, self.guild_id),
            color=discord.Color.yellow()
        )
        
        # Get current role reaction settings
        result = await self.bot.db.query("SELECT * FROM role_reactions WHERE guild_id = %s", (self.guild_id,))
        
        if result:
            embed.add_field(
                name=_("config_system.role_reactions.current_reactions", interaction.user.id, self.guild_id),
                value=f"{len(result)} " + _("config_system.role_reactions.reactions_configured", interaction.user.id, self.guild_id),
                inline=False
            )
        else:
            embed.add_field(
                name=_("config_system.role_reactions.current_reactions", interaction.user.id, self.guild_id),
                value=_("config_system.role_reactions.no_configs", interaction.user.id, self.guild_id),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ Information",
            value=_("config_system.role_reactions.interactive_warning", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = RoleReactionsInfoView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_xp_system_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.xp_system.title", interaction.user.id, self.guild_id),
            description=_("config_system.xp_system.description", interaction.user.id, self.guild_id),
            color=discord.Color.blue()
        )
        
        # Get current XP system settings  
        # XP system is always enabled, check if there's a config entry
        result = await self.bot.db.query("SELECT xp_channel FROM xp_config WHERE guild_id = %s", (self.guild_id,))
        xp_enabled = len(result) > 0 if result else False
        xp_channel = result[0]["xp_channel"] if result and result[0]["xp_channel"] else None
        
        embed.add_field(
            name=_("config_system.xp_system.current_status", interaction.user.id, self.guild_id),
            value=_("config_system.xp_system.enabled", interaction.user.id, self.guild_id) if xp_enabled else _("config_system.xp_system.disabled", interaction.user.id, self.guild_id),
            inline=False
        )
        
        if xp_channel:
            channel = self.bot.get_channel(xp_channel)
            embed.add_field(
                name=_("config_system.xp_system.xp_channel", interaction.user.id, self.guild_id),
                value=channel.mention if channel else _("config_system.xp_system.channel_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        else:
            embed.add_field(
                name=_("config_system.xp_system.xp_channel", interaction.user.id, self.guild_id),
                value=_("config_system.xp_system.not_configured", interaction.user.id, self.guild_id),
                inline=False
            )
        
        view = XPSystemConfigView(self.bot, self.guild_id)
        view.setup_buttons_for_user(interaction.user.id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_ticket_system_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.ticket_system.title", interaction.user.id, self.guild_id),
            description=_("config_system.ticket_system.description", interaction.user.id, self.guild_id),
            color=discord.Color.red()
        )
        
        # Get current ticket system settings
        # Ticket system doesn't have a dedicated config table, so we'll simulate it
        # by checking if there are any ticket-related configurations
        ticket_category = None
        ticket_support_role = None
        
        if ticket_category:
            category = self.bot.get_channel(ticket_category)
            embed.add_field(
                name=_("config_system.ticket_system.current_category", interaction.user.id, self.guild_id),
                value=category.name if category else _("config_system.ticket_system.category_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        
        if ticket_support_role:
            role = interaction.guild.get_role(ticket_support_role)
            embed.add_field(
                name=_("config_system.ticket_system.current_support_role", interaction.user.id, self.guild_id),
                value=role.mention if role else _("config_system.ticket_system.role_not_found", interaction.user.id, self.guild_id),
                inline=False
            )
        
        view = TicketSystemConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_language_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.language.title", interaction.user.id, self.guild_id),
            description=_("config_system.language.description", interaction.user.id, self.guild_id),
            color=discord.Color.blurple()
        )
        
        # Get current language
        result = await self.bot.db.query("SELECT language_code FROM guild_languages WHERE guild_id = %s", (self.guild_id,))
        current_language = result[0]["language_code"] if result else "en"
        
        embed.add_field(
            name=_("config_system.language.current_language", interaction.user.id, self.guild_id),
            value=_("config_system.language.english", interaction.user.id, self.guild_id) if current_language == "en" else _("config_system.language.french", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = LanguageConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# Configuration views for each system
class WelcomeConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.primary, emoji="📢")
    async def set_welcome_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WelcomeChannelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Set Message", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def set_welcome_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WelcomeMessageModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🚫")
    async def disable_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query("DELETE FROM welcome_config WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(_("config_system.welcome.disabled", interaction.user.id, self.guild_id), ephemeral=True)

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

class RoleRequestsConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.primary, emoji="📢")
    async def set_role_request_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RoleRequestChannelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🚫")
    async def disable_role_requests(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query("DELETE FROM role_request_config WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(_("config_system.role_requests.disabled", interaction.user.id, self.guild_id), ephemeral=True)

class RoleReactionsInfoView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Use /rolereact", style=discord.ButtonStyle.primary, emoji="⚡")
    async def use_rolereact(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            _("config_system.role_reactions.use_command_button", interaction.user.id, self.guild_id) + "\n\n" +
            "💡 **Tip:** Type `/rolereact` to access the full role reaction management interface!",
            ephemeral=True
        )

class XPSystemConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    def setup_buttons_for_user(self, user_id: int):
        """Setup buttons with user's language preference"""
        self.clear_items()
        
        # Create buttons with proper translations
        self.set_channel_button = discord.ui.Button(
            label=_("config_system.xp_system.configure_channel_button", user_id, self.guild_id),
            style=discord.ButtonStyle.secondary,
            emoji="📢"
        )
        self.set_channel_button.callback = self.set_xp_channel
        self.add_item(self.set_channel_button)
        
        self.enable_button = discord.ui.Button(
            label="Enable",
            style=discord.ButtonStyle.success,
            emoji="✅"
        )
        self.enable_button.callback = self.enable_xp_system
        self.add_item(self.enable_button)
        
        self.disable_button = discord.ui.Button(
            label="Disable",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )
        self.disable_button.callback = self.disable_xp_system
        self.add_item(self.disable_button)
        
        self.set_rate_button = discord.ui.Button(
            label="Set Rate",
            style=discord.ButtonStyle.secondary,
            emoji="⚙️"
        )
        self.set_rate_button.callback = self.set_xp_rate
        self.add_item(self.set_rate_button)
    
    async def set_xp_channel(self, interaction: discord.Interaction):
        modal = XPChannelModal(self.bot, self.guild_id, interaction.user.id)
        await interaction.response.send_modal(modal)
    
    async def enable_xp_system(self, interaction: discord.Interaction):
        # Enable XP system by ensuring there's a config entry
        await self.bot.db.query("INSERT INTO xp_config (guild_id) VALUES (%s) ON DUPLICATE KEY UPDATE guild_id = guild_id", (self.guild_id,))
        await interaction.response.send_message(_("config_system.xp_system.enabled_success", interaction.user.id, self.guild_id), ephemeral=True)
    
    async def disable_xp_system(self, interaction: discord.Interaction):
        # Disable XP system by removing config entry
        await self.bot.db.query("DELETE FROM xp_config WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(_("config_system.xp_system.disabled_success", interaction.user.id, self.guild_id), ephemeral=True)
    
    async def set_xp_rate(self, interaction: discord.Interaction):
        modal = XPRateModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)

class TicketSystemConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Set Category", style=discord.ButtonStyle.primary, emoji="📁")
    async def set_ticket_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketCategoryModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Set Support Role", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def set_support_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketSupportRoleModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🚫")
    async def disable_ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ticket system configuration is not implemented in database
        await interaction.response.send_message(_("config_system.ticket_system.not_implemented", interaction.user.id, self.guild_id), ephemeral=True)

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

# Modal classes for configuration inputs
class WelcomeChannelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set Welcome Channel")
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
            await interaction.response.send_message(_("config_system.welcome.channel_not_found", interaction.user.id, self.guild_id), ephemeral=True)
            return
        
        await self.bot.db.query("INSERT INTO welcome_config (guild_id, welcome_channel) VALUES (%s, %s) ON DUPLICATE KEY UPDATE welcome_channel = %s", (self.guild_id, channel.id, channel.id))
        await interaction.response.send_message(_("config_system.welcome.channel_set", interaction.user.id, self.guild_id, channel=channel.mention), ephemeral=True)

class WelcomeMessageModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set Welcome Message")
        self.bot = bot
        self.guild_id = guild_id
        
        self.message_input = discord.ui.TextInput(
            label="Welcome Message",
            placeholder="Enter welcome message (use {user} for user mention)",
            style=discord.TextStyle.long,
            required=True,
            max_length=2000
        )
        self.add_item(self.message_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        message = self.message_input.value
        await self.bot.db.query("INSERT INTO welcome_config (guild_id, welcome_message) VALUES (%s, %s) ON DUPLICATE KEY UPDATE welcome_message = %s", (self.guild_id, message, message))
        await interaction.response.send_message(_("config_system.welcome.message_set", interaction.user.id, self.guild_id), ephemeral=True)

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

class RoleRequestChannelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set Role Request Channel")
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
            await interaction.response.send_message(_("config_system.role_requests.channel_not_found", interaction.user.id, self.guild_id), ephemeral=True)
            return
        
        await self.bot.db.query("INSERT INTO role_request_config (guild_id, channel_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE channel_id = %s", (self.guild_id, channel.id, channel.id))
        await interaction.response.send_message(_("config_system.role_requests.channel_set", interaction.user.id, self.guild_id, channel=channel.mention), ephemeral=True)

class XPChannelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(title=_("config_system.xp_system.channel_modal_title", user_id, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        
        self.channel_input = discord.ui.TextInput(
            label=_("config_system.xp_system.channel_id_label", user_id, guild_id),
            placeholder=_("config_system.xp_system.channel_id_placeholder", user_id, guild_id),
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
            await interaction.response.send_message(_("config_system.xp_system.channel_not_found", interaction.user.id, self.guild_id), ephemeral=True)
            return
        
        await self.bot.db.query("INSERT INTO xp_config (guild_id, xp_channel) VALUES (%s, %s) ON DUPLICATE KEY UPDATE xp_channel = %s", (self.guild_id, channel.id, channel.id))
        await interaction.response.send_message(_("config_system.xp_system.channel_success", interaction.user.id, self.guild_id, channel=channel.mention), ephemeral=True)

class XPRateModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set XP Rate")
        self.bot = bot
        self.guild_id = guild_id
        
        self.rate_input = discord.ui.TextInput(
            label="XP Rate Multiplier",
            placeholder="Enter a number (e.g., 1.5 for 150% rate)",
            required=True
        )
        self.add_item(self.rate_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # XP rate is not stored in database
        await interaction.response.send_message(_("config_system.xp_system.rate_not_supported", interaction.user.id, self.guild_id), ephemeral=True)

class TicketCategoryModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set Ticket Category")
        self.bot = bot
        self.guild_id = guild_id
        
        self.category_input = discord.ui.TextInput(
            label="Category Name or ID",
            placeholder="Enter category name or ID",
            required=True
        )
        self.add_item(self.category_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Ticket system configuration is not implemented in database
        await interaction.response.send_message(_("config_system.ticket_system.not_implemented", interaction.user.id, self.guild_id), ephemeral=True)

class TicketSupportRoleModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Set Support Role")
        self.bot = bot
        self.guild_id = guild_id
        
        self.role_input = discord.ui.TextInput(
            label="Role Name or ID",
            placeholder="Enter role name or ID",
            required=True
        )
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Ticket system configuration is not implemented in database
        await interaction.response.send_message(_("config_system.ticket_system.not_implemented", interaction.user.id, self.guild_id), ephemeral=True)

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Config cog initialized")

    @app_commands.command(name="config", description="Configure bot settings")
    async def config(self, interaction: discord.Interaction):
        """Unified configuration command for all bot systems"""
        
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("config_system.no_permission", interaction.user.id, interaction.guild_id),
                ephemeral=True
            )
            return
        
        # Create main config view
        view = ConfigView(self.bot, interaction.guild_id)
        view.setup_select_for_user(interaction.user.id)
        
        embed = discord.Embed(
            title=_("config_system.title", interaction.user.id, interaction.guild_id),
            description=_("config_system.description_text", interaction.user.id, interaction.guild_id),
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
