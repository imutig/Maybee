import discord
from discord.ext import commands
from discord import app_commands

class EmbedModal(discord.ui.Modal, title="Créer un embed"):

    titre = discord.ui.TextInput(label="Titre", required=True)
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, required=True)
    couleur = discord.ui.TextInput(label="Couleur (ex: blue ou #ff6600)", required=False, default="blue")
    champs = discord.ui.TextInput(label="Champs (optionnel, ex: Nom1:Valeur1|Nom2:Valeur2...)",
                                   required=False, placeholder="ex: champ:val|champ2:val2")
    image = discord.ui.TextInput(label="URL image (optionnel)", required=False)

    def __init__(self, interaction, salon: discord.TextChannel):
        super().__init__()
        self.interaction = interaction
        self.salon = salon

    async def on_submit(self, interaction: discord.Interaction):
        # Couleur
        try:
            color = discord.Color(int(self.couleur.value[1:], 16)) if self.couleur.value.startswith("#") else getattr(discord.Color, self.couleur.value.lower())()
        except:
            color = discord.Color.blue()

        embed = discord.Embed(
            title=self.titre.value,
            description=self.description.value,
            color=color
        )
        embed.set_footer(text=f"Créé par {interaction.user.display_name}")

        # Champs
        if self.champs.value:
            try:
                for part in self.champs.value.split("|"):
                    if ":" in part:
                        name, value = part.split(":", 1)
                        embed.add_field(name=name.strip(), value=value.strip(), inline=False)
            except Exception:
                await interaction.response.send_message("❌ Erreur dans le format des champs (attendu: Champ:Valeur|...)", ephemeral=True)
                return

        if self.image.value:
            embed.set_image(url=self.image.value)

        try:
            await self.salon.send(embed=embed)
            await interaction.response.send_message("✅ Embed envoyé avec succès !", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

class EmbedCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Créer un embed via un formulaire")
    @app_commands.describe(salon="Salon où envoyer l'embed")
    async def embed(self, interaction: discord.Interaction, salon: discord.TextChannel = None):
        salon = salon or interaction.channel
        await interaction.response.send_modal(EmbedModal(interaction, salon))

async def setup(bot):
    await bot.add_cog(EmbedCreator(bot))
