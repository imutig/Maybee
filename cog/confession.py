import discord
from discord import app_commands
from discord.ext import commands
import yaml
import os

CONFESSION_FILE = "data/confessions.yaml"


class Confession(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def save_confession(self, username, message):
        # Charge l'existant
        if os.path.exists(CONFESSION_FILE):
            with open(CONFESSION_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or []
        else:
            data = []

        # Ajoute la nouvelle confession
        data.append({"user": username, "confession": message})

        # Réécrit dans le fichier
        with open(CONFESSION_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

    @app_commands.command(
        name="confession",
        description="Envoyer une confession anonyme dans le canal prévu")
    @app_commands.describe(message="Le contenu de ta confession (anonyme)")
    async def confession(self, interaction: discord.Interaction, message: str):
        # Sauvegarde la confession avec le pseudo
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        self.save_confession(username, message)

        # Crée un embed pour la confession
        embed = discord.Embed(title="💬 Nouvelle confession anonyme",
                              description=message,
                              color=discord.Color.purple())
        embed.set_footer(text="Confession envoyée anonymement")

        # Envoie la confession dans un canal spécifique (à modifier ici)
        channel_id = 1394137179197935647  # <-- Remplace par l'ID de ton canal de confession
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await interaction.response.send_message(
                "❌ Le canal de confession n'a pas été trouvé.", ephemeral=True)
            return

        # Envoie sans mentionner l'utilisateur (anonyme)
        await channel.send(embed=embed)

        # Confirme à l'utilisateur que sa confession est envoyée
        await interaction.response.send_message(
            "✅ Ta confession a bien été envoyée anonymement.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Confession(bot))
