import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime


def format_date_fr(date):
    mois = {
        "January": "janvier",
        "February": "février",
        "March": "mars",
        "April": "avril",
        "May": "mai",
        "June": "juin",
        "July": "juillet",
        "August": "août",
        "September": "septembre",
        "October": "octobre",
        "November": "novembre",
        "December": "décembre"
    }

    jour = {
        "Monday": "lundi",
        "Tuesday": "mardi",
        "Wednesday": "mercredi",
        "Thursday": "jeudi",
        "Friday": "vendredi",
        "Saturday": "samedi",
        "Sunday": "dimanche"
    }

    en_str = date.strftime("%A %d %B %Y à %Hh%M")
    for en, fr in mois.items():
        en_str = en_str.replace(en, fr)
    for en, fr in jour.items():
        en_str = en_str.replace(en, fr)
    return en_str


class Scan(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="scan",
        description="Scanne un membre et affiche ses infos de base.")
    @app_commands.describe(membre="Le membre à scanner")
    async def scan(self, interaction: discord.Interaction,
                   membre: discord.Member):
        roles = [
            role.mention for role in membre.roles
            if role != interaction.guild.default_role
        ]
        date_joined = format_date_fr(
            membre.joined_at) if membre.joined_at else "Inconnue"
        created_at = membre.created_at

        embed = discord.Embed(title=f"🔍 Scan de {membre.display_name}",
                              color=discord.Color.green())
        embed.set_thumbnail(url=membre.display_avatar.url)
        embed.add_field(name="🆔 ID", value=membre.id, inline=True)
        embed.add_field(name="📛 Pseudo",
                        value=f"{membre.name}#{membre.discriminator}",
                        inline=True)
        embed.add_field(name="📅 Arrivé sur le serveur",
                        value=date_joined,
                        inline=False)
        embed.add_field(name="📆 Compte créé le",
                        value=created_at,
                        inline=False)
        embed.add_field(name="🎭 Rôles",
                        value=", ".join(roles) if roles else "Aucun",
                        inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Scan(bot))
