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

    @app_commands.command(name="confession", description="Envoyer une confession anonyme dans le canal prévu")
    @app_commands.describe(message="Le contenu de ta confession (anonyme)")
    async def confession(self, interaction: discord.Interaction, message: str):
        guild_id = interaction.guild.id
        channel_id = await self.get_confession_channel(guild_id)
        
        if not channel_id:
            await interaction.response.send_message(
                "❌ Aucun canal de confession n'a été configuré pour ce serveur. "
                "Demandez à un administrateur d'utiliser `/configconfession`.", 
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                "❌ Le canal de confession configuré n'existe plus. "
                "Demandez à un administrateur de reconfigurer avec `/configconfession`.", 
                ephemeral=True
            )
            return

        # Save confession to database
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        await self.save_confession(interaction.user.id, username, message, guild_id)

        # Create embed for the confession
        embed = discord.Embed(
            title="💬 Nouvelle confession anonyme",
            description=message,
            color=discord.Color.purple()
        )
        embed.set_footer(text="Confession envoyée anonymement")

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message("✅ Confession envoyée anonymement!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas les permissions pour envoyer des messages dans le canal de confession.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erreur lors de l'envoi de la confession: {str(e)}", 
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

    @app_commands.command(name="confessionstats", description="Afficher les statistiques des confessions")
    async def confessionstats(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Vous n'avez pas la permission de voir les statistiques.", 
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        
        # Get total confessions count
        total_result = await self.db.query(
            "SELECT COUNT(*) as total FROM confessions WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        total_confessions = total_result['total'] if total_result else 0

        # Get confessions from last 7 days
        recent_result = await self.db.query(
            "SELECT COUNT(*) as recent FROM confessions WHERE guild_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
            (guild_id,),
            fetchone=True
        )
        recent_confessions = recent_result['recent'] if recent_result else 0

        embed = discord.Embed(
            title="📊 Statistiques des confessions",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total des confessions", value=str(total_confessions), inline=True)
        embed.add_field(name="Cette semaine", value=str(recent_confessions), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Confession(bot))
