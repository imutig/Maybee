import discord
from discord.ext import commands
from discord import app_commands
from i18n import _
import logging
import os

logger = logging.getLogger(__name__)

class Cache(commands.Cog):
    """Cache management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="cachestats", description="Display cache statistics")
    async def cache_stats(self, interaction: discord.Interaction):
        """Display cache statistics"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("errors.admin_only", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            stats = self.bot.cache.get_stats()
            
            embed = discord.Embed(
                title=_("cache.stats.title", user_id, guild_id),
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # User preferences cache
            user_stats = stats['user_preferences']
            embed.add_field(
                name=_("cache.stats.user_preferences", user_id, guild_id),
                value=_("cache.stats.cache_info", user_id, guild_id,
                       size=user_stats['size'],
                       hits=user_stats['hits'],
                       misses=user_stats['misses'],
                       hit_rate=user_stats['hit_rate']),
                inline=False
            )
            
            # Configuration cache
            config_stats = stats['configuration']
            embed.add_field(
                name=_("cache.stats.configuration", user_id, guild_id),
                value=_("cache.stats.cache_info", user_id, guild_id,
                       size=config_stats['size'],
                       hits=config_stats['hits'],
                       misses=config_stats['misses'],
                       hit_rate=config_stats['hit_rate']),
                inline=False
            )
            
            # Leaderboards cache (persistent)
            leaderboard_stats = stats['leaderboards']
            embed.add_field(
                name=_("cache.stats.leaderboards", user_id, guild_id),
                value=_("cache.stats.cache_info_persistent", user_id, guild_id,
                       size=leaderboard_stats['size'],
                       hits=leaderboard_stats['hits'],
                       misses=leaderboard_stats['misses'],
                       hit_rate=leaderboard_stats['hit_rate']),
                inline=False
            )
            
            # General cache
            general_stats = stats['general']
            embed.add_field(
                name=_("cache.stats.general", user_id, guild_id),
                value=_("cache.stats.cache_info", user_id, guild_id,
                       size=general_stats['size'],
                       hits=general_stats['hits'],
                       misses=general_stats['misses'],
                       hit_rate=general_stats['hit_rate']),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )
            
    @app_commands.command(name="clearcache", description="Clear all caches")
    async def clear_cache(self, interaction: discord.Interaction):
        """Clear all caches"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("errors.admin_only", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            self.bot.cache.clear_all()
            await interaction.response.send_message(
                _("cache.clear.success", user_id, guild_id),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )

    @app_commands.command(name="cacheinfo", description="Display detailed cache information")
    async def cache_info(self, interaction: discord.Interaction):
        """Display detailed cache information including persistence status"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                _("errors.admin_only", user_id, guild_id),
                ephemeral=True
            )
            return
            
        try:
            embed = discord.Embed(
                title="🔧 Cache System Information",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            # Persistent cache info
            embed.add_field(
                name="💾 Persistent Storage",
                value=f"**Leaderboards Cache**: `cache_data/leaderboards.json`\n"
                      f"**Status**: {'✅ Active' if hasattr(self.bot.cache.leaderboards, 'persist_file') else '❌ Disabled'}\n"
                      f"**TTL**: 30 minutes (survives bot restarts)",
                inline=False
            )
            
            # Cache directory info
            cache_dir = "cache_data"
            if os.path.exists(cache_dir):
                files = os.listdir(cache_dir)
                embed.add_field(
                    name="📁 Cache Files",
                    value=f"**Directory**: `{cache_dir}/`\n" + 
                          (f"**Files**: {', '.join(files)}" if files else "**Files**: None"),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📁 Cache Files",
                    value="**Directory**: Not created yet",
                    inline=False
                )
            
            # Performance notes
            embed.add_field(
                name="⚡ Performance Notes",
                value="• Weekly/Monthly leaderboards persist across bot restarts\n"
                      "• User preferences cached for 10 minutes\n"
                      "• Configuration cached for 5 minutes\n"
                      "• General cache is memory-only (faster but not persistent)",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", user_id, guild_id),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Cache(bot))
