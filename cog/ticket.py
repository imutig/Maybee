import discord
from discord import app_commands
from discord.ext import commands
import asyncio


class Ticket(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_ticket",
                          description="Configure le système de ticket.")
    async def setup_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = await guild.create_category("Tickets 🔖")
        ticket_channel = await guild.create_text_channel("général-tickets",
                                                         category=category)
        await interaction.response.send_message(
            f"Système de ticket configuré dans {category.name} !",
            ephemeral=True)

    @app_commands.command(name="setup_ticket_panel",
                          description="Créer le panel de ticket")
    async def setup_ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Support Tickets",
            description="Clique sur le bouton ci-dessous pour créer un ticket.",
            color=discord.Color.green())
        view = TicketPanelView()
        await interaction.response.send_message(embed=embed, view=view)


class TicketCreateButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Créer un ticket",
                         custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name="Tickets 🔖")
        if not category:
            await interaction.response.send_message(
                "❌ La catégorie des tickets n'a pas encore été créée. Merci d'utiliser /setup_ticket pour la créer.",
                ephemeral=True)
            return

        existing = discord.utils.get(category.channels,
                                     name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                "Tu as déjà un ticket ouvert dans la catégorie Tickets !",
                ephemeral=True)
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
            reason="Création d'un ticket")
        embed = discord.Embed(
            title="Ticket Support",
            description=
            f"Salut {user.mention} ! Un membre du staff va te répondre rapidement.\nClique sur le bouton pour fermer le ticket.",
            color=discord.Color.blue())
        view = TicketCloseView()
        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            f"Ton ticket a été créé : {channel.mention}", ephemeral=True)


class TicketCloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red,
                         label="Fermer le ticket",
                         custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await interaction.response.send_message("Fermeture dans 5 secondes...",
                                                ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket fermé par {interaction.user}")


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
