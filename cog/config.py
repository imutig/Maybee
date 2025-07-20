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
        elif select_value == "ticket_system":
            await self.show_ticket_system_config(interaction)
        elif select_value == "language":
            await self.show_language_config(interaction)
        elif select_value == "server_logs":
            await self.show_server_logs_config(interaction)

    async def show_welcome_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.welcome.title", interaction.user.id, self.guild_id),
            description=_("config_system.welcome.description", interaction.user.id, self.guild_id),
            color=discord.Color.green()
        )
        
        # Get current welcome settings from welcome_config table first
        result = await self.bot.db.query("SELECT welcome_channel, welcome_message FROM welcome_config WHERE guild_id = %s", (self.guild_id,))
        welcome_channel = result[0]["welcome_channel"] if result else None
        welcome_message = result[0]["welcome_message"] if result else None
        
        # If no welcome_config, check guild_config table for dashboard consistency
        if not welcome_channel and not welcome_message:
            guild_result = await self.bot.db.query("SELECT welcome_channel, welcome_message FROM guild_config WHERE guild_id = %s", (self.guild_id,))
            if guild_result:
                welcome_channel = guild_result[0]["welcome_channel"] if guild_result[0]["welcome_channel"] else None
                welcome_message = guild_result[0]["welcome_message"] if guild_result[0]["welcome_message"] else None
        
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
        # Check both xp_config and guild_config for level up channel
        xp_result = await self.bot.db.query("SELECT xp_channel FROM xp_config WHERE guild_id = %s", (self.guild_id,))
        guild_result = await self.bot.db.query("SELECT level_up_channel, level_up_message FROM guild_config WHERE guild_id = %s", (self.guild_id,))
        
        xp_enabled = len(xp_result) > 0 if xp_result else False
        
        # Prefer guild_config level_up_channel over xp_config xp_channel
        level_up_channel = None
        level_up_enabled = True
        
        if guild_result and guild_result[0]:
            level_up_channel = guild_result[0].get("level_up_channel")
            level_up_enabled = guild_result[0].get("level_up_message", True)
        
        if not level_up_channel and xp_result and xp_result[0]:
            level_up_channel = xp_result[0].get("xp_channel")
        
        embed.add_field(
            name=_("config_system.xp_system.current_status", interaction.user.id, self.guild_id),
            value=_("config_system.xp_system.enabled", interaction.user.id, self.guild_id) if xp_enabled else _("config_system.xp_system.disabled", interaction.user.id, self.guild_id),
            inline=False
        )
        
        if level_up_channel:
            channel = self.bot.get_channel(level_up_channel)
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
        
        # Add level up messages status
        embed.add_field(
            name="Level Up Messages",
            value="✅ Enabled" if level_up_enabled else "❌ Disabled",
            inline=True
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

    async def show_server_logs_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("config_system.server_logs.title", interaction.user.id, self.guild_id),
            description=_("config_system.server_logs.description", interaction.user.id, self.guild_id),
            color=discord.Color.orange()
        )
        
        # Get current server logs configuration
        result = await self.bot.db.query(
            "SELECT * FROM server_logs_config WHERE guild_id = %s", 
            (self.guild_id,), 
            fetchone=True
        )
        
        if result:
            log_channel = self.bot.get_channel(result['log_channel_id']) if result['log_channel_id'] else None
            channel_name = log_channel.mention if log_channel else _("config_system.server_logs.not_set", interaction.user.id, self.guild_id)
            
            embed.add_field(
                name=_("config_system.server_logs.current_channel", interaction.user.id, self.guild_id),
                value=channel_name,
                inline=False
            )
            
            # Show enabled/disabled features
            features = []
            if result['log_member_join']:
                features.append("✅ " + _("config_system.server_logs.member_join", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.member_join", interaction.user.id, self.guild_id))
                
            if result['log_member_leave']:
                features.append("✅ " + _("config_system.server_logs.member_leave", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.member_leave", interaction.user.id, self.guild_id))
                
            if result['log_voice_join']:
                features.append("✅ " + _("config_system.server_logs.voice_join", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.voice_join", interaction.user.id, self.guild_id))
                
            if result['log_voice_leave']:
                features.append("✅ " + _("config_system.server_logs.voice_leave", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.voice_leave", interaction.user.id, self.guild_id))
                
            if result['log_message_delete']:
                features.append("✅ " + _("config_system.server_logs.message_delete", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.message_delete", interaction.user.id, self.guild_id))
                
            if result['log_message_edit']:
                features.append("✅ " + _("config_system.server_logs.message_edit", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.message_edit", interaction.user.id, self.guild_id))
                
            if result['log_role_changes']:
                features.append("✅ " + _("config_system.server_logs.role_changes", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.role_changes", interaction.user.id, self.guild_id))
                
            if result['log_nickname_changes']:
                features.append("✅ " + _("config_system.server_logs.nickname_changes", interaction.user.id, self.guild_id))
            else:
                features.append("❌ " + _("config_system.server_logs.nickname_changes", interaction.user.id, self.guild_id))
                
            embed.add_field(
                name=_("config_system.server_logs.features", interaction.user.id, self.guild_id),
                value="\n".join(features),
                inline=False
            )
        else:
            embed.add_field(
                name=_("config_system.server_logs.current_channel", interaction.user.id, self.guild_id),
                value=_("config_system.server_logs.not_configured", interaction.user.id, self.guild_id),
                inline=False
            )
        
        view = ServerLogsConfigView(self.bot, self.guild_id)
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
        # Delete from welcome_config table
        await self.bot.db.query("DELETE FROM welcome_config WHERE guild_id = %s", (self.guild_id,))
        
        # Also update guild_config table for dashboard consistency
        await self.bot.db.query(
            """INSERT INTO guild_config (guild_id, welcome_enabled, updated_at)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE
               welcome_enabled = VALUES(welcome_enabled),
               updated_at = VALUES(updated_at)""",
            (self.guild_id, False, datetime.utcnow())
        )
        
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

class ConfirmResetXPView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Yes, Reset ALL XP", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset all XP data for the server"""
        try:
            # Get count before deletion for feedback
            count_result = await self.bot.db.query(
                'SELECT COUNT(*) as count FROM xp_data WHERE guild_id = %s', 
                (self.guild_id,), 
                fetchone=True
            )
            count = count_result['count'] if count_result else 0
            
            # Delete all XP-related data for the guild
            await self.bot.db.execute('DELETE FROM xp_data WHERE guild_id = %s', (self.guild_id,))
            await self.bot.db.execute('DELETE FROM xp_history WHERE guild_id = %s', (self.guild_id,))
            await self.bot.db.execute('DELETE FROM level_roles WHERE guild_id = %s', (self.guild_id,))
            await self.bot.db.execute('DELETE FROM xp_multipliers WHERE guild_id = %s', (self.guild_id,))
            
            # Also clear guild-specific XP configuration but keep the guild in the system
            # Don't delete from xp_config as it just enables/disables the system
            
            # Clear any cached leaderboard data
            if hasattr(self.bot, 'cache') and hasattr(self.bot.cache, 'invalidate_leaderboard'):
                await self.bot.cache.invalidate_leaderboard(self.guild_id)
            
            await interaction.response.send_message(
                f"✅ **XP Reset Complete!**\n\n"
                f"Successfully deleted:\n"
                f"• {count} user XP records\n"
                f"• All XP history records\n"
                f"• All level role assignments\n\n"
                f"All users will start fresh with 0 XP!",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ **Error resetting XP data:**\n{str(e)[:1000]}",
                ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ **XP reset cancelled.** No data was deleted.",
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
        
        self.toggle_levelup_button = discord.ui.Button(
            label="Toggle Level Up Messages",
            style=discord.ButtonStyle.secondary,
            emoji="📢"
        )
        self.toggle_levelup_button.callback = self.toggle_levelup_messages
        self.add_item(self.toggle_levelup_button)
        
        self.reset_xp_button = discord.ui.Button(
            label="Reset Server XP",
            style=discord.ButtonStyle.danger,
            emoji="🗑️"
        )
        self.reset_xp_button.callback = self.reset_server_xp
        self.add_item(self.reset_xp_button)
    
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
    
    async def toggle_levelup_messages(self, interaction: discord.Interaction):
        """Toggle level up messages on/off and sync with dashboard"""
        # Get current status
        result = await self.bot.db.query("SELECT level_up_message FROM guild_config WHERE guild_id = %s", (self.guild_id,))
        current_status = result[0].get("level_up_message", True) if result and result[0] else True
        
        # Toggle the status
        new_status = not current_status
        
        # Update guild_config table (syncs with dashboard)
        await self.bot.db.query(
            """INSERT INTO guild_config (guild_id, level_up_message, updated_at) 
               VALUES (%s, %s, %s) AS new_values
               ON DUPLICATE KEY UPDATE 
               level_up_message = new_values.level_up_message,
               updated_at = new_values.updated_at""",
            (self.guild_id, new_status, datetime.utcnow())
        )
        
        status_text = "✅ Enabled" if new_status else "❌ Disabled"
        await interaction.response.send_message(f"Level up messages: {status_text}", ephemeral=True)

    async def reset_server_xp(self, interaction: discord.Interaction):
        """Show confirmation dialog for resetting server XP"""
        view = ConfirmResetXPView(self.bot, self.guild_id)
        await interaction.response.send_message(
            "⚠️ **WARNING**: This will permanently delete ALL XP data for this server!\n\n"
            "This includes:\n"
            "• All user XP and levels\n"
            "• XP history records\n"
            "• Level role assignments\n\n"
            "**This action cannot be undone!**\n\n"
            "Are you sure you want to reset all XP data?",
            view=view,
            ephemeral=True
        )

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

class ServerLogsConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="", style=discord.ButtonStyle.primary, emoji="📢")
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.set_channel", interaction.user.id, self.guild_id)
        modal = LogChannelModal(self.bot, self.guild_id, interaction.user.id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def toggle_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.toggle_features", interaction.user.id, self.guild_id)
        view = ServerLogsToggleView(self.bot, self.guild_id, interaction.user.id)
        await interaction.response.send_message(
            _("config_system.server_logs.toggle_features", interaction.user.id, self.guild_id),
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label="Disable Logging", style=discord.ButtonStyle.danger, emoji="🔇")
    async def disable_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.query(
            "UPDATE server_logs_config SET log_channel_id = NULL WHERE guild_id = %s",
            (self.guild_id,)
        )
        
        # Also update guild_config table for dashboard sync
        await self.bot.db.query(
            """INSERT INTO guild_config 
               (guild_id, logs_enabled, logs_channel, updated_at)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               logs_enabled = %s,
               logs_channel = %s,
               updated_at = %s""",
            (self.guild_id, False, None, datetime.utcnow(), False, None, datetime.utcnow())
        )
        
        await interaction.response.send_message(
            _("config_system.server_logs.system_disabled", interaction.user.id, self.guild_id),
            ephemeral=True
        )

class ServerLogsToggleView(discord.ui.View):
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
    
    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="🚪")
    async def toggle_member_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.member_join_leave", interaction.user.id, self.guild_id)
        # Get current settings
        result = await self.bot.db.query(
            "SELECT log_member_join, log_member_leave FROM server_logs_config WHERE guild_id = %s",
            (self.guild_id,),
            fetchone=True
        )
        
        if result:
            # Toggle both join and leave
            new_value = not result['log_member_join']
            await self.bot.db.query(
                "UPDATE server_logs_config SET log_member_join = %s, log_member_leave = %s WHERE guild_id = %s",
                (new_value, new_value, self.guild_id)
            )
            
            # Also update guild_config for dashboard sync
            await self.bot.db.query(
                """INSERT INTO guild_config 
                   (guild_id, logs_enabled, updated_at)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   logs_enabled = %s,
                   updated_at = %s""",
                (self.guild_id, new_value, datetime.utcnow(), new_value, datetime.utcnow())
            )
            
            status = _("config_system.server_logs.feature_enabled", interaction.user.id, self.guild_id) if new_value else _("config_system.server_logs.feature_disabled", interaction.user.id, self.guild_id)
            await interaction.response.send_message(
                f"{_('config_system.server_logs.member_events', interaction.user.id, self.guild_id)} {status}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                _("config_system.server_logs.configure_first", interaction.user.id, self.guild_id),
                ephemeral=True
            )
    
    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="🔊")
    async def toggle_voice_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.voice_events", interaction.user.id, self.guild_id)
        result = await self.bot.db.query(
            "SELECT log_voice_join, log_voice_leave FROM server_logs_config WHERE guild_id = %s",
            (self.guild_id,),
            fetchone=True
        )
        
        if result:
            new_value = not result['log_voice_join']
            await self.bot.db.query(
                "UPDATE server_logs_config SET log_voice_join = %s, log_voice_leave = %s WHERE guild_id = %s",
                (new_value, new_value, self.guild_id)
            )
            
            # Also update guild_config for dashboard sync
            await self.bot.db.query(
                """INSERT INTO guild_config 
                   (guild_id, logs_enabled, updated_at)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   logs_enabled = %s,
                   updated_at = %s""",
                (self.guild_id, new_value, datetime.utcnow(), new_value, datetime.utcnow())
            )
            
            status = _("config_system.server_logs.feature_enabled", interaction.user.id, self.guild_id) if new_value else _("config_system.server_logs.feature_disabled", interaction.user.id, self.guild_id)
            await interaction.response.send_message(
                f"{_('config_system.server_logs.voice_events', interaction.user.id, self.guild_id)} {status}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                _("config_system.server_logs.configure_first", interaction.user.id, self.guild_id),
                ephemeral=True
            )
    
    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="💬")
    async def toggle_message_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.message_events", interaction.user.id, self.guild_id)
        result = await self.bot.db.query(
            "SELECT log_message_delete, log_message_edit FROM server_logs_config WHERE guild_id = %s",
            (self.guild_id,),
            fetchone=True
        )
        
        if result:
            new_value = not result['log_message_delete']
            await self.bot.db.query(
                "UPDATE server_logs_config SET log_message_delete = %s, log_message_edit = %s WHERE guild_id = %s",
                (new_value, new_value, self.guild_id)
            )
            
            # Also update guild_config for dashboard sync
            await self.bot.db.query(
                """INSERT INTO guild_config 
                   (guild_id, logs_enabled, updated_at)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   logs_enabled = %s,
                   updated_at = %s""",
                (self.guild_id, new_value, datetime.utcnow(), new_value, datetime.utcnow())
            )
            
            status = _("config_system.server_logs.feature_enabled", interaction.user.id, self.guild_id) if new_value else _("config_system.server_logs.feature_disabled", interaction.user.id, self.guild_id)
            await interaction.response.send_message(
                f"{_('config_system.server_logs.message_events', interaction.user.id, self.guild_id)} {status}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                _("config_system.server_logs.configure_first", interaction.user.id, self.guild_id),
                ephemeral=True
            )
    
    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="🔧")
    async def toggle_other_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("config_system.server_logs.button_labels.other_events", interaction.user.id, self.guild_id)
        result = await self.bot.db.query(
            "SELECT log_role_changes, log_nickname_changes FROM server_logs_config WHERE guild_id = %s",
            (self.guild_id,),
            fetchone=True
        )
        
        if result:
            new_value = not result['log_role_changes']
            await self.bot.db.query(
                "UPDATE server_logs_config SET log_role_changes = %s, log_nickname_changes = %s WHERE guild_id = %s",
                (new_value, new_value, self.guild_id)
            )
            
            # Also update guild_config for dashboard sync
            await self.bot.db.query(
                """INSERT INTO guild_config 
                   (guild_id, logs_enabled, updated_at)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   logs_enabled = %s,
                   updated_at = %s""",
                (self.guild_id, new_value, datetime.utcnow(), new_value, datetime.utcnow())
            )
            
            status = _("config_system.server_logs.feature_enabled", interaction.user.id, self.guild_id) if new_value else _("config_system.server_logs.feature_disabled", interaction.user.id, self.guild_id)
            await interaction.response.send_message(
                f"{_('config_system.server_logs.other_events', interaction.user.id, self.guild_id)} {status}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                _("config_system.server_logs.configure_first", interaction.user.id, self.guild_id),
                ephemeral=True
            )

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
        
        # Update welcome_config table
        await self.bot.db.query("INSERT INTO welcome_config (guild_id, welcome_channel) VALUES (%s, %s) ON DUPLICATE KEY UPDATE welcome_channel = %s", (self.guild_id, channel.id, channel.id))
        
        # Also update guild_config table for dashboard consistency
        await self.bot.db.query(
            """INSERT INTO guild_config (guild_id, welcome_enabled, welcome_channel, updated_at)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               welcome_enabled = VALUES(welcome_enabled),
               welcome_channel = VALUES(welcome_channel),
               updated_at = VALUES(updated_at)""",
            (self.guild_id, True, channel.id, datetime.utcnow())
        )
        
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
        
        # Update welcome_config table
        await self.bot.db.query("INSERT INTO welcome_config (guild_id, welcome_message) VALUES (%s, %s) ON DUPLICATE KEY UPDATE welcome_message = %s", (self.guild_id, message, message))
        
        # Also update guild_config table for dashboard consistency
        await self.bot.db.query(
            """INSERT INTO guild_config (guild_id, welcome_enabled, welcome_message, updated_at)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               welcome_enabled = VALUES(welcome_enabled),
               welcome_message = VALUES(welcome_message),
               updated_at = VALUES(updated_at)""",
            (self.guild_id, True, message, datetime.utcnow())
        )
        
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
        
        # Update xp_config table for legacy compatibility
        await self.bot.db.query("INSERT INTO xp_config (guild_id, xp_channel) VALUES (%s, %s) ON DUPLICATE KEY UPDATE xp_channel = %s", (self.guild_id, channel.id, channel.id))
        
        # Also update guild_config table for dashboard sync
        await self.bot.db.query(
            """INSERT INTO guild_config (guild_id, level_up_channel, level_up_message, updated_at) 
               VALUES (%s, %s, TRUE, %s) AS new_values
               ON DUPLICATE KEY UPDATE 
               level_up_channel = new_values.level_up_channel,
               level_up_message = new_values.level_up_message,
               updated_at = new_values.updated_at""",
            (self.guild_id, channel.id, datetime.utcnow())
        )
        
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

class LogChannelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(title=_("config_system.server_logs.modal_titles.set_log_channel", user_id, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        
        self.channel_input = discord.ui.TextInput(
            label=_("config_system.server_logs.modal_labels.channel_id_or_name", user_id, guild_id),
            placeholder=_("config_system.server_logs.modal_labels.channel_placeholder", user_id, guild_id),
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
            await interaction.response.send_message(
                _("config_system.server_logs.channel_not_found", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Check if channel is a text channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                _("config_system.server_logs.invalid_channel_type", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Insert or update the server logs configuration
        await self.bot.db.query(
            """INSERT INTO server_logs_config (guild_id, log_channel_id) 
               VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE log_channel_id = %s""",
            (self.guild_id, channel.id, channel.id)
        )
        
        # Also update guild_config table for dashboard sync
        await self.bot.db.query(
            """INSERT INTO guild_config 
               (guild_id, logs_enabled, logs_channel, updated_at)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               logs_enabled = %s,
               logs_channel = %s,
               updated_at = %s""",
            (self.guild_id, True, channel.id, datetime.utcnow(), True, channel.id, datetime.utcnow())
        )
        
        await interaction.response.send_message(
            _("config_system.server_logs.channel_set", interaction.user.id, self.guild_id).format(channel=channel.mention),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
