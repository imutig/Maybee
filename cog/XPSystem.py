import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio

class SetXPChannelModal(discord.ui.Modal, title="Attribuer salon annonces XP"):
    channel_id = discord.ui.TextInput(
        label="ID du salon",
        placeholder="Entrez l'ID du salon où envoyer les annonces XP",
        style=discord.TextStyle.short
    )

    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id_int = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id_int)
            if not channel:
                await interaction.response.send_message("Salon introuvable dans cette guild.", ephemeral=True)
                return
            
            await self.bot.db.query(
                """
                INSERT INTO xp_config (guild_id, xp_channel) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE xp_channel = %s
                """,
                (self.guild_id, channel_id_int, channel_id_int)
            )
            await interaction.response.send_message(f"Salon {channel.mention} attribué pour les annonces XP !", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("L'ID du salon doit être un nombre entier.", ephemeral=True)

class SetRoleLevelModal(discord.ui.Modal, title="Attribuer rôle à un niveau"):
    level = discord.ui.TextInput(
        label="Niveau",
        placeholder="Entrez le niveau (nombre entier)",
        style=discord.TextStyle.short
    )
    role_id = discord.ui.TextInput(
        label="ID du rôle",
        placeholder="Entrez l'ID du rôle à attribuer",
        style=discord.TextStyle.short
    )

    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            level_int = int(self.level.value)
            role_id_int = int(self.role_id.value)

            role = interaction.guild.get_role(role_id_int)
            if not role:
                await interaction.response.send_message("Rôle introuvable dans cette guild.", ephemeral=True)
                return
            
            await self.bot.db.query(
                """
                INSERT INTO level_roles (guild_id, level, role_id) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE role_id = %s
                """,
                (self.guild_id, level_int, role_id_int, role_id_int)
            )
            await interaction.response.send_message(f"Rôle {role.mention} attribué au niveau {level_int} !", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Le niveau et l'ID du rôle doivent être des nombres entiers.", ephemeral=True)

class ConfigLevelView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Attribuer salon annonces XP", style=discord.ButtonStyle.green)
    async def set_xp_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetXPChannelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Attribuer rôle à un niveau", style=discord.ButtonStyle.blurple)
    async def set_role_level(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetRoleLevelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}
        print("✅ XPSystem cog chargé")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.voice_xp_loop.is_running():
            print("▶️ Démarrage de la boucle XP vocale depuis on_ready.")
            self.voice_xp_loop.start()

        
    def cog_unload(self):
        self.voice_xp_loop.cancel()

    @tasks.loop(minutes=10)
    async def voice_xp_loop(self):
        print("🔁 Boucle XP vocale démarrée.")

        for guild in self.bot.guilds:
            print(f"📂 Serveur : {guild.name} ({guild.id})")

            for vc in guild.voice_channels:
                print(f"🔊 Salon vocal : {vc.name} | Membres : {len(vc.members)}")

                if len(vc.members) <= 1:
                    print("⛔ Ignoré : seulement 1 personne ou moins dans le vocal.")
                    continue

                for member in vc.members:
                    print(f"👤 Membre : {member.display_name} ({member.id})")

                    if member.bot:
                        print("🤖 Ignoré : c'est un bot.")
                        continue

                    if member.voice.self_mute or member.voice.self_deaf:
                        print("🔇 Ignoré : utilisateur s'est mis en mute/sourdine.")
                        continue

                    if member.voice.mute or member.voice.deaf:
                        print("🔕 Ignoré : mute/sourdine forcée par le serveur.")
                        continue

                    print("✅ Ajout de 15 XP vocal à", member.display_name)
                    leveled_up, level = await self.add_xp(member.id, guild.id, 15, source="voice")

                    if leveled_up:
                        print(f"🆙 {member.display_name} est monté niveau {level} !")
                        await self.handle_level_up(guild, member, level)

        print("✅ Boucle XP vocale terminée.\n")

    async def add_xp(self, user_id, guild_id, amount, source="text"):
        sql = "SELECT * FROM xp_data WHERE user_id = %s AND guild_id = %s"
        data = await self.bot.db.query(sql, (user_id, guild_id), fetchone=True)

        if not data:
            await self.bot.db.query(
                "INSERT INTO xp_data (user_id, guild_id, xp, level, text_xp, voice_xp) VALUES (%s, %s, 0, 1, 0, 0)",
                (user_id, guild_id)
            )
            data = {"xp": 0, "level": 1, "text_xp": 0, "voice_xp": 0}

        new_xp = data["xp"] + amount
        text_xp = data["text_xp"] + amount if source == "text" else data["text_xp"]
        voice_xp = data["voice_xp"] + amount if source == "voice" else data["voice_xp"]
        new_level = int((new_xp / 100)**0.5) + 1
        leveled_up = new_level > data["level"]

        await self.bot.db.query(
            "UPDATE xp_data SET xp=%s, text_xp=%s, voice_xp=%s, level=%s WHERE user_id=%s AND guild_id=%s",
            (new_xp, text_xp, voice_xp, new_level, user_id, guild_id)
        )

        return leveled_up, new_level

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        key = (user_id, guild_id)

        if key in self.cooldown:
            return

        xp = random.randint(3, 6)
        leveled_up, level = await self.add_xp(user_id, guild_id, xp, source="text")

        if leveled_up:
            await self.handle_level_up(message.guild, message.author, level)

        self.cooldown[key] = True
        await asyncio.sleep(10)
        del self.cooldown[key]

    async def handle_level_up(self, guild, member, level):
        config = await self.bot.db.query("SELECT xp_channel FROM xp_config WHERE guild_id = %s", (guild.id,), fetchone=True)
        gained_roles = []

        # Attribution des rôles
        roles = await self.bot.db.query(
            "SELECT role_id FROM level_roles WHERE guild_id = %s AND level = %s",
            (guild.id, level),
            fetchall=True
        )
        for row in roles:
            role = guild.get_role(row["role_id"])
            if role:
                await member.add_roles(role)
                gained_roles.append(role.mention)

        # Annonce dans le salon XP s'il est configuré
        if config:
            channel = guild.get_channel(config["xp_channel"])
            if channel:
                embed = discord.Embed(
                    title="🎉 Niveau atteint !",
                    description=f"{member.mention} est maintenant **niveau {level}** !",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                if gained_roles:
                    embed.add_field(name="🎁 Rôle(s) obtenu(s)", value=", ".join(gained_roles), inline=False)

                await channel.send(content=f"{member.mention}", embed=embed)


    @commands.hybrid_command(name="configlevel", description="Configurer le système de niveaux et annonces XP")
    async def configlevel(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Configuration du système XP",
            description="Utilise les boutons ci-dessous pour configurer le salon d'annonces XP ou attribuer un rôle à un niveau.",
            color=discord.Color.blue()
        )
        view = ConfigLevelView(self.bot, ctx.guild.id)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="topxp", description="Afficher le classement des XP (texte, vocal, total)")            
    async def topxp(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        # Récupérer top 10 par text_xp, voice_xp et total xp
        query = """
            SELECT user_id, text_xp, voice_xp, xp
            FROM xp_data
            WHERE guild_id = %s
            ORDER BY xp DESC
            LIMIT 10
        """
        rows = await self.bot.db.query(query, (guild_id,), fetchall=True)

        if not rows:
            await interaction.response.send_message("Aucune donnée XP trouvée dans ce serveur.", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Top 10 XP", color=discord.Color.gold())
        embed.set_footer(text="Classement basé sur l'XP totale")

        text_lines = []
        voice_lines = []
        total_lines = []

        for i, row in enumerate(rows, start=1):
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else f"Utilisateur ID {row['user_id']}"

            text_lines.append(f"{i}. {name} — {row['text_xp']} XP texte")
            voice_lines.append(f"{i}. {name} — {row['voice_xp']} XP vocal")
            total_lines.append(f"{i}. {name} — {row['xp']} XP total")

        embed.add_field(name="XP Texte", value="\n".join(text_lines), inline=True)
        embed.add_field(name="XP Vocal", value="\n".join(voice_lines), inline=True)
        embed.add_field(name="XP Total", value="\n".join(total_lines), inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="levelroles", description="Afficher la liste des rôles attribués par niveau")       
    async def levelroles(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        rows = await self.bot.db.query(
            "SELECT level, role_id FROM level_roles WHERE guild_id = %s ORDER BY level ASC",
            (guild_id,),
            fetchall=True
        )

        if not rows:
            await interaction.response.send_message("Aucun rôle configuré pour les niveaux dans ce serveur.", ephemeral=True)
            return

        lines = []
        for row in rows:
            role = interaction.guild.get_role(row["role_id"])
            role_name = role.mention if role else f"Rôle ID {row['role_id']} (introuvable)"
            lines.append(f"Niveau {row['level']} → {role_name}")

        embed = discord.Embed(
            title="🎖️ Rôles attribués par niveau",
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

        
    @app_commands.command(name="level", description="Voir votre niveau et XP")
    async def level(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id

        data = await self.bot.db.query("SELECT * FROM xp_data WHERE user_id=%s AND guild_id=%s", (user_id, guild_id), fetchone=True)
        if not data:
            await interaction.response.send_message("Tu n'as pas encore d'XP. Parle un peu !", ephemeral=True)
            return

        xp = data["xp"]
        level = data["level"]
        xp_next = ((level)**2) * 100
        xp_prev = ((level - 1)**2) * 100
        progress = xp - xp_prev
        total_needed = xp_next - xp_prev
        bar_length = 20
        filled = int(bar_length * progress / total_needed)
        bar = "█" * filled + "-" * (bar_length - filled)

        embed = discord.Embed(title=f"Niveau de {interaction.user.display_name}", color=0x00ff00)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Niveau", value=str(level), inline=True)
        embed.add_field(name="XP total", value=f"{xp}/{xp_next}", inline=True)
        embed.add_field(name="Progression", value=f"[{bar}] ({progress}/{total_needed})", inline=False)
        embed.add_field(name="XP texte", value=str(data["text_xp"]), inline=True)
        embed.add_field(name="XP vocal", value=str(data["voice_xp"]), inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
