import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Literal
from i18n import _

class XPMultiplier:
    """XP multiplier system for events and boosts"""
    
    def __init__(self):
        self.multipliers: Dict[int, Dict[str, float]] = {}  # guild_id -> {type: multiplier}
        self.temporary_multipliers: Dict[int, Dict[str, tuple]] = {}  # guild_id -> {type: (multiplier, expires_at)}
        
    def set_multiplier(self, guild_id: int, multiplier_type: str, value: float, duration: Optional[int] = None):
        """Set a multiplier for a guild"""
        if guild_id not in self.multipliers:
            self.multipliers[guild_id] = {}
            
        if duration:
            # Temporary multiplier
            expires_at = datetime.utcnow() + timedelta(minutes=duration)
            if guild_id not in self.temporary_multipliers:
                self.temporary_multipliers[guild_id] = {}
            self.temporary_multipliers[guild_id][multiplier_type] = (value, expires_at)
        else:
            # Permanent multiplier
            self.multipliers[guild_id][multiplier_type] = value
            
    def get_multiplier(self, guild_id: int, multiplier_type: str = "base") -> float:
        """Get current multiplier for a guild"""
        multiplier = 1.0
        
        # Check permanent multipliers
        if guild_id in self.multipliers and multiplier_type in self.multipliers[guild_id]:
            multiplier = self.multipliers[guild_id][multiplier_type]
            
        # Check temporary multipliers
        if guild_id in self.temporary_multipliers and multiplier_type in self.temporary_multipliers[guild_id]:
            temp_multiplier, expires_at = self.temporary_multipliers[guild_id][multiplier_type]
            if datetime.utcnow() < expires_at:
                multiplier = max(multiplier, temp_multiplier)
            else:
                # Remove expired multiplier and log it
                print(f"🕐 XP Multiplier for {multiplier_type} in guild {guild_id} has expired (was {temp_multiplier}x)")
                del self.temporary_multipliers[guild_id][multiplier_type]
                
        return multiplier

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
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        try:
            channel_id_int = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id_int)
            if not channel:
                await interaction.response.send_message(
                    _("xp_system.config.channel_not_found", user_id, guild_id), ephemeral=True)
                return
            
            await self.bot.db.query(
                """
                INSERT INTO xp_config (guild_id, xp_channel) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE xp_channel = %s
                """,
                (self.guild_id, channel_id_int, channel_id_int)
            )
            await interaction.response.send_message(
                _("xp_system.config.channel_success", user_id, guild_id, channel=channel.mention), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(
                _("xp_system.config.invalid_number", user_id, guild_id), ephemeral=True)

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
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        try:
            level_int = int(self.level.value)
            role_id_int = int(self.role_id.value)

            role = interaction.guild.get_role(role_id_int)
            if not role:
                await interaction.response.send_message(
                    _("xp_system.config.role_not_found", user_id, guild_id), ephemeral=True)
                return
            
            await self.bot.db.query(
                """
                INSERT INTO level_roles (guild_id, level, role_id) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE role_id = %s
                """,
                (self.guild_id, level_int, role_id_int, role_id_int)
            )
            await interaction.response.send_message(
                _("xp_system.config.role_success", user_id, guild_id, role=role.mention, level=level_int), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(
                _("xp_system.config.invalid_number", user_id, guild_id), ephemeral=True)

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
        self.xp_batch = {}  # For batching XP updates
        self.batch_size = 50  # Process batches of 50 XP updates
        self.xp_multiplier = XPMultiplier()  # XP multiplier system
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
        """Add XP to a user with improved performance and history tracking"""
        try:
            sql = "SELECT * FROM xp_data WHERE user_id = %s AND guild_id = %s"
            data = await self.bot.db.query(sql, (user_id, guild_id), fetchone=True)

            if not data:
                await self.bot.db.query(
                    "INSERT INTO xp_data (user_id, guild_id, xp, level, text_xp, voice_xp) VALUES (%s, %s, 0, 1, 0, 0)",
                    (user_id, guild_id)
                )
                data = {"xp": 0, "level": 1, "text_xp": 0, "voice_xp": 0}

            # Get guild-specific multipliers
            guild_multiplier = self.xp_multiplier.get_multiplier(guild_id, source)
            
            # Calculate actual XP gained with multiplier
            base_xp = amount
            actual_xp_gained = int(base_xp * guild_multiplier)
            
            # Apply XP to correct source
            text_xp = data["text_xp"] + actual_xp_gained if source == "text" else data["text_xp"]
            voice_xp = data["voice_xp"] + actual_xp_gained if source == "voice" else data["voice_xp"]
            
            # Debug: Show XP breakdown
            print(f"🔍 XP Breakdown - User {user_id}: Total={data['xp']} -> {data['xp'] + actual_xp_gained}, Text={data['text_xp']} -> {text_xp}, Voice={data['voice_xp']} -> {voice_xp}")
            
            # Enhanced logging
            if guild_multiplier != 1.0:
                print(f"⚡ XP Gained: {base_xp} base XP × {guild_multiplier}x multiplier = {actual_xp_gained} XP ({source}) - User {user_id} in guild {guild_id}")
            else:
                print(f"📈 XP Gained: {actual_xp_gained} XP ({source}) - User {user_id} in guild {guild_id}")
            
            new_xp = data["xp"] + actual_xp_gained
            new_level = int((new_xp / 100)**0.5) + 1
            leveled_up = new_level > data["level"]

            # Update main XP table
            await self.bot.db.query(
                "UPDATE xp_data SET xp=%s, text_xp=%s, voice_xp=%s, level=%s WHERE user_id=%s AND guild_id=%s",
                (new_xp, text_xp, voice_xp, new_level, user_id, guild_id)
            )
            
            # Track XP history for leaderboards (only if we have the table)
            try:
                await self.bot.db.query(
                    "INSERT INTO xp_history (user_id, guild_id, xp_gained, xp_type) VALUES (%s, %s, %s, %s)",
                    (user_id, guild_id, actual_xp_gained, source)
                )
            except Exception as history_error:
                # If table doesn't exist, continue without history tracking
                print(f"[XP][WARNING] XP history tracking failed (table may not exist): {history_error}")

            return leveled_up, new_level
        except Exception as e:
            print(f"[XP][ERROR] Error adding XP: {e}")
            return False, 1

    def calculate_level(self, total_xp: int) -> int:
        """Calculate level from total XP"""
        return int((total_xp / 100)**0.5) + 1
        
    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP needed for a specific level"""
        return (level - 1)**2 * 100
        
    def calculate_xp_needed_for_next_level(self, current_xp: int) -> int:
        """Calculate XP needed for the next level"""
        current_level = self.calculate_level(current_xp)
        next_level_xp = self.calculate_xp_for_level(current_level + 1)
        return next_level_xp - current_xp

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message XP with improved performance"""
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        key = (user_id, guild_id)

        if key in self.cooldown:
            return

        try:
            xp = random.randint(3, 6)
            leveled_up, level = await self.add_xp(user_id, guild_id, xp, source="text")

            if leveled_up:
                await self.handle_level_up(message.guild, message.author, level)

            self.cooldown[key] = True
            await asyncio.sleep(10)
            if key in self.cooldown:  # Check if still exists before deleting
                del self.cooldown[key]
        except Exception as e:
            print(f"[XP][ERROR] Error processing message XP: {e}")
            # Remove from cooldown even on error
            if key in self.cooldown:
                del self.cooldown[key]

    async def handle_level_up(self, guild, member, level):
        user_id = member.id
        guild_id = guild.id
        
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
                    title=_("xp_system.level_up.title", user_id, guild_id),
                    description=_("xp_system.level_up.description", user_id, guild_id, user=member.mention, level=level),
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                if gained_roles:
                    embed.add_field(
                        name=_("xp_system.level_up.roles_gained", user_id, guild_id), 
                        value=", ".join(gained_roles), 
                        inline=False
                    )

                await channel.send(content=f"{member.mention}", embed=embed)


    # Configuration command removed - use unified /config command instead
    # @commands.hybrid_command(name="configlevel", description="Configurer le système de niveaux et annonces XP")
    # async def configlevel(self, ctx: commands.Context):
    #     embed = discord.Embed(
    #         title="Configuration du système XP",
    #         description="Utilise les boutons ci-dessous pour configurer le salon d'annonces XP ou attribuer un rôle à un niveau.",
    #         color=discord.Color.blue()
    #     )
    #     view = ConfigLevelView(self.bot, ctx.guild.id)
    #     await ctx.send(embed=embed, view=view)

    @app_commands.command(name="leaderboard", description="Show XP leaderboard")
    @app_commands.describe(
        period="Choose leaderboard period",
        type="Choose leaderboard type"
    )
    async def leaderboard(self, interaction: discord.Interaction, 
                         period: Literal["weekly", "monthly", "all-time"] = "all-time",
                         type: Literal["total", "text", "voice"] = "total"):
        """Unified leaderboard command with period and type options"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        if period == "weekly":
            await self._show_weekly_leaderboard(interaction, user_id, guild_id, type)
        elif period == "monthly":
            await self._show_monthly_leaderboard(interaction, user_id, guild_id, type)
        else:  # all-time
            await self._show_alltime_leaderboard(interaction, user_id, guild_id, type)
    
    async def _show_weekly_leaderboard(self, interaction: discord.Interaction, user_id: int, guild_id: int, type: str = "total"):
        """Show weekly XP leaderboard with persistent caching"""
        # Check persistent cache
        cache_key = f"weekly_leaderboard_{guild_id}_{type}"
        cached_embed = self.bot.cache.leaderboards.get(cache_key)
        
        if cached_embed:
            # Convert cached data back to embed
            embed_dict = cached_embed
            embed = discord.Embed.from_dict(embed_dict)
            await interaction.response.send_message(embed=embed)
            return
        
        try:
            # Get weekly XP data
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            # Build query based on type
            if type == "text":
                query = """SELECT user_id, SUM(xp_gained) as weekly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'text'
                           GROUP BY user_id
                           ORDER BY weekly_xp DESC
                           LIMIT 10"""
                color = discord.Color.blue()
                title_suffix = " (Text)"
            elif type == "voice":
                query = """SELECT user_id, SUM(xp_gained) as weekly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'voice'
                           GROUP BY user_id
                           ORDER BY weekly_xp DESC
                           LIMIT 10"""
                color = discord.Color.green()
                title_suffix = " (Voice)"
            else:  # total
                query = """SELECT user_id, SUM(xp_gained) as weekly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s
                           GROUP BY user_id
                           ORDER BY weekly_xp DESC
                           LIMIT 10"""
                color = discord.Color.gold()
                title_suffix = ""
            
            print(f"🔍 Weekly Leaderboard Debug - Type: {type}, Guild: {guild_id}")
            print(f"📊 Query: {query}")
            
            weekly_data = await self.bot.db.query(query, (guild_id, week_ago), fetchall=True)
            
            print(f"📋 Results: {len(weekly_data) if weekly_data else 0} rows")
            if weekly_data:
                for i, row in enumerate(weekly_data[:3]):  # Show first 3 results
                    print(f"  Row {i+1}: {row}")
            
            if not weekly_data:
                await interaction.response.send_message(
                    _("xp_system.weekly_leaderboard.no_data", user_id, guild_id),
                    ephemeral=True
                )
                return
                
            # Create embed
            embed = discord.Embed(
                title=_("xp_system.weekly_leaderboard.title", user_id, guild_id) + title_suffix,
                color=color,
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, data in enumerate(weekly_data, 1):
                user = self.bot.get_user(data["user_id"])
                username = user.display_name if user else "Unknown User"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{username}**: {data['weekly_xp']} XP\n"
                
            embed.description = leaderboard_text
            embed.set_footer(text=_("xp_system.weekly_leaderboard.footer", user_id, guild_id))
            
            # Cache the result as dict (for persistence) - 30 minutes TTL
            self.bot.cache.leaderboards.set(cache_key, embed.to_dict(), ttl=1800)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in weekly leaderboard: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
    
    async def _show_monthly_leaderboard(self, interaction: discord.Interaction, user_id: int, guild_id: int, type: str = "total"):
        """Show monthly XP leaderboard with persistent caching"""
        # Check persistent cache
        cache_key = f"monthly_leaderboard_{guild_id}_{type}"
        cached_embed = self.bot.cache.leaderboards.get(cache_key)
        
        if cached_embed:
            # Convert cached data back to embed
            embed_dict = cached_embed
            embed = discord.Embed.from_dict(embed_dict)
            await interaction.response.send_message(embed=embed)
            return
        
        try:
            # Get monthly XP data
            month_ago = datetime.utcnow() - timedelta(days=30)
            
            # Build query based on type
            if type == "text":
                query = """SELECT user_id, SUM(xp_gained) as monthly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'text'
                           GROUP BY user_id
                           ORDER BY monthly_xp DESC
                           LIMIT 10"""
                color = discord.Color.blue()
                title_suffix = " (Text)"
            elif type == "voice":
                query = """SELECT user_id, SUM(xp_gained) as monthly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'voice'
                           GROUP BY user_id
                           ORDER BY monthly_xp DESC
                           LIMIT 10"""
                color = discord.Color.green()
                title_suffix = " (Voice)"
            else:  # total
                query = """SELECT user_id, SUM(xp_gained) as monthly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s
                           GROUP BY user_id
                           ORDER BY monthly_xp DESC
                           LIMIT 10"""
                color = discord.Color.purple()
                title_suffix = ""
            
            print(f"🔍 Monthly Leaderboard Debug - Type: {type}, Guild: {guild_id}")
            print(f"📊 Query: {query}")
            
            monthly_data = await self.bot.db.query(query, (guild_id, month_ago), fetchall=True)
            
            print(f"📋 Results: {len(monthly_data) if monthly_data else 0} rows")
            if monthly_data:
                for i, row in enumerate(monthly_data[:3]):  # Show first 3 results
                    print(f"  Row {i+1}: {row}")
            
            if not monthly_data:
                await interaction.response.send_message(
                    _("xp_system.monthly_leaderboard.no_data", user_id, guild_id),
                    ephemeral=True
                )
                return
                
            # Create embed
            embed = discord.Embed(
                title=_("xp_system.monthly_leaderboard.title", user_id, guild_id) + title_suffix,
                color=color,
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, data in enumerate(monthly_data, 1):
                user = self.bot.get_user(data["user_id"])
                username = user.display_name if user else "Unknown User"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{username}**: {data['monthly_xp']} XP\n"
                
            embed.description = leaderboard_text
            embed.set_footer(text=_("xp_system.monthly_leaderboard.footer", user_id, guild_id))
            
            # Cache the result as dict (for persistence) - 30 minutes TTL
            self.bot.cache.leaderboards.set(cache_key, embed.to_dict(), ttl=1800)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in monthly leaderboard: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
    
    async def _show_alltime_leaderboard(self, interaction: discord.Interaction, user_id: int, guild_id: int, type: str):
        """Show all-time XP leaderboard with different types"""
        # Check persistent cache
        cache_key = f"alltime_leaderboard_{type}_{guild_id}"
        cached_embed = self.bot.cache.leaderboards.get(cache_key)
        
        if cached_embed:
            embed_dict = cached_embed
            embed = discord.Embed.from_dict(embed_dict)
            await interaction.response.send_message(embed=embed)
            return
        
        try:
            # Get all-time XP data based on type
            if type == "total":
                query = """SELECT user_id, xp FROM xp_data WHERE guild_id = %s ORDER BY xp DESC LIMIT 10"""
                field_name = _("commands.topxp.total_xp_field", user_id, guild_id)
                color = discord.Color.gold()
                xp_field = "xp"
            elif type == "text":
                query = """SELECT user_id, text_xp FROM xp_data WHERE guild_id = %s ORDER BY text_xp DESC LIMIT 10"""
                field_name = _("commands.topxp.text_xp_field", user_id, guild_id)
                color = discord.Color.blue()
                xp_field = "text_xp"
            else:  # voice
                query = """SELECT user_id, voice_xp FROM xp_data WHERE guild_id = %s ORDER BY voice_xp DESC LIMIT 10"""
                field_name = _("commands.topxp.voice_xp_field", user_id, guild_id)
                color = discord.Color.green()
                xp_field = "voice_xp"
            
            rows = await self.bot.db.query(query, (guild_id,), fetchall=True)
            
            # Debug: Show what data was retrieved
            print(f"🔍 Leaderboard Debug - Type: {type}, Guild: {guild_id}")
            print(f"📊 Query: {query}")
            print(f"📋 Results: {len(rows) if rows else 0} rows")
            if rows:
                for i, row in enumerate(rows[:3]):  # Show first 3 results
                    print(f"  Row {i+1}: {row}")
            
            if not rows:
                await interaction.response.send_message(
                    _("commands.topxp.no_data", user_id, guild_id), 
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = discord.Embed(
                title=_("commands.topxp.embed_title", user_id, guild_id) + f" ({type.title()})",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, row in enumerate(rows, 1):
                member = interaction.guild.get_member(row["user_id"])
                name = member.display_name if member else f"Unknown User"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{name}**: {row[xp_field]} XP\n"
            
            embed.description = leaderboard_text
            embed.set_footer(text=_("commands.topxp.embed_footer", user_id, guild_id))
            
            # Cache the result - 10 minutes TTL
            self.bot.cache.leaderboards.set(cache_key, embed.to_dict(), ttl=600)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in all-time leaderboard: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )

    @app_commands.command(name="levelroles", description="Afficher la liste des rôles attribués par niveau")       
    async def levelroles(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id

        rows = await self.bot.db.query(
            "SELECT level, role_id FROM level_roles WHERE guild_id = %s ORDER BY level ASC",
            (guild_id,),
            fetchall=True
        )

        if not rows:
            await interaction.response.send_message(
                _("xp_system.level_roles.no_roles", user_id, guild_id), ephemeral=True)
            return

        lines = []
        for row in rows:
            role = interaction.guild.get_role(row["role_id"])
            role_name = role.mention if role else f"Rôle ID {row['role_id']} (introuvable)"
            lines.append(f"Niveau {row['level']} → {role_name}")

        embed = discord.Embed(
            title=_("xp_system.level_roles.title", user_id, guild_id),
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
            await interaction.response.send_message(
                _("commands.level.no_xp", user_id, guild_id), ephemeral=True)
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

        embed = discord.Embed(
            title=_("commands.level.embed_title", user_id, guild_id, user=interaction.user.display_name), 
            color=0x00ff00
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(
            name=_("commands.level.level_field", user_id, guild_id), 
            value=str(level), 
            inline=True
        )
        embed.add_field(
            name=_("commands.level.total_xp_field", user_id, guild_id), 
            value=f"{xp}/{xp_next}", 
            inline=True
        )
        embed.add_field(
            name=_("commands.level.progress_field", user_id, guild_id), 
            value=f"[{bar}] ({progress}/{total_needed})", 
            inline=False
        )
        embed.add_field(
            name=_("commands.level.text_xp_field", user_id, guild_id), 
            value=str(data["text_xp"]), 
            inline=True
        )
        embed.add_field(
            name=_("commands.level.voice_xp_field", user_id, guild_id), 
            value=str(data["voice_xp"]), 
            inline=True
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xpmultiplier", description="Set XP multiplier for events")
    @app_commands.describe(
        multiplier="The multiplier value (e.g., 2.0 for double XP)",
        duration="Duration in minutes (optional, permanent if not specified)",
        event_type="Type of event (text, voice, or both)"
    )
    @app_commands.choices(event_type=[
        app_commands.Choice(name="Text XP", value="text"),
        app_commands.Choice(name="Voice XP", value="voice"),
        app_commands.Choice(name="Both", value="both")
    ])
    async def set_xp_multiplier(self, interaction: discord.Interaction, multiplier: float, 
                               event_type: str, duration: Optional[int] = None):
        """Set XP multiplier for events"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("errors.admin_only", user_id, guild_id),
                ephemeral=True
            )
            return
            
        # Validate multiplier
        if multiplier < 0.1 or multiplier > 10.0:
            await interaction.response.send_message(
                _("xp_system.multiplier.invalid_range", user_id, guild_id),
                ephemeral=True
            )
            return
            
        # Set multiplier
        duration_text = f" for {duration} minutes" if duration else " (permanent)"
        if event_type == "both":
            self.xp_multiplier.set_multiplier(guild_id, "text", multiplier, duration)
            self.xp_multiplier.set_multiplier(guild_id, "voice", multiplier, duration)
            print(f"🔧 XP Multiplier set: {multiplier}x for TEXT and VOICE in guild {guild_id} by {interaction.user.display_name} (ID: {user_id}){duration_text}")
        else:
            self.xp_multiplier.set_multiplier(guild_id, event_type, multiplier, duration)
            print(f"🔧 XP Multiplier set: {multiplier}x for {event_type.upper()} in guild {guild_id} by {interaction.user.display_name} (ID: {user_id}){duration_text}")
            
        # Create response message
        await interaction.response.send_message(
            _("xp_system.multiplier.success", user_id, guild_id, 
              multiplier=multiplier, event_type=event_type, duration=duration_text),
            ephemeral=True
        )

    @app_commands.command(name="xpstats", description="Show detailed XP statistics")
    async def xp_stats(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Show detailed XP statistics for a user"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        target_user = member or interaction.user
        
        try:
            # Get comprehensive XP data
            xp_data = await self.bot.db.query(
                "SELECT * FROM xp_data WHERE guild_id = %s AND user_id = %s",
                (guild_id, target_user.id),
                fetchone=True
            )
            
            if not xp_data:
                await interaction.response.send_message(
                    _("xp_system.stats.no_data", user_id, guild_id, user=target_user.display_name),
                    ephemeral=True
                )
                return
                
            # Get recent activity
            week_ago = datetime.utcnow() - timedelta(days=7)
            try:
                recent_activity = await self.bot.db.query(
                    """SELECT DATE(timestamp) as date, SUM(xp_gained) as daily_xp
                       FROM xp_history 
                       WHERE guild_id = %s AND user_id = %s AND timestamp >= %s
                       GROUP BY DATE(timestamp)
                       ORDER BY date DESC
                       LIMIT 7""",
                    (guild_id, target_user.id, week_ago),
                    fetchall=True
                )
            except Exception as e:
                print(f"Error getting recent activity: {e}")
                recent_activity = []
            
            # Calculate level and progress
            level = self.calculate_level(xp_data["xp"])
            xp_for_current_level = self.calculate_xp_for_level(level)
            xp_for_next_level = self.calculate_xp_for_level(level + 1)
            xp_progress = xp_data["xp"] - xp_for_current_level
            xp_needed = xp_for_next_level - xp_data["xp"]
            
            # Create detailed embed
            embed = discord.Embed(
                title=_("xp_system.stats.title", user_id, guild_id, user=target_user.display_name),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            embed.add_field(
                name=_("xp_system.stats.level_field", user_id, guild_id),
                value=f"**{level}** ({xp_progress}/{xp_for_next_level - xp_for_current_level})",
                inline=True
            )
            embed.add_field(
                name=_("xp_system.stats.total_xp_field", user_id, guild_id),
                value=f"**{xp_data['xp']}** XP",
                inline=True
            )
            embed.add_field(
                name=_("xp_system.stats.xp_needed_field", user_id, guild_id),
                value=f"**{xp_needed}** XP",
                inline=True
            )
            embed.add_field(
                name=_("xp_system.stats.text_xp_field", user_id, guild_id),
                value=f"**{xp_data['text_xp']}** XP",
                inline=True
            )
            embed.add_field(
                name=_("xp_system.stats.voice_xp_field", user_id, guild_id),
                value=f"**{xp_data['voice_xp']}** XP",
                inline=True
            )
            
            # Add recent activity
            if recent_activity:
                activity_text = ""
                for day_data in recent_activity:
                    activity_text += f"**{day_data['date']}**: {day_data['daily_xp']} XP\n"
                embed.add_field(
                    name=_("xp_system.stats.recent_activity_field", user_id, guild_id),
                    value=activity_text,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in XP stats: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
