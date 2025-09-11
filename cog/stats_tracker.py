"""
Système de tracking des statistiques pour les graphiques du dashboard
"""
import discord
from discord.ext import commands, tasks
import logging
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

class StatsTracker(commands.Cog):
    """Cog pour tracker les statistiques des serveurs"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        
        # Démarrer le tracking automatique
        self.member_count_tracker.start()
        self.message_tracker.start()
    
    def cog_unload(self):
        """Arrêter les tâches quand le cog est déchargé"""
        self.member_count_tracker.cancel()
        self.message_tracker.cancel()
    
    @tasks.loop(minutes=5)
    async def member_count_tracker(self):
        """Enregistre le nombre de membres toutes les 5 minutes"""
        try:
            for guild in self.bot.guilds:
                try:
                    # Compter les membres (humains seulement)
                    human_count = sum(1 for member in guild.members if not member.bot)
                    bot_count = sum(1 for member in guild.members if member.bot)
                    total_count = guild.member_count
                    
                    # Enregistrer dans la base de données
                    await self.db.query(
                        """INSERT INTO member_count_history 
                           (guild_id, member_count, bot_count, human_count, recorded_at)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                           member_count = VALUES(member_count),
                           bot_count = VALUES(bot_count),
                           human_count = VALUES(human_count)""",
                        (guild.id, total_count, bot_count, human_count, datetime.now(timezone.utc))
                    )
                    
                    logger.debug(f"📊 Member count recorded for {guild.name}: {human_count} humans, {bot_count} bots")
                    
                except Exception as e:
                    logger.error(f"❌ Error recording member count for {guild.name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in member_count_tracker: {e}")
    
    @member_count_tracker.before_loop
    async def before_member_count_tracker(self):
        """Attendre que le bot soit prêt avant de démarrer le tracking"""
        await self.bot.wait_until_ready()
        logger.info("📊 Member count tracker started")
    
    @tasks.loop(minutes=1)
    async def message_tracker(self):
        """Enregistre les statistiques de messages toutes les minutes"""
        try:
            # Cette tâche sera implémentée plus tard si nécessaire
            # Pour l'instant, on se concentre sur le member_count_tracker
            pass
        except Exception as e:
            logger.error(f"❌ Error in message_tracker: {e}")
    
    @message_tracker.before_loop
    async def before_message_tracker(self):
        """Attendre que le bot soit prêt avant de démarrer le tracking"""
        await self.bot.wait_until_ready()
        logger.info("📊 Message tracker started")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Enregistrer les messages dans la table messages"""
        if message.author.bot or not message.guild:
            return
        
        try:
            await self.db.query(
                """INSERT INTO messages 
                   (message_id, user_id, guild_id, channel_id, content, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE content = VALUES(content)""",
                (message.id, message.author.id, message.guild.id, message.channel.id, 
                 message.content[:1000] if message.content else None, datetime.now(timezone.utc))
            )
            
            logger.debug(f"📝 Message logged: {message.author.name} in {message.guild.name}")
            
        except Exception as e:
            logger.error(f"❌ Error logging message: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Enregistrer les nouveaux membres dans la table members"""
        try:
            await self.db.query(
                """INSERT INTO members 
                   (user_id, guild_id, username, joined_at, created_at)
                   VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE 
                   username = VALUES(username),
                   joined_at = VALUES(joined_at)""",
                (member.id, member.guild.id, member.display_name, 
                 datetime.now(timezone.utc), datetime.now(timezone.utc))
            )
            
            logger.debug(f"👋 Member logged: {member.display_name} joined {member.guild.name}")
            
        except Exception as e:
            logger.error(f"❌ Error logging member join: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Marquer les membres qui quittent dans la table members"""
        try:
            await self.db.query(
                """UPDATE members 
                   SET left_at = %s, updated_at = %s
                   WHERE user_id = %s AND guild_id = %s""",
                (datetime.now(timezone.utc), datetime.now(timezone.utc), 
                 member.id, member.guild.id)
            )
            
            logger.debug(f"👋 Member logged: {member.display_name} left {member.guild.name}")
            
        except Exception as e:
            logger.error(f"❌ Error logging member leave: {e}")
    
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        """Enregistrer l'utilisation des commandes dans la table command_logs"""
        if not interaction.guild:
            return
        
        try:
            await self.db.query(
                """INSERT INTO command_logs 
                   (user_id, guild_id, command_name, created_at)
                   VALUES (%s, %s, %s, %s)""",
                (interaction.user.id, interaction.guild.id, command.name, datetime.now(timezone.utc))
            )
            
            logger.debug(f"⚡ Command logged: {command.name} by {interaction.user.name}")
            
        except Exception as e:
            logger.error(f"❌ Error logging command: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Enregistrer le nombre initial de membres au démarrage"""
        try:
            logger.info("📊 Recording initial member counts...")
            
            for guild in self.bot.guilds:
                try:
                    human_count = sum(1 for member in guild.members if not member.bot)
                    bot_count = sum(1 for member in guild.members if member.bot)
                    total_count = guild.member_count
                    
                    await self.db.query(
                        """INSERT INTO member_count_history 
                           (guild_id, member_count, bot_count, human_count, recorded_at)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                           member_count = VALUES(member_count),
                           bot_count = VALUES(bot_count),
                           human_count = VALUES(human_count)""",
                        (guild.id, total_count, bot_count, human_count, datetime.now(timezone.utc))
                    )
                    
                    logger.info(f"📊 Initial count for {guild.name}: {human_count} humans, {bot_count} bots")
                    
                except Exception as e:
                    logger.error(f"❌ Error recording initial count for {guild.name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in on_ready member count recording: {e}")

async def setup(bot):
    await bot.add_cog(StatsTracker(bot))

