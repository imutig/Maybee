import discord
from discord.ext import commands
from discord import app_commands
from i18n import _
from .command_logger import log_command_usage
from custom_emojis import get_emoji, YELLOW_COG, GLOBE, USERS, TROPHY, SHIELD, TICKET, CHART_BAR, SUCCESS

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="Get the link to access the web dashboard")
    @log_command_usage
    async def dashboard(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Créer un embed avec le lien du dashboard
        embed = discord.Embed(
            title=f"{GLOBE} {_('commands.dashboard.title', user_id, guild_id)}",
            description=_("commands.dashboard.description", user_id, guild_id),
            color=0xFAC10C,  # Couleur jaune miel Maybee
            url="https://web-production-448ba.up.railway.app/"
        )
        
        embed.add_field(
            name=f"{GLOBE} {_('commands.dashboard.link_title', user_id, guild_id)}",
            value="[🌐 **Accéder au Dashboard**](https://web-production-448ba.up.railway.app/)",
            inline=False
        )
        
        embed.add_field(
            name=f"{TROPHY} {_('commands.dashboard.features_title', user_id, guild_id)}",
            value=f"• {SHIELD} **Gestion des rôles automatiques**\n• {TROPHY} **Système de niveaux et XP**\n• {USERS} **Configuration des messages de bienvenue**\n• {TICKET} **Logs des tickets**\n• {CHART_BAR} **Statistiques du serveur**\n• {SUCCESS} **Et bien plus encore !**",
            inline=False
        )
        
        embed.set_footer(text=_('commands.dashboard.footer', user_id, guild_id))
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1414987201556512798.png")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Dashboard(bot))
