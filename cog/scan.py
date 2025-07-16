import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from i18n import _


class Scan(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="scan",
        description="Scan a member and display their basic info")
    @app_commands.describe(membre="The member to scan")
    async def scan(self, interaction: discord.Interaction,
                   membre: discord.Member):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        roles = [
            role.mention for role in membre.roles
            if role != interaction.guild.default_role
        ]
        date_joined = membre.joined_at.strftime("%B %d, %Y at %H:%M") if membre.joined_at else _("common.unknown", user_id, guild_id)
        created_at = membre.created_at.strftime("%B %d, %Y at %H:%M")

        embed = discord.Embed(
            title=_("commands.scan.embed_title", user_id, guild_id, member=membre.display_name),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=membre.display_avatar.url)
        embed.add_field(
            name=_("commands.scan.id_field", user_id, guild_id), 
            value=membre.id, inline=True
        )
        embed.add_field(
            name=_("commands.scan.username_field", user_id, guild_id),
            value=f"{membre.name}#{membre.discriminator}",
            inline=True
        )
        embed.add_field(
            name=_("commands.scan.joined_field", user_id, guild_id),
            value=date_joined,
            inline=False
        )
        embed.add_field(
            name=_("commands.scan.created_field", user_id, guild_id),
            value=created_at,
            inline=False
        )
        embed.add_field(
            name=_("commands.scan.roles_field", user_id, guild_id),
            value=", ".join(roles) if roles else _("commands.scan.no_roles", user_id, guild_id),
            inline=False
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Scan(bot))
