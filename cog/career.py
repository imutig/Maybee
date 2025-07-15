import discord
from discord import app_commands
from discord.ext import commands


class Career(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="career",
        description="Ajoute une décision de carrière pour un membre")
    @app_commands.describe(
        member="Le membre concerné",
        decision="Type de décision prise",
        reason="La raison de cette décision",
        decided_by=
        "Mentionne les rôles qui ont pris la décision (séparés par des virgules ou espaces)"
    )
    @app_commands.choices(decision=[
        app_commands.Choice(name="Avertissement", value="Avertissement"),
        app_commands.Choice(name="Blâme", value="Blâme"),
        app_commands.Choice(name="Rétrogradation", value="Rétrogradation"),
        app_commands.Choice(name="Promotion", value="Promotion"),
        app_commands.Choice(name="Exclusion", value="Exclusion")
    ])
    async def career(self, interaction: discord.Interaction,
                     member: discord.Member,
                     decision: app_commands.Choice[str], reason: str,
                     decided_by: str):
        embed = discord.Embed(title="📋 Décision de Carrière",
                              color=discord.Color.orange())
        embed.add_field(name="👤 Membre", value=member.mention, inline=False)
        embed.add_field(name="📌 Décision", value=decision.value, inline=False)
        embed.add_field(name="📝 Raison", value=reason, inline=False)
        embed.add_field(name="🧑‍⚖️ Décidé par", value=decided_by, inline=False)
        embed.set_footer(text=f"Décision enregistrée par {interaction.user}",
                         icon_url=interaction.user.display_avatar.url)

        # 👇 on mentionne la personne avant le message
        await interaction.response.send_message(content=member.mention,
                                                embed=embed)


async def setup(bot):
    await bot.add_cog(Career(bot))
