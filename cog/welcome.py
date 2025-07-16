import discord
from discord.ext import commands
from discord import app_commands, Embed
import yaml
import os

WELCOME_CONFIG_FILE = "config/welcome.yaml"

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(WELCOME_CONFIG_FILE):
            return {}
        with open(WELCOME_CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}

    def save_config(self):
        with open(WELCOME_CONFIG_FILE, "w") as f:
            yaml.dump(self.config, f)

    def format_message(self, template: str, member: discord.Member):
        return template\
            .replace("{memberName}", member.display_name)\
            .replace("{memberMention}", member.mention)\
            .replace("{serverName}", member.guild.name)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        conf = self.config.get(guild_id, {})
        channel_id = conf.get("welcome_channel")
        message = conf.get("welcome_message", "Bienvenue {memberMention} dans {serverName} ! 🎉")

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = Embed(
                    title="👋 Nouveau membre !",
                    description=self.format_message(message, member),
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = str(member.guild.id)
        conf = self.config.get(guild_id, {})
        channel_id = conf.get("goodbye_channel")
        message = conf.get("goodbye_message", "{memberName} a quitté {serverName}... 😢")

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = Embed(
                    title="👋 Départ",
                    description=self.format_message(message, member),
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                await channel.send(embed=embed)

    @app_commands.command(name="configwelcome", description="Configurer le message de bienvenue")
    @app_commands.describe(channel="Salon de bienvenue", message="Message avec {memberMention}, {memberName}, {serverName}")
    async def configwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        guild_id = str(interaction.guild.id)
        self.config.setdefault(guild_id, {})
        self.config[guild_id]["welcome_channel"] = channel.id
        self.config[guild_id]["welcome_message"] = message
        self.save_config()
        await interaction.response.send_message("✅ Message de bienvenue configuré.", ephemeral=True)

    @app_commands.command(name="configgoodbye", description="Configurer le message d'au revoir")
    @app_commands.describe(channel="Salon d’au revoir", message="Message avec {memberName}, {serverName}")
    async def configgoodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        guild_id = str(interaction.guild.id)
        self.config.setdefault(guild_id, {})
        self.config[guild_id]["goodbye_channel"] = channel.id
        self.config[guild_id]["goodbye_message"] = message
        self.save_config()
        await interaction.response.send_message("✅ Message d’au revoir configuré.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
