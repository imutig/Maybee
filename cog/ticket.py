import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from i18n import _


class Ticket(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_ticket",
                          description="Configure le système de ticket.")
    async def setup_ticket(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        guild = interaction.guild
        category = await guild.create_category(_("ticket_system.category_name", user_id, guild_id))
        ticket_channel = await guild.create_text_channel(
            _("ticket_system.general_channel", user_id, guild_id),
            category=category
        )
        await interaction.response.send_message(
            _("ticket_system.setup_success", user_id, guild_id, category=category.name),
            ephemeral=True)

    @app_commands.command(name="setup_ticket_panel",
                          description="Créer le panel de ticket")
    async def setup_ticket_panel(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        embed = discord.Embed(
            title=_("ticket_system.panel_title", user_id, guild_id),
            description=_("ticket_system.panel_description", user_id, guild_id),
            color=discord.Color.green())
        view = TicketPanelView()
        await interaction.response.send_message(embed=embed, view=view)


class TicketCreateButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Créer un ticket",
                         custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name=_("ticket_system.category_name", user_id, guild_id))
        if not category:
            await interaction.response.send_message(
                _("ticket_system.category_not_found", user_id, guild_id), ephemeral=True)
            return

        existing = discord.utils.get(category.channels,
                                     name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                _("ticket_system.ticket_exists", user_id, guild_id), ephemeral=True)
            return

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(view_channel=False),
            user:
            discord.PermissionOverwrite(view_channel=True,
                                        send_messages=True,
                                        read_message_history=True),
            guild.me:
            discord.PermissionOverwrite(view_channel=True)
        }
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            overwrites=overwrites,
            category=category,
            reason=_("ticket_system.creation_reason", user_id, guild_id))
        embed = discord.Embed(
            title=_("ticket_system.ticket_title", user_id, guild_id),
            description=_("ticket_system.ticket_description", user_id, guild_id, user=user.mention),
            color=discord.Color.blue())
        view = TicketCloseView()
        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            _("ticket_system.ticket_created", user_id, guild_id, channel=channel.mention), ephemeral=True)


class TicketCloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red,
                         label="Fermer le ticket",
                         custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        channel = interaction.channel
        await interaction.response.send_message(
            _("ticket_system.closing_message", user_id, guild_id), ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete(reason=_("ticket_system.close_reason", user_id, guild_id, user=interaction.user))


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())


class TicketCloseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())


async def setup(bot):
    await bot.add_cog(Ticket(bot))
