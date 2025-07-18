import discord
from discord.ext import commands
from discord import app_commands, Embed
from i18n import _

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def get_welcome_config(self, guild_id):
        """Get welcome configuration for a guild"""
        # Try welcome_config table first
        result = await self.db.query(
            "SELECT * FROM welcome_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if result:
            return result
            
        # If no welcome_config, check guild_config table for dashboard consistency
        guild_result = await self.db.query(
            "SELECT welcome_channel, welcome_message, welcome_enabled FROM guild_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if guild_result and guild_result.get("welcome_enabled"):
            # Convert guild_config format to welcome_config format
            return {
                "welcome_channel": guild_result.get("welcome_channel"),
                "welcome_message": guild_result.get("welcome_message"),
                "goodbye_channel": None,
                "goodbye_message": None
            }
        
        return {}

    async def save_welcome_config(self, guild_id, **kwargs):
        """Save welcome configuration for a guild"""
        # Check if config exists
        existing = await self.get_welcome_config(guild_id)
        
        if existing:
            # Update existing config
            set_clauses = []
            params = []
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = %s")
                params.append(value)
            
            if set_clauses:
                params.append(guild_id)
                query = f"UPDATE welcome_config SET {', '.join(set_clauses)} WHERE guild_id = %s"
                await self.db.query(query, params)
        else:
            # Insert new config
            columns = ['guild_id'] + list(kwargs.keys())
            values = [guild_id] + list(kwargs.values())
            placeholders = ', '.join(['%s'] * len(values))
            
            query = f"INSERT INTO welcome_config ({', '.join(columns)}) VALUES ({placeholders})"
            await self.db.query(query, values)

    def format_message(self, template: str, member: discord.Member):
        return template\
            .replace("{memberName}", member.display_name)\
            .replace("{memberMention}", member.mention)\
            .replace("{serverName}", member.guild.name)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = member.guild.id
        config = await self.get_welcome_config(guild_id)
        
        channel_id = config.get("welcome_channel")
        # Use configured message or default translation
        message = config.get("welcome_message")
        if not message:
            message = _("welcome_system.default_welcome_message", member.id, guild_id)

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = Embed(
                    title=_("welcome_system.new_member_title", member.id, guild_id),
                    description=self.format_message(message, member),
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = member.guild.id
        config = await self.get_welcome_config(guild_id)
        
        channel_id = config.get("goodbye_channel")
        # Use configured message or default translation
        message = config.get("goodbye_message")
        if not message:
            message = _("welcome_system.default_goodbye_message", member.id, guild_id)

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = Embed(
                    title=_("welcome_system.member_left_title", member.id, guild_id),
                    description=self.format_message(message, member),
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                await channel.send(embed=embed)

    # Configuration commands removed - use unified /config command instead
    # @app_commands.command(name="configwelcome", description="Configurer le message de bienvenue")
    # @app_commands.describe(channel="Salon de bienvenue", message="Message avec {memberMention}, {memberName}, {serverName}")
    # async def configwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    #     guild_id = interaction.guild.id
    #     await self.save_welcome_config(guild_id, welcome_channel=channel.id, welcome_message=message)
    #     await interaction.response.send_message("✅ Message de bienvenue configuré.", ephemeral=True)

    # @app_commands.command(name="configgoodbye", description="Configurer le message d'au revoir")
    # @app_commands.describe(channel="Salon d'au revoir", message="Message avec {memberName}, {serverName}")
    # async def configgoodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    #     guild_id = interaction.guild.id
    #     await self.save_welcome_config(guild_id, goodbye_channel=channel.id, goodbye_message=message)
    #     await interaction.response.send_message("✅ Message d'au revoir configuré.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
