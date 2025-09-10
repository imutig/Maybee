import discord
from discord import app_commands
from discord.ext import commands

class Confession(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def get_confession_channel(self, guild_id):
        """Get confession channel for a guild"""
        result = await self.db.query(
            "SELECT channel_id FROM confession_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        return result['channel_id'] if result else None

    async def set_confession_channel(self, guild_id, channel_id):
        """Set confession channel for a guild"""
        await self.db.query(
            "INSERT INTO confession_config (guild_id, channel_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE channel_id = %s",
            (guild_id, channel_id, channel_id)
        )

    async def save_confession(self, user_id, username, message, guild_id):
        """Save a confession to the database"""
        await self.db.query(
            "INSERT INTO confessions (user_id, username, confession, guild_id) VALUES (%s, %s, %s, %s)",
            (user_id, username, message, guild_id)
        )

    @app_commands.command(name="confession", description="Send an anonymous confession to the designated channel")
    @app_commands.describe(message="The content of your confession (anonymous)")
    async def confession(self, interaction: discord.Interaction, message: str):
        from i18n import _
        
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        channel_id = await self.get_confession_channel(guild_id)
        
        if not channel_id:
            await interaction.response.send_message(
                _("confession_system.errors.no_channel", user_id, guild_id), 
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                _("confession_system.errors.channel_not_found", user_id, guild_id), 
                ephemeral=True
            )
            return

        # Save confession to database
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        await self.save_confession(interaction.user.id, username, message, guild_id)

        # Create embed for the confession
        embed = discord.Embed(
            title=_("confession_system.embed.title", user_id, guild_id),
            description=message,
            color=discord.Color.purple()
        )
        embed.set_footer(text=_("confession_system.embed.footer", user_id, guild_id))

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(_("confession_system.success", user_id, guild_id), ephemeral=True)
                
        except discord.Forbidden:
            await interaction.response.send_message(
                _("confession_system.errors.no_permission", user_id, guild_id), 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                _("confession_system.errors.send_error", user_id, guild_id, error=str(e)), 
                ephemeral=True
            )

    # Configuration command removed - use unified /config command instead
    # @app_commands.command(name="configconfession", description="Configurer le canal de confessions")
    # @app_commands.describe(channel="Le canal où envoyer les confessions")
    # async def configconfession(self, interaction: discord.Interaction, channel: discord.TextChannel):
    #     if not interaction.user.guild_permissions.manage_channels:
    #         await interaction.response.send_message(
    #             "❌ Vous n'avez pas la permission de gérer les canaux.", 
    #             ephemeral=True
    #         )
    #         return

    #     guild_id = interaction.guild.id
    #     await self.set_confession_channel(guild_id, channel.id)
    #     await interaction.response.send_message(
    #         f"✅ Canal de confessions configuré sur {channel.mention}!", 
    #         ephemeral=True
    #     )

async def setup(bot):
    await bot.add_cog(Confession(bot))
