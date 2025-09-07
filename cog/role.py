import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button

class RoleRequestView(View):
    def __init__(self, bot, user_id, role_id, action, message_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.role_id = role_id
        self.action = action
        self.message_id = message_id

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            from i18n import _
            from .command_logger import log_command_usage
            user_id = interaction.user.id
            guild_id = interaction.guild.id if interaction.guild else None
            await interaction.response.send_message(
                _("errors.admin_only", user_id, guild_id), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accepter", style=ButtonStyle.green, custom_id="role_accept")
    async def accept_button(self, interaction: Interaction, button: Button):
        from i18n import _
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        role = guild.get_role(self.role_id)

        if not member or not role:
            await interaction.response.send_message(
                _("role_requests.member_role_not_found", user_id, guild_id), ephemeral=True)
            return

        try:
            if self.action == "add":
                await member.add_roles(role)
                action_done = _("role_requests.action_added", user_id, guild_id)
            else:
                await member.remove_roles(role)
                action_done = _("role_requests.action_removed", user_id, guild_id)
        except Exception as e:
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id), ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(
            name=_("role_requests.status_field", user_id, guild_id), 
            value=_("role_requests.accepted_by", user_id, guild_id, user=interaction.user.mention), 
            inline=False
        )
        embed.add_field(
            name=_("role_requests.action_performed", user_id, guild_id), 
            value=_("role_requests.role_action_result", user_id, guild_id, role=role.name, action=action_done, member=member.mention), 
            inline=False
        )

        await interaction.response.edit_message(content=None, embed=embed, view=None)

        # Update database
        cog = self.bot.get_cog("RoleRequest")
        if cog:
            await cog.update_request_status(self.message_id, "approved")

    @discord.ui.button(label="Refuser", style=ButtonStyle.red, custom_id="role_deny")
    async def deny_button(self, interaction: Interaction, button: Button):
        from i18n import _
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        role = guild.get_role(self.role_id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(
            name=_("role_requests.status_field", user_id, guild_id), 
            value=_("role_requests.denied_by", user_id, guild_id, user=interaction.user.mention), 
            inline=False
        )

        await interaction.response.edit_message(content=None, embed=embed, view=None)

        # Update database
        cog = self.bot.get_cog("RoleRequest")
        if cog:
            await cog.update_request_status(self.message_id, "denied")


class RoleRequest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def save_role_request(self, message_id, user_id, role_id, action, guild_id):
        """Save a role request to the database"""
        await self.db.query(
            "INSERT INTO role_requests (message_id, user_id, role_id, action, guild_id) VALUES (%s, %s, %s, %s, %s)",
            (message_id, user_id, role_id, action, guild_id)
        )

    async def update_request_status(self, message_id, status):
        """Update the status of a role request"""
        await self.db.query(
            "UPDATE role_requests SET status = %s WHERE message_id = %s",
            (status, message_id)
        )

    async def get_pending_requests(self, guild_id):
        """Get all pending role requests for a guild"""
        result = await self.db.query(
            "SELECT * FROM role_requests WHERE guild_id = %s AND status = 'pending'",
            (guild_id,),
            fetchall=True
        )
        return result if result else []

    async def get_role_request_channel(self, guild_id):
        """Get role request channel for a guild"""
        # Check if there's a configured channel in database
        result = await self.db.query(
            "SELECT channel_id FROM role_request_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        if result:
            return result['channel_id']
        
        # Fallback to hardcoded channel ID
        return 1393935449944227931

    async def set_role_request_channel(self, guild_id, channel_id):
        """Set role request channel for a guild"""
        await self.db.query(
            "INSERT INTO role_request_config (guild_id, channel_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE channel_id = %s",
            (guild_id, channel_id, channel_id)
        )

    # Role commands removed - use role menus instead

    async def handle_request(self, interaction: Interaction, role: discord.Role, action: str):
        from i18n import _
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                _("role_requests.role_too_high", user_id, guild_id), ephemeral=True)
            return

        verb = _("role_requests.action_add", user_id, guild_id) if action == "add" else _("role_requests.action_remove", user_id, guild_id)
        embed = discord.Embed(
            title=_("role_requests.embed_title", user_id, guild_id),
            description=_("role_requests.embed_description", user_id, guild_id, user=interaction.user.mention, action=verb, role=role.mention),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=_("role_requests.embed_footer", user_id, guild_id, user_id=interaction.user.id, role_id=role.id))

        view = RoleRequestView(self.bot, user_id=interaction.user.id, role_id=role.id, action=action)

        channel_id = await self.get_role_request_channel(interaction.guild.id)
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                _("role_requests.channel_not_found", user_id, guild_id), ephemeral=True)
            return

        message = await channel.send(embed=embed, view=view)
        view.message_id = message.id

        # Save request to database
        await self.save_role_request(message.id, interaction.user.id, role.id, action, interaction.guild.id)

        await interaction.response.send_message(
            _("role_requests.request_sent", user_id, guild_id, action=verb, channel=channel.mention),
            ephemeral=True)

    # Configuration command removed - use unified /config command instead
    # @app_commands.command(name="configrolechannel", description="Configure le canal pour les demandes de rôles")
    # @app_commands.describe(channel="Le canal où envoyer les demandes de rôles")
    # async def configrolechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
    #     if not interaction.user.guild_permissions.manage_channels:
    #         await interaction.response.send_message(
    #             "Vous n'avez pas la permission de gérer les canaux.", ephemeral=True)
    #         return

    #     guild_id = interaction.guild.id
    #     await self.set_role_request_channel(guild_id, channel.id)
    #     await interaction.response.send_message(
    #         f"Canal des demandes de rôles configuré sur {channel.mention}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        """Restore role request views on bot startup"""
        for guild in self.bot.guilds:
            pending_requests = await self.get_pending_requests(guild.id)
            channel_id = await self.get_role_request_channel(guild.id)
            channel = guild.get_channel(channel_id)
            
            if not channel:
                continue
                
            for request in pending_requests:
                try:
                    message = await channel.fetch_message(request['message_id'])
                    view = RoleRequestView(
                        self.bot,
                        user_id=request['user_id'],
                        role_id=request['role_id'],
                        action=request['action'],
                        message_id=request['message_id']
                    )
                    await message.edit(view=view)
                except Exception as e:
                    print(f"[ERREUR] Impossible de restaurer la demande {request['message_id']}: {e}")

async def setup(bot):
    await bot.add_cog(RoleRequest(bot))
