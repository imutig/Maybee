import discord
from discord.ext import commands, tasks
from discord import app_commands, Embed
import yaml
import random
import asyncio
import datetime
import os

CONFIG_FILE = "config/config_xp.yaml"
XP_FILE = "data/xp_data.yaml"
XP_RANGE = (3, 6)
XP_COOLDOWN = 10
VOICE_XP_AMOUNT = 5
VOICE_XP_INTERVAL = 180  # 3 minutes en secondes


class XPSystem(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.user_last_xp = {}
        self.guild_xp_channels = self.load_config()
        self.voice_xp_task = None  # On lancera la tâche dans on_ready

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(self.guild_xp_channels, f)

    def load_xp(self):
        if not os.path.exists(XP_FILE):
            return {}
        with open(XP_FILE, "r") as f:
            return yaml.safe_load(f) or {}

    def save_xp(self, data):
        with open(XP_FILE, "w") as f:
            yaml.dump(data, f)

    def add_xp(self, user_id, guild_id, amount, source="text"):
        data = self.load_xp()
        data.setdefault(str(guild_id), {})
        data[str(guild_id)].setdefault(str(user_id), {
            "xp": 0,
            "level": 1,
            "text_xp": 0,
            "voice_xp": 0
        })
        profile = data[str(guild_id)][str(user_id)]

        profile["xp"] += amount
        if source == "text":
            profile["text_xp"] += amount
        elif source == "voice":
            profile["voice_xp"] += amount

        level = int((profile["xp"] / 100)**0.5) + 1
        leveled_up = False
        if level > profile["level"]:
            profile["level"] = level
            leveled_up = True

        self.save_xp(data)
        return leveled_up, profile["level"]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        now = datetime.datetime.utcnow()
        last_time = self.user_last_xp.get(message.author.id)

        if last_time and (now - last_time).total_seconds() < XP_COOLDOWN:
            return

        self.user_last_xp[message.author.id] = now
        xp_gain = random.randint(*XP_RANGE)
        leveled_up, new_level = self.add_xp(message.author.id,
                                            message.guild.id,
                                            xp_gain,
                                            source="text")

        guild_conf = self.guild_xp_channels.get(str(message.guild.id), {})
        if leveled_up:
            xp_channel_id = guild_conf.get("xp_channel")
            level_roles = guild_conf.get("level_roles", {})
            role_id = level_roles.get(str(new_level))
            if role_id:
                role = message.guild.get_role(role_id)
                if role:
                    await message.author.add_roles(role)

            if xp_channel_id:
                channel = self.bot.get_channel(xp_channel_id)
                if channel:
                    await channel.send(
                        f"🎉 {message.author.mention} est monté niveau **{new_level}** !"
                        + (f" et a reçu le rôle {role.mention} !"
                           if role_id else ""))

    async def give_voice_xp_loop(self):
        await self.bot.wait_until_ready()
        print("[XP VOICE] Tâche XP vocal démarrée.")
        while not self.bot.is_closed():
            print("[XP VOICE] Nouvelle boucle XP vocal.")
            for guild in self.bot.guilds:
                print(f"[XP VOICE] Guild: {guild.name}")
                for vc in guild.voice_channels:
                    print(f"[XP VOICE] Salon vocal : {vc.name}")
                    for member in vc.members:
                        if member.bot:
                            print(f"[XP VOICE] Ignoré (bot) : {member.name}")
                            continue
                        print(f"[XP VOICE] XP vocal donné à : {member.name}")
                        self.add_xp(member.id,
                                    guild.id,
                                    VOICE_XP_AMOUNT,
                                    source="voice")
            await asyncio.sleep(VOICE_XP_INTERVAL)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.voice_xp_task:
            print("[XP VOICE] Initialisation de la tâche XP vocal.")
            self.voice_xp_task = asyncio.create_task(self.give_voice_xp_loop())
        else:
            print("[XP VOICE] Tâche XP vocal déjà en cours.")

    @app_commands.command(name="level",
                          description="Affiche ton niveau actuel")
    async def level(self, interaction: discord.Interaction):
        data = self.load_xp()
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        user_data = data.get(guild_id, {}).get(user_id, {
            "xp": 0,
            "level": 1,
            "text_xp": 0,
            "voice_xp": 0
        })

        xp = user_data["xp"]
        level = user_data["level"]
        text_xp = user_data.get("text_xp", 0)
        voice_xp = user_data.get("voice_xp", 0)

        xp_for_this_level = 100 * ((level - 1)**2)
        xp_for_next_level = 100 * (level**2)
        current_xp = xp - xp_for_this_level
        xp_needed = xp_for_next_level - xp_for_this_level
        progress = min(max(current_xp / xp_needed, 0), 1)

        bar_length = 20
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        embed = Embed(title=f"Niveau de {interaction.user.display_name}",
                      color=0x7289DA)
        embed.add_field(name="Niveau", value=str(level), inline=True)
        embed.add_field(name="XP total",
                        value=f"{xp} / {xp_for_next_level}",
                        inline=True)
        embed.add_field(name="Progression", value=bar, inline=False)
        embed.add_field(name="XP écrit", value=str(text_xp), inline=True)
        embed.add_field(name="XP vocal", value=str(voice_xp), inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="XP System")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="topxp", description="Classement XP")
    async def topxp(self, interaction: discord.Interaction):
        data = self.load_xp()
        guild_id = str(interaction.guild.id)
        guild_data = data.get(guild_id, {})

        if not guild_data:
            await interaction.response.send_message("Aucune donnée XP.",
                                                    ephemeral=True)
            return

        top_users = sorted(guild_data.items(),
                           key=lambda x: x[1].get("xp", 0),
                           reverse=True)[:10]
        embed = Embed(title=f"Classement XP - {interaction.guild.name}",
                      color=0xFFD700)
        description = ""

        for i, (user_id, user_info) in enumerate(top_users, start=1):
            member = interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"ID {user_id}"
            description += f"**{i}. {name}** - Niveau {user_info['level']} - {user_info['xp']} XP\n"

        embed.description = description
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="configlevel",
        description="Configurer le salon d'XP et les rôles par niveau")
    @app_commands.describe(xp_channel="Salon d'annonce de niveau",
                           level="Niveau",
                           role="Rôle à attribuer")
    async def configlevel(self,
                          interaction: discord.Interaction,
                          xp_channel: discord.TextChannel = None,
                          level: int = None,
                          role: discord.Role = None):
        guild_id = str(interaction.guild.id)
        self.guild_xp_channels.setdefault(guild_id, {})

        if xp_channel:
            self.guild_xp_channels[guild_id]["xp_channel"] = xp_channel.id

        if level is not None and role is not None:
            self.guild_xp_channels[guild_id].setdefault("level_roles", {})
            self.guild_xp_channels[guild_id]["level_roles"][str(
                level)] = role.id

        self.save_config()
        await interaction.response.send_message("✅ Configuration mise à jour.",
                                                ephemeral=True)

    @app_commands.command(
        name="levelroles",
        description="Voir les rôles attribués selon les niveaux")
    async def levelroles(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        guild_conf = self.guild_xp_channels.get(guild_id, {})
        roles_config = guild_conf.get("level_roles", {})

        if not roles_config:
            await interaction.response.send_message(
                "Aucun rôle configuré pour les niveaux.", ephemeral=True)
            return

        description = ""
        for lvl, role_id in sorted(roles_config.items(),
                                   key=lambda x: int(x[0])):
            role = interaction.guild.get_role(role_id)
            if role:
                description += f"Niveau {lvl} → {role.mention}\n"
            else:
                description += f"Niveau {lvl} → (rôle introuvable)\n"

        embed = Embed(title="Rôles par niveau",
                      description=description,
                      color=0x00FFAA)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(XPSystem(bot))
