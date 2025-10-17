import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Literal
from i18n import _
from .command_logger import log_command_usage
from custom_emojis import TROPHY, STAR, GEM, FIRE, ARROW_UP

logger = logging.getLogger(__name__)

class XPMultiplier:
    """XP multiplier system for events and boosts"""
    
    def __init__(self, bot=None):
        self.bot = bot
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
            
    async def get_multiplier(self, guild_id: int, multiplier_type: str = "base") -> float:
        """Get current multiplier for a guild"""
        multiplier = 1.0
        
        # First check database for base multiplier from web dashboard
        if self.bot and multiplier_type in ["text", "voice", "base"]:
            try:
                sql = "SELECT xp_multiplier FROM guild_config WHERE guild_id = %s"
                logger.debug(f"Executing SQL: {sql} with guild_id={guild_id}")
                result = await self.bot.db.query(sql, (str(guild_id),), fetchone=True)
                logger.debug(f"Database result: {result}")
                if result and result.get('xp_multiplier'):
                    multiplier = float(result['xp_multiplier'])
                    logger.debug(f"Using database multiplier {multiplier}x for guild {guild_id}")
                else:
                    logger.debug(f"No result or no xp_multiplier found for guild {guild_id}")
            except Exception as e:
                logger.warning(f"Could not fetch multiplier from database: {e}")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        # Check permanent multipliers (from /xpmultiplier command)
        if guild_id in self.multipliers and multiplier_type in self.multipliers[guild_id]:
            command_multiplier = self.multipliers[guild_id][multiplier_type]
            multiplier = max(multiplier, command_multiplier)  # Use highest multiplier
            print(f"🔢 Using command multiplier {command_multiplier}x for guild {guild_id} (final: {multiplier}x)")
            
        # Check temporary multipliers
        if guild_id in self.temporary_multipliers and multiplier_type in self.temporary_multipliers[guild_id]:
            temp_multiplier, expires_at = self.temporary_multipliers[guild_id][multiplier_type]
            if datetime.utcnow() < expires_at:
                multiplier = max(multiplier, temp_multiplier)  # Use highest multiplier
                print(f"🔢 Using temporary multiplier {temp_multiplier}x for guild {guild_id} (final: {multiplier}x)")
            else:
                # Remove expired multiplier and log it
                print(f"🕐 XP Multiplier for {multiplier_type} in guild {guild_id} has expired (was {temp_multiplier}x)")
                del self.temporary_multipliers[guild_id][multiplier_type]
                
        return multiplier

class SetXPChannelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id):
        super().__init__(title=_('xp_system.modals.set_xp_channel.title', 0, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        
        self.channel_id = discord.ui.TextInput(
            label=_('xp_system.modals.set_xp_channel.channel_id_label', 0, guild_id),
            placeholder=_('xp_system.modals.set_xp_channel.channel_id_placeholder', 0, guild_id),
            style=discord.TextStyle.short
        )
        self.add_item(self.channel_id)

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

class SetRoleLevelModal(discord.ui.Modal):
    def __init__(self, bot, guild_id):
        super().__init__(title=_('xp_system.modals.set_role_level.title', 0, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        
        self.level = discord.ui.TextInput(
            label=_('xp_system.modals.set_role_level.level_label', 0, guild_id),
            placeholder=_('xp_system.modals.set_role_level.level_placeholder', 0, guild_id),
            style=discord.TextStyle.short
        )
        self.add_item(self.level)
        
        self.role_id = discord.ui.TextInput(
            label=_('xp_system.modals.set_role_level.role_id_label', 0, guild_id),
            placeholder=_('xp_system.modals.set_role_level.role_id_placeholder', 0, guild_id),
            style=discord.TextStyle.short
        )
        self.add_item(self.role_id)

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
        
        # Add buttons with translated labels
        self.add_item(discord.ui.Button(
            label=_('xp_system.buttons.set_xp_channel', 0, guild_id),
            style=discord.ButtonStyle.green,
            custom_id="set_xp_channel"
        ))
        self.add_item(discord.ui.Button(
            label=_('xp_system.buttons.set_role_level', 0, guild_id),
            style=discord.ButtonStyle.blurple,
            custom_id="set_role_level"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get("custom_id") == "set_xp_channel":
            modal = SetXPChannelModal(self.bot, self.guild_id)
            await interaction.response.send_modal(modal)
            return True
        elif interaction.data.get("custom_id") == "set_role_level":
            modal = SetRoleLevelModal(self.bot, self.guild_id)
            await interaction.response.send_modal(modal)
            return True
        return False

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}
        self.xp_batch = {}  # For batching XP updates
        self.batch_size = 50  # Process batches of 50 XP updates
        self.xp_multiplier = XPMultiplier(bot)  # XP multiplier system
        logger.info("XPSystem cog loaded")

    def _calculate_level(self, xp: int) -> int:
        """
        Calculate level from XP using a progressive formula that starts easy and becomes gradually harder.
        Formula: level = floor(xp / 200) + floor(sqrt(xp / 500)) + 1
        This creates an easy start with gradual difficulty increase.
        
        Level progression:
        Level 1: 0-199 XP
        Level 2: 200-399 XP  
        Level 3: 400-599 XP
        Level 4: 600-799 XP
        Level 5: 800-999 XP
        Level 10: ~2000 XP
        etc.
        """
        if xp < 0:
            return 1
        import math
        
        # Formule hybride : linéaire au début, puis racine carrée
        linear_part = xp // 200
        sqrt_part = int(math.sqrt(xp / 400))
        
        return linear_part + sqrt_part + 1

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.voice_xp_loop.is_running():
            logger.info("Starting voice XP loop from on_ready")
            self.voice_xp_loop.start()

        
    def cog_unload(self):
        self.voice_xp_loop.cancel()

    @tasks.loop(minutes=10)
    async def voice_xp_loop(self):
        logger.info("Voice XP loop started")

        for guild in self.bot.guilds:
            logger.debug(f"Processing guild: {guild.name} ({guild.id})")

            for vc in guild.voice_channels:
                logger.debug(f"Voice channel: {vc.name} | Members: {len(vc.members)}")

                if len(vc.members) <= 1:
                    logger.debug("Skipped: only 1 person or less in voice")
                    continue

                for member in vc.members:
                    logger.debug(f"Member: {member.display_name} ({member.id})")

                    if member.bot:
                        logger.debug("Skipped: bot user")
                        continue

                    if member.voice.self_mute or member.voice.self_deaf:
                        logger.debug("Skipped: user self-muted/deafened")
                        continue

                    if member.voice.mute or member.voice.deaf:
                        logger.debug("Skipped: server-muted/deafened")
                        continue

                    logger.debug(f"Adding 15 voice XP to {member.display_name}")
                    leveled_up, level = await self.add_xp(member.id, guild.id, 15, source="voice")

                    if leveled_up:
                        logger.info(f"Level up: {member.display_name} reached level {level}")
                        await self.handle_level_up(guild, member, level)

        logger.info("Voice XP loop completed")

    def format_voice_time(self, voice_xp: int) -> str:
        """Convert voice XP to formatted time string (15 XP = 1 minute)"""
        total_minutes = voice_xp // 15
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}min"
        else:
            return f"{minutes}min"
    
    def format_leaderboard_entry(self, rank: int, name: str, value: str, highlight: bool = False) -> str:
        """Format a leaderboard entry with consistent styling"""
        # Medal emojis for top 3
        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f"`#{rank:02d}`"
        
        # Add highlight for special entries
        prefix = "**" if highlight else ""
        suffix = "**" if highlight else ""
        
        return f"{medal} {prefix}{name}{suffix}: {value}\n"

    async def add_xp(self, user_id, guild_id, amount, source="text"):
        """Add XP to a user with improved performance and history tracking"""
        try:
            sql = "SELECT * FROM xp_data WHERE user_id = %s AND guild_id = %s"
            data = await self.bot.db.query(sql, (user_id, guild_id), fetchone=True)

            if not data:
                await self.bot.db.query(
                    "INSERT INTO xp_data (user_id, guild_id, xp, level, text_xp, voice_xp, message_count) VALUES (%s, %s, 0, 1, 0, 0, 0)",
                    (user_id, guild_id)
                )
                data = {"xp": 0, "level": 1, "text_xp": 0, "voice_xp": 0, "message_count": 0}

            # Get guild-specific multipliers
            guild_multiplier = await self.xp_multiplier.get_multiplier(guild_id, source)
            
            # Calculate actual XP gained with multiplier
            base_xp = amount
            actual_xp_gained = int(base_xp * guild_multiplier)
            
            # Apply XP to correct source
            text_xp = data["text_xp"] + actual_xp_gained if source == "text" else data["text_xp"]
            voice_xp = data["voice_xp"] + actual_xp_gained if source == "voice" else data["voice_xp"]
            
            # Increment message count for text messages
            message_count = data.get("message_count", 0)
            if source == "text":
                message_count += 1
            
            # Log XP gain (only for debugging, not spam)
            logger.debug(f"XP gained: {actual_xp_gained} ({source}) - User {user_id} in guild {guild_id}")
            
            new_xp = data["xp"] + actual_xp_gained
            new_level = self._calculate_level(new_xp)
            leveled_up = new_level > data["level"]

            # Update main XP table
            await self.bot.db.query(
                "UPDATE xp_data SET xp=%s, text_xp=%s, voice_xp=%s, message_count=%s, level=%s WHERE user_id=%s AND guild_id=%s",
                (new_xp, text_xp, voice_xp, message_count, new_level, user_id, guild_id)
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
        """Calculate level from total XP - Smoother, slower progression"""
        # New formula: More gradual level progression
        # Level 1: 0 XP, Level 2: 100 XP, Level 3: 250 XP, Level 4: 450 XP, etc.
        if total_xp < 100:
            return 1
        # Use a more gradual cubic root formula for smoother progression
        return int((total_xp / 50) ** 0.4) + 1
        
    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP needed for a specific level"""
        if level <= 1:
            return 0
        # Reverse of the level calculation
        return int(((level - 1) ** 2.5) * 50)
        
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
            xp = 7  # Fixed 7 XP per message
            leveled_up, level = await self.add_xp(user_id, guild_id, xp, source="text")

            if leveled_up:
                await self.handle_level_up(message.guild, message.author, level)

            self.cooldown[key] = True
            await asyncio.sleep(5)  # 5 second cooldown
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
        
        # Check both xp_config and guild_config for level up channel
        xp_config = await self.bot.db.query("SELECT xp_channel FROM xp_config WHERE guild_id = %s", (guild.id,), fetchone=True)
        guild_config = await self.bot.db.query("SELECT level_up_channel, level_up_message FROM guild_config WHERE guild_id = %s", (guild.id,), fetchone=True)
        
        # Determine the channel to use for level up announcements
        level_up_channel = None
        level_up_enabled = True
        
        if guild_config:
            level_up_enabled = guild_config.get("level_up_message", True)
            if guild_config.get("level_up_channel"):
                channel_id = int(guild_config["level_up_channel"])
                level_up_channel = self.bot.get_channel(channel_id)
                logger.debug(f"Using level_up_channel from guild_config: {guild_config['level_up_channel']} (converted to {channel_id})")
                logger.debug(f"Channel object: {level_up_channel}")
        
        if not level_up_channel and xp_config and xp_config.get("xp_channel"):
            channel_id = int(xp_config["xp_channel"])
            level_up_channel = self.bot.get_channel(channel_id)
            logger.debug(f"Using xp_channel from xp_config: {xp_config['xp_channel']} (converted to {channel_id})")
            logger.debug(f"Channel object: {level_up_channel}")
        
        logger.debug(f"Level up - {member.display_name} reached level {level} in {guild.name}")
        logger.debug(f"Level up enabled: {level_up_enabled}, Channel: {level_up_channel}")
        
        gained_roles = []

        # Attribution des rôles - seulement le rôle le plus élevé
        roles = await self.bot.db.query(
            "SELECT role_id, level FROM level_roles WHERE guild_id = %s AND level <= %s ORDER BY level DESC",
            (guild.id, level),
            fetchall=True
        )
        
        # Trouver le rôle de niveau le plus élevé que l'utilisateur devrait avoir
        highest_role = None
        highest_level = 0
        all_level_roles = []
        
        # Récupérer tous les rôles de niveau pour ce serveur
        all_roles_data = await self.bot.db.query(
            "SELECT role_id FROM level_roles WHERE guild_id = %s",
            (guild.id,),
            fetchall=True
        )
        
        for role_data in all_roles_data:
            role = guild.get_role(role_data["role_id"])
            if role:
                all_level_roles.append(role)
        
        # Trouver le rôle le plus élevé à attribuer
        for row in roles:
            role = guild.get_role(row["role_id"])
            if role and row["level"] > highest_level:
                highest_role = role
                highest_level = row["level"]
        
        # Supprimer tous les autres rôles de niveau
        roles_to_remove = [role for role in all_level_roles if role != highest_role and role in member.roles]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Level role cleanup - removing lower roles")
        
        # Attribuer le rôle le plus élevé si l'utilisateur ne l'a pas déjà
        if highest_role and highest_role not in member.roles:
            await member.add_roles(highest_role, reason=f"Level {level} role assignment")
            gained_roles.append(highest_role.mention)

        # Annonce dans le salon s'il est configuré ET si les messages de level up sont activés
        if level_up_enabled and level_up_channel:
            # Get custom level-up message configuration
            level_up_config = await self.bot.db.query(
                "SELECT * FROM level_up_config WHERE guild_id = %s",
                (guild.id,),
                fetchone=True
            )
            
            # Use custom config if available, otherwise use defaults
            if level_up_config and level_up_config.get("enabled", True):
                message_type = level_up_config.get("message_type", "embed")
                
                # Use custom channel if specified
                if level_up_config.get("channel_id"):
                    custom_channel_id = int(level_up_config["channel_id"])
                    custom_channel = self.bot.get_channel(custom_channel_id)
                    if custom_channel:
                        level_up_channel = custom_channel
                
                if message_type == "simple":
                    # Simple text message
                    message_content = level_up_config.get("message_content", "Congratulations {user}! You have reached level {level}!")
                    message_content = message_content.replace("{user}", member.mention).replace("{level}", str(level))
                    
                    try:
                        await level_up_channel.send(message_content)
                        logger.debug(f"Simple level up message sent to {level_up_channel.name}")
                    except Exception as e:
                        logger.warning(f"Failed to send level up message: {e}")
                        
                else:
                    # Embed message with custom configuration
                    embed_title = level_up_config.get("embed_title", "Level Up!")
                    embed_description = level_up_config.get("embed_description", "{user} has reached level **{level}**!")
                    embed_color = level_up_config.get("embed_color", "#FFD700")
                    
                    # Replace placeholders
                    embed_title = embed_title.replace("{user}", member.display_name).replace("{level}", str(level))
                    embed_description = embed_description.replace("{user}", member.mention).replace("{level}", str(level))
                    
                    # Parse color (hex to int)
                    try:
                        if embed_color.startswith("#"):
                            color_int = int(embed_color[1:], 16)
                        else:
                            color_int = int(embed_color, 16)
                        embed_color_obj = discord.Color(color_int)
                    except:
                        embed_color_obj = discord.Color.gold()
                    
                    embed = discord.Embed(
                        title=embed_title,
                        description=embed_description,
                        color=embed_color_obj
                    )
                    
                    # Add thumbnail if specified
                    if level_up_config.get("embed_thumbnail_url"):
                        # Custom thumbnail URL takes priority
                        embed.set_thumbnail(url=level_up_config["embed_thumbnail_url"])
                    elif level_up_config.get("show_user_avatar", True):
                        # Show user avatar only if enabled (default: True)
                        embed.set_thumbnail(url=member.display_avatar.url)
                    # If show_user_avatar is False and no custom thumbnail, no thumbnail is set
                    
                    # Add image if specified
                    if level_up_config.get("embed_image_url"):
                        embed.set_image(url=level_up_config["embed_image_url"])
                    
                    # Add footer if specified
                    if level_up_config.get("embed_footer_text"):
                        embed.set_footer(text=level_up_config["embed_footer_text"])
                    
                    # Add timestamp if enabled
                    if level_up_config.get("embed_timestamp", True):
                        embed.timestamp = discord.utils.utcnow()
                    
                    # Add roles gained field if any
                    if gained_roles:
                        embed.add_field(
                            name="🎖️ Roles Gained",
                            value=", ".join(gained_roles),
                            inline=False
                        )
                    
                    try:
                        await level_up_channel.send(content=f"{member.mention}", embed=embed)
                        logger.debug(f"Custom embed level up message sent to {level_up_channel.name}")
                    except Exception as e:
                        logger.warning(f"Failed to send level up message: {e}")
            else:
                # Default level-up message (fallback)
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

                try:
                    await level_up_channel.send(content=f"{member.mention}", embed=embed)
                    logger.debug(f"Level up message sent to {level_up_channel.name}")
                except Exception as e:
                    logger.warning(f"Failed to send level up message: {e}")
        else:
            logger.debug(f"Level up message not sent - enabled: {level_up_enabled}, channel: {bool(level_up_channel)}")


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

    @app_commands.command(name="xp", description="View your level and XP progress")
    @app_commands.describe(user="User to check XP for (optional)")
    async def xp(self, interaction: discord.Interaction, user: discord.Member = None):
        """Show user's XP, level, and progress with XP bar"""
        target_user = user or interaction.user
        user_id = target_user.id
        guild_id = interaction.guild.id
        
        # Get user XP data from database
        try:
            sql = "SELECT * FROM xp_data WHERE user_id = %s AND guild_id = %s"
            result = await self.bot.db.query(sql, (user_id, guild_id), fetchone=True)
            
            if not result:
                # User has no XP data
                no_xp_msg = _("commands.level.no_xp", user_id, guild_id)
                embed = discord.Embed(
                    title=f"{TROPHY} {_('xp_system.commands.xp.title', user_id, guild_id, user=target_user.display_name)}",
                    description=no_xp_msg,
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
                await interaction.response.send_message(embed=embed)
                return
            
            # Extract XP data
            total_xp = result.get('xp', 0)
            text_xp = result.get('text_xp', 0)
            voice_xp = result.get('voice_xp', 0)
            level = result.get('level', 1)
            
            # Calculate level and progress
            calculated_level = self.calculate_level(total_xp)
            current_level_xp = self.calculate_xp_for_level(calculated_level)
            next_level_xp = self.calculate_xp_for_level(calculated_level + 1)
            xp_needed = next_level_xp - total_xp
            progress_xp = total_xp - current_level_xp
            level_xp_range = next_level_xp - current_level_xp
            
            # Create progress bar
            progress_percentage = progress_xp / level_xp_range if level_xp_range > 0 else 0
            bar_length = 20
            filled_length = int(bar_length * progress_percentage)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            # Create embed
            embed = discord.Embed(
                title=f"{TROPHY} {_('xp_system.commands.xp.title', user_id, guild_id, user=target_user.display_name)}",
                color=discord.Color.blue()
            )
            
            # Add fields
            embed.add_field(
                name=f"{TROPHY} {_('xp_system.commands.xp.level', user_id, guild_id)}",
                value=f"**{calculated_level}**",
                inline=True
            )
            
            embed.add_field(
                name=f"{STAR} {_('xp_system.commands.xp.total_xp', user_id, guild_id)}",
                value=f"**{total_xp:,}** XP",
                inline=True
            )
            
            embed.add_field(
                name=f"{ARROW_UP} {_('xp_system.commands.xp.progress', user_id, guild_id)}",
                value=f"**{progress_xp:,}** / **{level_xp_range:,}** XP\n`{bar}` {progress_percentage:.1%}",
                inline=False
            )
            
            embed.add_field(
                name=f"💬 {_('xp_system.commands.xp.text_xp', user_id, guild_id)}",
                value=f"**{text_xp:,}** XP",
                inline=True
            )
            
            embed.add_field(
                name=f"🎤 {_('xp_system.commands.xp.voice_xp', user_id, guild_id)}",
                value=f"**{voice_xp:,}** XP",
                inline=True
            )
            
            embed.add_field(
                name=_('xp_system.commands.xp.next_level', user_id, guild_id),
                value=f"**{xp_needed:,}** {_('xp_system.commands.xp.xp_needed', user_id, guild_id)}",
                inline=True
            )
            
            embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
            embed.set_footer(text=_('xp_system.commands.xp.footer', user_id, guild_id, level=calculated_level, total_xp=total_xp))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"❌ Error in xp command: {e}")
            await interaction.response.send_message(_('xp_system.commands.xp.error', user_id, guild_id), ephemeral=True)

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
                color = discord.Color.from_rgb(88, 101, 242)  # Discord blurple
                title_emoji = "💬"
                title_suffix = f" {title_emoji} {_('xp_system.leaderboard.types.text', user_id, guild_id)}"
            elif type == "voice":
                query = """SELECT user_id, SUM(xp_gained) as weekly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'voice'
                           GROUP BY user_id
                           ORDER BY weekly_xp DESC
                           LIMIT 10"""
                color = discord.Color.from_rgb(87, 242, 135)  # Bright green
                title_emoji = "🎤"
                title_suffix = f" {title_emoji} {_('xp_system.leaderboard.types.voice', user_id, guild_id)}"
            else:  # total
                query = """SELECT user_id, SUM(xp_gained) as weekly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s
                           GROUP BY user_id
                           ORDER BY weekly_xp DESC
                           LIMIT 10"""
                color = discord.Color.from_rgb(255, 215, 0)  # Gold
                title_emoji = "📊"
                title_suffix = f" {title_emoji} Total"
            
            logger.debug(f"Weekly Leaderboard Debug - Type: {type}, Guild: {guild_id}")
            weekly_data = await self.bot.db.query(query, (guild_id, week_ago), fetchall=True)
            
            if not weekly_data:
                await interaction.response.send_message(
                    _("xp_system.weekly_leaderboard.no_data", user_id, guild_id),
                    ephemeral=True
                )
                return
                
            # Create embed
            embed = discord.Embed(
                title=f"📅 {_('xp_system.weekly_leaderboard.title', user_id, guild_id)}{title_suffix}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, data in enumerate(weekly_data, 1):
                user = self.bot.get_user(data["user_id"])
                username = user.display_name if user else _('xp_system.leaderboard.unknown_user', user_id, guild_id)
                
                xp_value = data['weekly_xp']
                
                # Format display based on type
                if type == "text":
                    # Estimate messages from XP (average 10-20 XP per message, use 15)
                    est_messages = xp_value // 15
                    display_value = f"~**{est_messages:,}** messages `({xp_value:,} XP)`"
                elif type == "voice":
                    voice_time = self.format_voice_time(xp_value)
                    display_value = f"**{voice_time}** `({xp_value:,} XP)`"
                else:  # total
                    display_value = f"**{xp_value:,}** XP"
                
                leaderboard_text += self.format_leaderboard_entry(i, username, display_value)
                
            embed.description = leaderboard_text
            embed.set_footer(text=f"⏱️ {_('xp_system.weekly_leaderboard.footer', user_id, guild_id)} • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
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
                color = discord.Color.from_rgb(88, 101, 242)  # Discord blurple
                title_emoji = "💬"
                title_suffix = f" {title_emoji} {_('xp_system.leaderboard.types.text', user_id, guild_id)}"
            elif type == "voice":
                query = """SELECT user_id, SUM(xp_gained) as monthly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'voice'
                           GROUP BY user_id
                           ORDER BY monthly_xp DESC
                           LIMIT 10"""
                color = discord.Color.from_rgb(87, 242, 135)  # Bright green
                title_emoji = "🎤"
                title_suffix = f" {title_emoji} {_('xp_system.leaderboard.types.voice', user_id, guild_id)}"
            else:  # total
                query = """SELECT user_id, SUM(xp_gained) as monthly_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND timestamp >= %s
                           GROUP BY user_id
                           ORDER BY monthly_xp DESC
                           LIMIT 10"""
                color = discord.Color.from_rgb(255, 215, 0)  # Gold
                title_emoji = "📊"
                title_suffix = f" {title_emoji} Total"
            
            logger.debug(f"Monthly Leaderboard Debug - Type: {type}, Guild: {guild_id}")
            monthly_data = await self.bot.db.query(query, (guild_id, month_ago), fetchall=True)
            
            if not monthly_data:
                await interaction.response.send_message(
                    _("xp_system.monthly_leaderboard.no_data", user_id, guild_id),
                    ephemeral=True
                )
                return
                
            # Create embed
            embed = discord.Embed(
                title=f"📅 {_('xp_system.monthly_leaderboard.title', user_id, guild_id)}{title_suffix}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, data in enumerate(monthly_data, 1):
                user = self.bot.get_user(data["user_id"])
                username = user.display_name if user else _('xp_system.leaderboard.unknown_user', user_id, guild_id)
                
                xp_value = data['monthly_xp']
                
                # Format display based on type
                if type == "text":
                    # Estimate messages from XP (average 10-20 XP per message, use 15)
                    est_messages = xp_value // 15
                    display_value = f"~**{est_messages:,}** messages `({xp_value:,} XP)`"
                elif type == "voice":
                    voice_time = self.format_voice_time(xp_value)
                    display_value = f"**{voice_time}** `({xp_value:,} XP)`"
                else:  # total
                    display_value = f"**{xp_value:,}** XP"
                
                leaderboard_text += self.format_leaderboard_entry(i, username, display_value)
                
            embed.description = leaderboard_text
            embed.set_footer(text=f"⏱️ {_('xp_system.monthly_leaderboard.footer', user_id, guild_id)} • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
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
                field_name = f"{STAR} {_('xp_system.leaderboard.types.total', user_id, guild_id)}"
                color = discord.Color.from_rgb(255, 215, 0)  # Gold
                title_emoji = "📊"
                xp_field = "xp"
            elif type == "text":
                query = """SELECT user_id, text_xp, message_count FROM xp_data WHERE guild_id = %s ORDER BY text_xp DESC LIMIT 10"""
                field_name = f"💬 {_('xp_system.leaderboard.types.text', user_id, guild_id)}"
                color = discord.Color.from_rgb(88, 101, 242)  # Discord blurple
                title_emoji = "💬"
                xp_field = "text_xp"
            else:  # voice
                query = """SELECT user_id, voice_xp FROM xp_data WHERE guild_id = %s ORDER BY voice_xp DESC LIMIT 10"""
                field_name = f"🎤 {_('xp_system.leaderboard.types.voice', user_id, guild_id)}"
                color = discord.Color.from_rgb(87, 242, 135)  # Bright green
                title_emoji = "🎤"
                xp_field = "voice_xp"
            
            rows = await self.bot.db.query(query, (guild_id,), fetchall=True)
            
            # Debug: Show what data was retrieved
            logger.debug(f"Leaderboard Debug - Type: {type}, Guild: {guild_id}")
            
            if not rows:
                await interaction.response.send_message(
                    _("commands.topxp.no_data", user_id, guild_id), 
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"🏆 {_('xp_system.alltime_leaderboard.title', user_id, guild_id, type=type.title())} {title_emoji}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, row in enumerate(rows, 1):
                member = interaction.guild.get_member(row["user_id"])
                name = member.display_name if member else _('xp_system.leaderboard.unknown_user', user_id, guild_id)
                
                # Format display based on type
                if type == "text":
                    # Show message count and XP in parentheses
                    msg_count = row.get("message_count", 0)
                    xp_value = row[xp_field]
                    display_value = f"**{msg_count:,}** messages `({xp_value:,} XP)`"
                elif type == "voice":
                    # Show voice time and XP in parentheses
                    xp_value = row[xp_field]
                    voice_time = self.format_voice_time(xp_value)
                    display_value = f"**{voice_time}** `({xp_value:,} XP)`"
                else:  # total
                    # Just show total XP
                    display_value = f"**{row[xp_field]:,}** XP"
                
                leaderboard_text += self.format_leaderboard_entry(i, name, display_value)
            
            embed.description = leaderboard_text
            embed.set_footer(text=f"⏱️ {_('commands.topxp.embed_footer', user_id, guild_id)} • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
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
    @log_command_usage
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
            role_name = role.mention if role else _('xp_system.level_roles.role_not_found', user_id, guild_id, role_id=row['role_id'])
            lines.append(_('xp_system.level_roles.level_role_format', user_id, guild_id, level=row['level'], role=role_name))

        embed = discord.Embed(
            title=_("xp_system.level_roles.title", user_id, guild_id),
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    # synclevelroles command removed - level roles are now handled automatically

        
    # Removed redundant /level command - now using enhanced /xp command from enhanced_xp.py
    # Removed redundant /xpstats command - now using enhanced /xp command with detailed:True from enhanced_xp.py

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
