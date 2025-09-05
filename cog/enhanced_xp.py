"""
Enhanced XP System with batch operations and improved performance
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from collections import defaultdict, deque
from services import handle_errors, rate_limit, ValidationMixin, DatabaseError
from monitoring import profile_performance

logger = logging.getLogger(__name__)

class XPBatchProcessor:
    """Batch processor for XP updates to improve database performance"""
    
    def __init__(self, database, batch_size: int = 100):
        self.database = database
        self.batch_size = batch_size
        self.pending_updates: Dict[str, Dict] = {}  # user_guild_key -> update_data
        self.batch_queue = asyncio.Queue()
        self.processing = False
        
    async def add_xp_update(self, user_id: int, guild_id: int, xp_gain: int, source: str = "message"):
        """Add an XP update to the batch queue"""
        key = f"{user_id}_{guild_id}"
        
        if key in self.pending_updates:
            # Accumulate XP for existing entry
            self.pending_updates[key]['xp_gain'] += xp_gain
            self.pending_updates[key]['last_update'] = datetime.now()
        else:
            # Create new entry
            self.pending_updates[key] = {
                'user_id': user_id,
                'guild_id': guild_id,
                'xp_gain': xp_gain,
                'source': source,
                'last_update': datetime.now()
            }
        
        # Process batch if we've reached the size limit
        if len(self.pending_updates) >= self.batch_size:
            await self.process_batch()
    
    @profile_performance("xp_batch_process")
    async def process_batch(self):
        """Process the current batch of XP updates"""
        if not self.pending_updates or self.processing:
            return
        
        self.processing = True
        updates_to_process = list(self.pending_updates.values())
        self.pending_updates.clear()
        
        try:
            # Group updates by guild for better performance
            guild_updates = defaultdict(list)
            for update in updates_to_process:
                guild_updates[update['guild_id']].append(update)
            
            level_ups = []
            
            for guild_id, guild_update_list in guild_updates.items():
                # Batch process updates for this guild
                batch_level_ups = await self._process_guild_batch(guild_id, guild_update_list)
                level_ups.extend(batch_level_ups)
            
            logger.info(f"Processed batch of {len(updates_to_process)} XP updates, {len(level_ups)} level ups")
            return level_ups
            
        except Exception as e:
            logger.error(f"Error processing XP batch: {e}")
            # Re-add failed updates back to queue
            for update in updates_to_process:
                key = f"{update['user_id']}_{update['guild_id']}"
                self.pending_updates[key] = update
        finally:
            self.processing = False
    
    async def _process_guild_batch(self, guild_id: int, updates: List[Dict]) -> List[Tuple]:
        """Process XP updates for a specific guild"""
        try:
            # Prepare batch update query
            user_ids = [update['user_id'] for update in updates]
            
            # Get current XP values for all users in batch
            current_xp_query = """
                SELECT user_id, xp, level FROM user_xp 
                WHERE guild_id = %s AND user_id IN ({})
            """.format(','.join(['%s'] * len(user_ids)))
            
            current_xp_results = await self.database.query(
                current_xp_query, 
                [guild_id] + user_ids,
                fetchall=True
            )
            
            # Create lookup for current XP
            current_xp = {row[0]: {'xp': row[1], 'level': row[2]} for row in current_xp_results}
            
            # Prepare batch insert/update
            batch_operations = []
            level_ups = []
            
            for update in updates:
                user_id = update['user_id']
                xp_gain = update['xp_gain']
                
                if user_id in current_xp:
                    # Update existing record
                    old_xp = current_xp[user_id]['xp']
                    old_level = current_xp[user_id]['level']
                    new_xp = old_xp + xp_gain
                    new_level = self._calculate_level(new_xp)
                    
                    batch_operations.append({
                        'type': 'update',
                        'user_id': user_id,
                        'guild_id': guild_id,
                        'old_xp': old_xp,
                        'new_xp': new_xp,
                        'old_level': old_level,
                        'new_level': new_level
                    })
                    
                    if new_level > old_level:
                        level_ups.append((user_id, guild_id, old_level, new_level))
                else:
                    # Insert new record
                    new_level = self._calculate_level(xp_gain)
                    batch_operations.append({
                        'type': 'insert',
                        'user_id': user_id,
                        'guild_id': guild_id,
                        'new_xp': xp_gain,
                        'new_level': new_level
                    })
                    
                    if new_level > 0:
                        level_ups.append((user_id, guild_id, 0, new_level))
            
            # Execute batch operations
            await self._execute_batch_operations(batch_operations)
            
            return level_ups
            
        except Exception as e:
            logger.error(f"Error processing guild batch for guild {guild_id}: {e}")
            raise
    
    async def _execute_batch_operations(self, operations: List[Dict]):
        """Execute batch database operations"""
        if not operations:
            return
        
        # Separate updates and inserts
        updates = [op for op in operations if op['type'] == 'update']
        inserts = [op for op in operations if op['type'] == 'insert']
        
        try:
            # Batch updates
            if updates:
                update_query = """
                    UPDATE user_xp SET xp = %s, level = %s, last_message = NOW() 
                    WHERE user_id = %s AND guild_id = %s
                """
                update_params = [
                    (op['new_xp'], op['new_level'], op['user_id'], op['guild_id'])
                    for op in updates
                ]
                await self.database.execute_many(update_query, update_params)
            
            # Batch inserts
            if inserts:
                insert_query = """
                    INSERT INTO user_xp (user_id, guild_id, xp, level, last_message)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE 
                    xp = VALUES(xp), level = VALUES(level), last_message = VALUES(last_message)
                """
                insert_params = [
                    (op['user_id'], op['guild_id'], op['new_xp'], op['new_level'])
                    for op in inserts
                ]
                await self.database.execute_many(insert_query, insert_params)
                
        except Exception as e:
            logger.error(f"Error executing batch operations: {e}")
            raise
    
    def _calculate_level(self, xp: int) -> int:
        """
        Calculate level from XP using a progressive formula that starts easy and becomes gradually harder.
        Formula: level = floor(xp / 200) + floor(sqrt(xp / 500)) + 1
        This creates an easy start with gradual difficulty increase.
        """
        if xp < 0:
            return 1
        import math
        
        # Formule hybride : linéaire au début, puis racine carrée
        linear_part = xp // 200
        sqrt_part = int(math.sqrt(xp / 400))
        
        return linear_part + sqrt_part + 1
    
    async def force_process(self):
        """Force process any pending updates"""
        if self.pending_updates:
            await self.process_batch()

class EnhancedXPSystem(commands.Cog, ValidationMixin):
    """Enhanced XP System with batch processing and better performance"""
    
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.batch_processor = None
        self.voice_cooldowns = {}
        
        # Performance tracking
        self.xp_events_processed = 0
        self.level_ups_today = 0
        
        logger.info("Enhanced XP System loaded")
    
    async def cog_load(self):
        """Initialize batch processor when cog is loaded"""
        if hasattr(self.bot, 'db'):
            self.batch_processor = XPBatchProcessor(self.bot.db, batch_size=50)
            # Start periodic batch processing
            self.periodic_batch_process.start()
            logger.info("XP batch processor initialized")
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        if hasattr(self, 'periodic_batch_process'):
            self.periodic_batch_process.cancel()
        if hasattr(self, 'voice_xp_loop'):
            self.voice_xp_loop.cancel()
    
    @tasks.loop(seconds=30)
    async def periodic_batch_process(self):
        """Periodically process pending XP updates"""
        if self.batch_processor:
            try:
                await self.batch_processor.force_process()
            except Exception as e:
                logger.error(f"Error in periodic batch process: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle XP gain from messages with rate limiting"""
        if message.author.bot or not message.guild:
            return
        
        user_id = message.author.id
        guild_id = message.guild.id
        
        # Check cooldown (5 minutes)
        cooldown_key = f"{user_id}_{guild_id}"
        current_time = datetime.now()
        
        if cooldown_key in self.cooldowns:
            if current_time - self.cooldowns[cooldown_key] < timedelta(minutes=5):
                return
        
        self.cooldowns[cooldown_key] = current_time
        
        # Generate XP gain (10-25 XP per message)
        import random
        xp_gain = random.randint(10, 25)
        
        # Add to batch processor
        if self.batch_processor:
            try:
                await self.batch_processor.add_xp_update(user_id, guild_id, xp_gain, "message")
                self.xp_events_processed += 1
            except Exception as e:
                logger.error(f"Error adding XP update to batch: {e}")
    
    @app_commands.command(name="xp", description="Check your XP and level with detailed statistics")
    @app_commands.describe(
        user="User to check XP for (defaults to yourself)",
        detailed="Show detailed statistics including recent activity"
    )
    @handle_errors
    @rate_limit(cooldown=10)
    async def check_xp(self, interaction: discord.Interaction, 
                      user: Optional[discord.Member] = None, 
                      detailed: bool = False):
        """Check XP and level for a user with optional detailed statistics"""
        target_user = user or interaction.user
        
        try:
            # Force process any pending updates for this user
            if self.batch_processor:
                await self.batch_processor.force_process()
            
            # Get XP data - try new enhanced table first, fallback to old table
            xp_data = None
            try:
                xp_data = await self.bot.db.query(
                    "SELECT xp, level, text_xp, voice_xp FROM user_xp WHERE user_id = %s AND guild_id = %s",
                    (target_user.id, interaction.guild.id),
                    fetchone=True
                )
            except:
                # Fallback to old table structure
                try:
                                    xp_data = await self.bot.db.query(
                    "SELECT xp, level, text_xp, voice_xp FROM xp_data WHERE user_id = %s AND guild_id = %s",
                    (target_user.id, interaction.guild.id),
                    fetchone=True
                )
                except:
                    pass
            
            if not xp_data:
                embed = discord.Embed(
                    title="📊 XP Status",
                    description=f"{target_user.mention} has no XP yet!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            current_xp, level, text_xp, voice_xp = xp_data
            next_level_xp = self._calculate_xp_for_level(level + 1)
            current_level_xp = self._calculate_xp_for_level(level)
            progress_xp = current_xp - current_level_xp
            needed_xp = next_level_xp - current_level_xp
            xp_needed_for_next = next_level_xp - current_xp
            
            # Create progress bar
            progress_percentage = (progress_xp / needed_xp) * 100 if needed_xp > 0 else 100
            progress_bar = self._create_progress_bar(progress_percentage)
            
            # Create embed
            color = discord.Color.gold() if detailed else discord.Color.blue()
            title = "📊 Detailed XP Statistics" if detailed else "📊 XP Status"
            
            embed = discord.Embed(
                title=title,
                color=color,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Basic information
            embed.add_field(
                name="👤 User",
                value=target_user.mention,
                inline=True
            )
            embed.add_field(
                name="🏆 Level",
                value=f"**{level}**",
                inline=True
            )
            embed.add_field(
                name="⭐ Total XP",
                value=f"**{current_xp:,}** XP",
                inline=True
            )
            
            # Progress information
            embed.add_field(
                name="📈 Progress to Next Level",
                value=f"{progress_bar}\n**{progress_xp:,}** / **{needed_xp:,}** XP ({progress_percentage:.1f}%)",
                inline=False
            )
            
            if detailed:
                # Detailed statistics
                embed.add_field(
                    name="📝 Text XP",
                    value=f"**{text_xp:,}** XP",
                    inline=True
                )
                embed.add_field(
                    name="🎤 Voice XP", 
                    value=f"**{voice_xp:,}** XP",
                    inline=True
                )
                embed.add_field(
                    name="🎯 XP Needed",
                    value=f"**{xp_needed_for_next:,}** XP",
                    inline=True
                )
                
                # Try to get recent activity if available
                try:
                    week_ago = datetime.now() - timedelta(days=7)
                    recent_activity = await self.bot.db.query(
                        """SELECT DATE(timestamp) as date, SUM(xp_gained) as daily_xp
                           FROM xp_history 
                           WHERE guild_id = %s AND user_id = %s AND timestamp >= %s
                           GROUP BY DATE(timestamp)
                           ORDER BY date DESC
                           LIMIT 5""",
                        (interaction.guild.id, target_user.id, week_ago),
                        fetchall=True
                    )
                    
                    if recent_activity:
                        activity_text = ""
                        for day_data in recent_activity:
                            activity_text += f"**{day_data[0]}**: {day_data[1]} XP\n"
                        
                        embed.add_field(
                            name="📅 Recent Activity (Last 5 Days)",
                            value=activity_text,
                            inline=False
                        )
                except Exception as e:
                    logger.debug(f"Could not fetch recent activity: {e}")
                
                embed.set_footer(text="💡 Use '/xp detailed:False' for a quick overview")
            else:
                # Quick stats for non-detailed view
                embed.add_field(
                    name="📝 Text XP",
                    value=f"{text_xp:,}",
                    inline=True
                )
                embed.add_field(
                    name="🎤 Voice XP",
                    value=f"{voice_xp:,}",
                    inline=True
                )
                embed.add_field(
                    name="🎯 XP Needed",
                    value=f"{xp_needed_for_next:,}",
                    inline=True
                )
                embed.set_footer(text="💡 Use '/xp detailed:True' for detailed statistics")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in check_xp command: {e}")
            raise DatabaseError("Failed to retrieve XP data")
    
    @app_commands.command(name="leaderboard", description="Show the server XP leaderboard")
    @handle_errors
    @rate_limit(cooldown=30)
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1):
        """Show XP leaderboard with pagination"""
        try:
            # Force process pending updates
            if self.batch_processor:
                await self.batch_processor.force_process()
            
            page = max(1, page)  # Ensure page is at least 1
            offset = (page - 1) * 10
            
            # Get leaderboard data
            leaderboard_data = await self.bot.db.query("""
                SELECT user_id, xp, level 
                FROM user_xp 
                WHERE guild_id = %s 
                ORDER BY level DESC, xp DESC 
                LIMIT 10 OFFSET %s
            """, (interaction.guild.id, offset), fetchall=True)
            
            # Get total count for pagination
            total_count = await self.bot.db.query(
                "SELECT COUNT(*) FROM user_xp WHERE guild_id = %s",
                (interaction.guild.id,),
                fetchone=True
            )
            total_pages = (total_count[0] + 9) // 10 if total_count else 1
            
            embed = discord.Embed(
                title=f"🏆 XP Leaderboard - Page {page}/{total_pages}",
                color=discord.Color.gold()
            )
            
            if not leaderboard_data:
                embed.description = "No XP data found for this server."
            else:
                description = ""
                for i, (user_id, xp, level) in enumerate(leaderboard_data, start=offset + 1):
                    user = interaction.guild.get_member(user_id)
                    username = user.display_name if user else f"User {user_id}"
                    
                    # Add medal for top 3
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    else:
                        medal = f"**{i}.**"
                    
                    description += f"{medal} {username} - Level {level} ({xp:,} XP)\n"
                
                embed.description = description
            
            embed.set_footer(text=f"Page {page} of {total_pages}")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            raise DatabaseError("Failed to retrieve leaderboard data")
    
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate total XP required for a specific level"""
        if level <= 0:
            return 0
        return sum(i * 100 for i in range(1, level + 1))
    
    def _create_progress_bar(self, percentage: float, length: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int(length * percentage / 100)
        empty = length - filled
        return f"{'█' * filled}{'░' * empty}"

async def setup(bot):
    await bot.add_cog(EnhancedXPSystem(bot))
