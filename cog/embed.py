import discord
from discord.ext import commands
from discord import app_commands
from i18n import _

class EmbedModal(discord.ui.Modal, title="Create an embed"):

    titre = discord.ui.TextInput(label="Title", required=True)
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, required=True)
    couleur = discord.ui.TextInput(label="Color (ex: blue or #ff6600)", required=False, default="blue")
    champs = discord.ui.TextInput(label="Fields (optional)",
                                   required=False, placeholder="ex: field:val|field2:val2")
    image = discord.ui.TextInput(label="Image URL (optional)", required=False)

    def __init__(self, interaction, salon: discord.TextChannel):
        super().__init__()
        self.interaction = interaction
        self.salon = salon
        self.user_id = interaction.user.id
        self.guild_id = interaction.guild.id if interaction.guild else None

    async def on_submit(self, interaction: discord.Interaction):
        # Color
        try:
            color = discord.Color(int(self.couleur.value[1:], 16)) if self.couleur.value.startswith("#") else getattr(discord.Color, self.couleur.value.lower())()
        except:
            color = discord.Color.blue()

        embed = discord.Embed(
            title=self.titre.value,
            description=self.description.value,
            color=color
        )
        embed.set_footer(text=_("commands.embed.created_footer", self.user_id, self.guild_id, user=interaction.user.display_name))

        # Fields
        if self.champs.value:
            try:
                for part in self.champs.value.split("|"):
                    if ":" in part:
                        name, value = part.split(":", 1)
                        embed.add_field(name=name.strip(), value=value.strip(), inline=False)
            except Exception:
                await interaction.response.send_message(
                    _("commands.embed.fields_error", self.user_id, self.guild_id), 
                    ephemeral=True
                )
                return

        if self.image.value:
            embed.set_image(url=self.image.value)

        try:
            await self.salon.send(embed=embed)
            await interaction.response.send_message(
                _("commands.embed.success", self.user_id, self.guild_id), 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                _("commands.embed.error", self.user_id, self.guild_id, error=str(e)), 
                ephemeral=True
            )

class EmbedCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Create an embed via a form")
    @app_commands.describe(salon="Channel where to send the embed")
    async def embed(self, interaction: discord.Interaction, salon: discord.TextChannel = None):
        salon = salon or interaction.channel
        await interaction.response.send_modal(EmbedModal(interaction, salon))

async def setup(bot):
    await bot.add_cog(EmbedCreator(bot))
