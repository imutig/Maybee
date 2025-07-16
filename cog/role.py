import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button

class RoleRequest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def save_role_request(self, message_id, user_id, role_id, action, guild_id):
        await self.db.query(
            "INSERT INTO role_requests (message_id, user_id, role_id, action, guild_id) VALUES (%s, %s, %s, %s, %s)",
            (message_id, user_id, role_id, action, guild_id)
        )

    async def update_request_status(self, message_id, status):
        await self.db.query(
            "UPDATE role_requests SET status = %s WHERE message_id = %s",
            (status, message_id)
        )

    async def get_role_config(self, guild_id):
        result = await self.db.query(
            "SELECT * FROM role_request_config WHERE guild_id = %s",
            (guild_id,)
        )
        return result[0] if result else None

    async def save_role_config(self, guild_id, channel_id, log_channel_id=None, allowed_roles=None):
        await self.db.query(
            "INSERT INTO role_request_config (guild_id, channel_id, log_channel_id, allowed_roles) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE channel_id = %s, log_channel_id = %s, allowed_roles = %s",
            (guild_id, channel_id, log_channel_id, allowed_roles, channel_id, log_channel_id, allowed_roles)
        )

    @app_commands.command(name="request_role", description="Request a role from the available roles")
    async def request_role(self, interaction: Interaction, role: discord.Role):
        # Check if user already has the role
        if role in interaction.user.roles:
            await interaction.response.send_message(f"You already have the {role.name} role!", ephemeral=True)
            return

        # Check if role exists in allowed roles
        config = await self.get_role_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("Role requests are not configured for this server!", ephemeral=True)
            return

        allowed_roles = config.get('allowed_roles', '').split(',') if config.get('allowed_roles') else []
        if allowed_roles and str(role.id) not in allowed_roles:
            await interaction.response.send_message(f"The {role.name} role is not available for requests!", ephemeral=True)
            return

        # Create embed for role request
        embed = discord.Embed(
            title="Role Request",
            description=f"{interaction.user.mention} is requesting the {role.mention} role",
            color=discord.Color.blue()
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="User ID", value=interaction.user.id, inline=True)
        embed.set_footer(text=f"Requested at {discord.utils.format_dt(discord.utils.utcnow())}")

        # Create view with approve/deny buttons
        view = RoleRequestView(self, interaction.user, role)
        
        # Send message to configured channel
        channel = self.bot.get_channel(config['channel_id'])
        if channel:
            message = await channel.send(embed=embed, view=view)
            
            # Save request to database
            await self.save_role_request(message.id, interaction.user.id, role.id, "add", interaction.guild.id)
            
            await interaction.response.send_message(f"Your request for the {role.name} role has been submitted!", ephemeral=True)
        else:
            await interaction.response.send_message("Role request channel not found!", ephemeral=True)

    @app_commands.command(name="remove_role", description="Request to remove a role you have")
    async def remove_role(self, interaction: Interaction, role: discord.Role):
        # Check if user has the role
        if role not in interaction.user.roles:
            await interaction.response.send_message(f"You don't have the {role.name} role!", ephemeral=True)
            return

        # Check if role exists in allowed roles
        config = await self.get_role_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("Role requests are not configured for this server!", ephemeral=True)
            return

        allowed_roles = config.get('allowed_roles', '').split(',') if config.get('allowed_roles') else []
        if allowed_roles and str(role.id) not in allowed_roles:
            await interaction.response.send_message(f"The {role.name} role is not available for removal requests!", ephemeral=True)
            return

        # Create embed for role removal request
        embed = discord.Embed(
            title="Role Removal Request",
            description=f"{interaction.user.mention} is requesting to remove the {role.mention} role",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="User ID", value=interaction.user.id, inline=True)
        embed.set_footer(text=f"Requested at {discord.utils.format_dt(discord.utils.utcnow())}")

        # Create view with approve/deny buttons
        view = RoleRequestView(self, interaction.user, role, action="remove")
        
        # Send message to configured channel
        channel = self.bot.get_channel(config['channel_id'])
        if channel:
            message = await channel.send(embed=embed, view=view)
            
            # Save request to database
            await self.save_role_request(message.id, interaction.user.id, role.id, "remove", interaction.guild.id)
            
            await interaction.response.send_message(f"Your request to remove the {role.name} role has been submitted!", ephemeral=True)
        else:
            await interaction.response.send_message("Role request channel not found!", ephemeral=True)

    @app_commands.command(name="configrole", description="Configure role request settings")
    @app_commands.describe(
        channel="Channel where role requests will be sent",
        log_channel="Channel where role request logs will be sent",
        allowed_roles="Comma-separated list of role IDs that can be requested"
    )
    async def config_role(self, interaction: Interaction, channel: discord.TextChannel, log_channel: discord.TextChannel = None, allowed_roles: str = None):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You don't have permission to configure role requests!", ephemeral=True)
            return

        # Save configuration
        await self.save_role_config(
            interaction.guild.id,
            channel.id,
            log_channel.id if log_channel else None,
            allowed_roles
        )

        embed = discord.Embed(
            title="Role Request Configuration",
            description="Role request system has been configured!",
            color=discord.Color.green()
        )
        embed.add_field(name="Request Channel", value=channel.mention, inline=True)
        if log_channel:
            embed.add_field(name="Log Channel", value=log_channel.mention, inline=True)
        if allowed_roles:
            embed.add_field(name="Allowed Roles", value=allowed_roles, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

class RoleRequestView(View):
    def __init__(self, cog, user, role, action="add"):
        super().__init__(timeout=None)
        self.cog = cog
        self.user = user
        self.role = role
        self.action = action

    @discord.ui.button(label="Approve", style=ButtonStyle.green, emoji="✅")
    async def approve_request(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You don't have permission to approve role requests!", ephemeral=True)
            return

        try:
            if self.action == "add":
                await self.user.add_roles(self.role)
                action_text = "added to"
            else:
                await self.user.remove_roles(self.role)
                action_text = "removed from"

            # Update request status
            await self.cog.update_request_status(interaction.message.id, "approved")

            # Update embed
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="Status", value=f"✅ Approved by {interaction.user.mention}", inline=False)

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

            # Send log message
            config = await self.cog.get_role_config(interaction.guild.id)
            if config and config.get('log_channel_id'):
                log_channel = self.cog.bot.get_channel(config['log_channel_id'])
                if log_channel:
                    log_embed = discord.Embed(
                        title="Role Request Approved",
                        description=f"Role {self.role.mention} was {action_text} {self.user.mention}",
                        color=discord.Color.green()
                    )
                    log_embed.add_field(name="Approved by", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="Action", value=action_text.title(), inline=True)
                    await log_channel.send(embed=log_embed)

        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to {self.action} role: {e}", ephemeral=True)

    @discord.ui.button(label="Deny", style=ButtonStyle.red, emoji="❌")
    async def deny_request(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You don't have permission to deny role requests!", ephemeral=True)
            return

        # Update request status
        await self.cog.update_request_status(interaction.message.id, "denied")

        # Update embed
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"❌ Denied by {interaction.user.mention}", inline=False)

        # Disable buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        # Send log message
        config = await self.cog.get_role_config(interaction.guild.id)
        if config and config.get('log_channel_id'):
            log_channel = self.cog.bot.get_channel(config['log_channel_id'])
            if log_channel:
                log_embed = discord.Embed(
                    title="Role Request Denied",
                    description=f"Role {self.role.mention} request for {self.user.mention} was denied",
                    color=discord.Color.red()
                )
                log_embed.add_field(name="Denied by", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="Action", value=self.action.title(), inline=True)
                await log_channel.send(embed=log_embed)

async def setup(bot):
    await bot.add_cog(RoleRequest(bot))
