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
        
        # Create select options with translations
        self.select_options = [
            discord.SelectOption(
                label=_("config_system.welcome.title", 0, guild_id).replace("🎉 ", ""),
                value="welcome",
                description=_("config_system.welcome.description", 0, guild_id),
                emoji="👋"
            ),
            discord.SelectOption(
                label=_("config_system.confession.title", 0, guild_id).replace("💬 ", ""),
                value="confession",
                description=_("config_system.confession.description", 0, guild_id),
                emoji="🔒"
            ),
            discord.SelectOption(
                label=_("config_system.role_requests.title", 0, guild_id).replace("🎭 ", ""),
                value="role_requests",
                description=_("config_system.role_requests.description", 0, guild_id),
                emoji="📋"
            ),
            discord.SelectOption(
                label=_("config_system.role_reactions.title", 0, guild_id).replace("⚡ ", ""),
                value="role_reactions",
                description=_("config_system.role_reactions.description", 0, guild_id),
                emoji="⚡"
            ),
            discord.SelectOption(
                label=_("config_system.xp_system.title", 0, guild_id).replace("📊 ", ""),
                value="xp_system",
                description=_("config_system.xp_system.description", 0, guild_id),
                emoji="⬆️"
            ),
            discord.SelectOption(
                label=_("config_system.ticket_system.title", 0, guild_id).replace("🎫 ", ""),
                value="ticket_system",
                description=_("config_system.ticket_system.description", 0, guild_id),
                emoji="🔧"
            ),
            discord.SelectOption(
                label=_("config_system.language.title", 0, guild_id).replace("🌍 ", ""),
                value="language",
                description=_("config_system.language.description", 0, guild_id),
                emoji="🗣️"
            )
        ]
        
        # Create the select component
        self.config_select = discord.ui.Select(
            placeholder=_("config_system.select_placeholder", 0, guild_id),
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
        
        view = RoleReactionsConfigView(self.bot, self.guild_id)
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
        xp_rate = 1.0  # Default rate since there's no rate configuration in the database
        
        embed.add_field(
            name=_("config_system.xp_system.current_status", interaction.user.id, self.guild_id),
            value=_("config_system.xp_system.enabled", interaction.user.id, self.guild_id) if xp_enabled else _("config_system.xp_system.disabled", interaction.user.id, self.guild_id),
            inline=False
        )
        
        if xp_enabled:
            embed.add_field(
                name=_("config_system.xp_system.current_rate", interaction.user.id, self.guild_id),
                value=str(xp_rate),
                inline=False
            )
        
        view = XPSystemConfigView(self.bot, self.guild_id)
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

class RoleReactionsConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Add Reaction", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_role_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RoleReactionModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove All", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_all_reactions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query("DELETE FROM role_reactions WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(_("config_system.role_reactions.removed_all", interaction.user.id, self.guild_id), ephemeral=True)

class XPSystemConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Enable", style=discord.ButtonStyle.success, emoji="✅")
    async def enable_xp_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Enable XP system by ensuring there's a config entry
        await self.bot.db.query("INSERT INTO xp_config (guild_id) VALUES (%s) ON DUPLICATE KEY UPDATE guild_id = guild_id", (self.guild_id,))
        await interaction.response.send_message(_("config_system.xp_system.enabled_success", interaction.user.id, self.guild_id), ephemeral=True)
    
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="❌")
    async def disable_xp_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Disable XP system by removing config entry
        await self.bot.db.query("DELETE FROM xp_config WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(_("config_system.xp_system.disabled_success", interaction.user.id, self.guild_id), ephemeral=True)
    
    @discord.ui.button(label="Set Rate", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def set_xp_rate(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await self.bot.db.query("INSERT INTO guild_languages (guild_id, language_code) VALUES (%s, 'en') ON DUPLICATE KEY UPDATE language_code = 'en'", (self.guild_id,))
        await interaction.response.send_message(_("config_system.language.changed_to_english", interaction.user.id, self.guild_id), ephemeral=True)
    
    @discord.ui.button(label="Français", style=discord.ButtonStyle.primary, emoji="🇫🇷")
    async def set_french(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query("INSERT INTO guild_languages (guild_id, language_code) VALUES (%s, 'fr') ON DUPLICATE KEY UPDATE language_code = 'fr'", (self.guild_id,))
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

class RoleReactionModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title="Add Role Reaction")
        self.bot = bot
        self.guild_id = guild_id
        
        self.emoji_input = discord.ui.TextInput(
            label="Emoji",
            placeholder="Enter emoji (e.g., 🎮 or :emoji_name:)",
            required=True
        )
        self.role_input = discord.ui.TextInput(
            label="Role",
            placeholder="Enter role name or ID",
            required=True
        )
        self.add_item(self.emoji_input)
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        emoji = self.emoji_input.value.strip()
        role_input = self.role_input.value.strip()
        
        # Try to find the role
        role = None
        if role_input.startswith('<@&') and role_input.endswith('>'):
            role_id = int(role_input[3:-1])
            role = interaction.guild.get_role(role_id)
        elif role_input.isdigit():
            role = interaction.guild.get_role(int(role_input))
        else:
            role = discord.utils.get(interaction.guild.roles, name=role_input)
        
        if not role:
            await interaction.response.send_message(_("config_system.role_reactions.role_not_found", interaction.user.id, self.guild_id), ephemeral=True)
            return
        
        await self.bot.db.query("INSERT INTO role_reactions (guild_id, emoji, role_id) VALUES (%s, %s, %s)", (self.guild_id, emoji, role.id))
        await interaction.response.send_message(_("config_system.role_reactions.added", interaction.user.id, self.guild_id, emoji=emoji, role=role.name), ephemeral=True)

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
        embed = discord.Embed(
            title=_("config_system.title", interaction.user.id, interaction.guild_id),
            description=_("config_system.description_text", interaction.user.id, interaction.guild_id),
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
