import discord
from discord.ext import commands
from discord import app_commands

class EmbedCreator(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed",
                          description="Créer un embed personnalisé")
    @app_commands.describe(
        titre="Titre de l'embed",
        description="Description de l'embed",
        couleur="Couleur hexadécimale (ex: #ff6600) ou nom (blue, red...)",
        image_url="URL d'une image à afficher (optionnel)",
        fields="Champs à ajouter au format clé:valeur|clé2:valeur2...",
        salon="Salon dans lequel envoyer l'embed")
    async def embed(self,
                    interaction: discord.Interaction,
                    titre: str,
                    description: str,
                    salon: discord.TextChannel,
                    couleur: str = "blue",
                    image_url: str = None,
                    fields: str = None):
        # Gestion de la couleur
        try:
            if couleur.startswith("#"):
                color = discord.Color(int(couleur[1:], 16))
            else:
                color = getattr(discord.Color, couleur.lower())()
        except Exception:
            color = discord.Color.blue()
            await interaction.response.send_message(
                "❗️ Couleur invalide, j'utilise le bleu par défaut.",
                ephemeral=True)

        # Création de l'embed
        embed = discord.Embed(title=titre,
                              description=description,
                              color=color)
        embed.set_footer(text=f"Créé par {interaction.user.display_name}")

        # Image si fournie
        if image_url:
            embed.set_image(url=image_url)

        # Ajout des fields si fournis
        if fields:
            try:
                # Format attendu : "clé:valeur|clé2:valeur2"
                field_list = fields.split("|")
                for field in field_list:
                    if ":" in field:
                        name, value = field.split(":", 1)
                        embed.add_field(name=name.strip(),
                                        value=value.strip(),
                                        inline=False)
            except Exception:
                await interaction.response.send_message(
                    "❌ Erreur dans le format des champs. Utilise clé:valeur|clé2:valeur2",
                    ephemeral=True)
                return

        # Envoie dans le salon choisi
        try:
            await salon.send(embed=embed)
            await interaction.response.send_message(
                "✅ Embed envoyé avec succès !", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erreur lors de l'envoi : {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(EmbedCreator(bot))
