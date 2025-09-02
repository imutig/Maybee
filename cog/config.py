import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from datetime import datetime
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
        """Cr    @discord.ui.button(label="", style=discord.ButtonStyle.danger, emoji="🔇")
    async def disable_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.disable_logging", interaction.user.id, self.guild_id)
        await self.bot.db.query(
            "UPDATE server_logs_config SET log_channel_id = NULL WHERE guild_id = %s",
            (self.guild_id,)
        )
        await interaction.response.send_message(
            _("config_system.server_logs.disabled", interaction.user.id, self.guild_id),
            ephemeral=True
        )t options with user's language preference"""
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
        elif select_value == "role_requests":
            await self.show_role_requests_config(interaction)
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
            title=_("config_system.welcome.title", interaction.user.id, self.guild_id),
            description="🌐 **Use the Web Dashboard**\n\nThe welcome system is now fully managed through the web dashboard for a better experience.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🔗 Access Dashboard",
            value="Visit the web dashboard to configure:\n• Welcome channel selection\n• Welcome message content\n• Custom embed settings\n• Enable/disable welcome system",
            inline=False
        )
        
        embed.add_field(
            name="💡 Why use the dashboard?",
            value="• User-friendly interface\n• Better form validation\n• Persistent settings storage\n• Easy configuration management",
            inline=False
        )
        
        view = DashboardRedirectView("welcome")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_confession_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.confession.title", interaction.user.id, self.guild_id),
            description=_("config_system.confession.description", interaction.user.id, self.guild_id),
            color=discord.Color.purple()
        )
        
        # Get current confession settings
        result = await self.bot.db.query("SELECT channel_id FROM confession_config WHERE guild_id = %s", (self.guild_id,), fetchone=True)
        confession_channel = result["channel_id"] if result else None
        
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
        result = await self.bot.db.query("SELECT channel_id FROM role_request_config WHERE guild_id = %s", (self.guild_id,), fetchone=True)
        role_request_channel = result["channel_id"] if result else None
        
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
            description="🌐 **Use the Web Dashboard**\n\nThe XP system is now fully managed through the web dashboard for advanced features.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔗 Dashboard Features",
            value="• XP system enable/disable\n• Level-up channel configuration\n• Level-up message settings\n• XP multipliers\n• **Reset server XP data**\n• Advanced leaderboards",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ XP Reset",
            value="XP reset functionality has been moved to the dashboard for safety.\nThis prevents accidental data loss.",
            inline=False
        )
        
        view = DashboardRedirectView("xp_system")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_language_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.language.title", interaction.user.id, self.guild_id),
            description=_("config_system.language.description", interaction.user.id, self.guild_id),
            color=discord.Color.blurple()
        )
        
        # Get current language
        result = await self.bot.db.query("SELECT language_code FROM guild_languages WHERE guild_id = %s", (self.guild_id,), fetchone=True)
        current_language = result["language_code"] if result else "en"
        
        embed.add_field(
            name=_("config_system.language.current_language", interaction.user.id, self.guild_id),
            value=_("config_system.language.english", interaction.user.id, self.guild_id) if current_language == "en" else _("config_system.language.french", interaction.user.id, self.guild_id),
            inline=False
        )
        
        view = LanguageConfigView(self.bot, self.guild_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def show_server_logs_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.server_logs.title", interaction.user.id, self.guild_id),
            description="🌐 **Use the Web Dashboard**\n\nServer logs are now fully managed through the web dashboard with advanced options.",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="🔗 Dashboard Features",
            value="• Log channel configuration\n• Individual event toggles\n• Message delete/edit logs\n• Member join/leave logs\n• Voice activity logs\n• Role & nickname changes\n• Real-time settings preview",
            inline=False
        )
        
        embed.add_field(
            name="✨ Enhanced Features",
            value="• Filter by user/channel\n• Log message formatting\n• Bulk configuration\n• Export log data",
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
            title="🌐 Web Dashboard Access",
            description=f"Configure your {self.system_name.replace('_', ' ').title()} settings on the web dashboard:",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="📱 Dashboard URL",
            value="[Click here to access the dashboard](https://web-production-448ba.up.railway.app/)",
            inline=False
        )
        
        embed.add_field(
            name="🔐 Login",
            value="Use your Discord account to log in and manage your server settings.",
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
    
    @discord.ui.button(label="Configure Role Reactions", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def configure_role_reactions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            _("config_system.role_reactions.use_command_button", interaction.user.id, self.guild_id) + "\n\n" +
            "💡 **Tip:** Type `/rolereact` to access the full role reaction management interface!",
            ephemeral=True
        )
    
    @discord.ui.button(label="View Current Setup", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_current_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get current role reactions from database
        result = await self.bot.db.query("SELECT * FROM role_reactions WHERE guild_id = %s ORDER BY message_id", (self.guild_id,))
        
        if not result:
            await interaction.response.send_message(
                _("config_system.role_reactions.no_reactions_found", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Group by message_id to show organized info
        messages = {}
        for row in result:
            message_id = row['message_id']
            if message_id not in messages:
                messages[message_id] = []
            messages[message_id].append(row)
        
        embed = discord.Embed(
            title=_("config_system.role_reactions.current_setup_title", interaction.user.id, self.guild_id),
            color=discord.Color.blue()
        )
        
        for message_id, reactions in messages.items():
            # Try to get the message
            message = None
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(message_id)
                    break
                except:
                    continue
            
            message_info = f"Message ID: {message_id}"
            if message:
                message_info += f"\nChannel: {message.channel.mention}"
                if len(message.content) > 100:
                    message_info += f"\nContent: {message.content[:100]}..."
                else:
                    message_info += f"\nContent: {message.content}"
            
            reactions_list = []
            for reaction in reactions:
                role = interaction.guild.get_role(reaction['role_id'])
                if role:
                    reactions_list.append(f"{reaction['emoji']} → {role.mention}")
                else:
                    reactions_list.append(f"{reaction['emoji']} → Role not found (ID: {reaction['role_id']})")
            
            embed.add_field(
                name=f"📝 {message_info}",
                value="\n".join(reactions_list) if reactions_list else "No valid reactions",
                inline=False
            )
        
        if len(embed.fields) == 0:
            embed.add_field(
                name="No Active Role Reactions",
                value="Use `/rolereact` to set up role reactions!",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Clear All", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_all_reactions(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Confirm before clearing
        view = ConfirmClearView(self.bot, self.guild_id)
        await interaction.response.send_message(
            _("config_system.role_reactions.confirm_clear", interaction.user.id, self.guild_id),
            view=view,
            ephemeral=True
        )

class ConfirmClearView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Yes, Clear All", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query("DELETE FROM role_reactions WHERE guild_id = %s", (self.guild_id,))
        await interaction.response.send_message(
            _("config_system.role_reactions.cleared_all", interaction.user.id, self.guild_id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            _("config_system.role_reactions.clear_cancelled", interaction.user.id, self.guild_id),
            ephemeral=True
        )

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
