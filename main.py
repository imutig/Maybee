import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
from datetime import datetime
from db import Database
from cache import BotCache
from cog.ticket import TicketPanelView, TicketCloseView
from dotenv import load_dotenv
from i18n import i18n, _
from services import ServiceContainer, BotConfig, RateLimitManager, handle_errors, rate_limit
from monitoring import initialize_monitoring, get_health_checker, profile_performance

# Setup enhanced logging with Unicode support
import sys
import re

# Create a custom stream handler that handles Unicode properly
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Replace all non-ASCII characters with '?' for console safety
            msg = re.sub(r'[^\x00-\x7F]+', '?', msg)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure logging with Unicode-safe handlers
logging.basicConfig(
    level=logging.DEBUG,  # Temporairement activé pour debug Disboard
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        UnicodeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========== Configuration du bot ==========

load_dotenv()

# Load configuration from environment
try:
    config = BotConfig.from_env()
    logger.info("Configuration loaded successfully")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    exit(1)

TOKEN = config.discord_token
PREFIX = "?"
CATEGORY = "Tickets 🔖"

# =========== Fonctions YAML ==========

class MyBot(commands.Bot):

    def __init__(self, config: BotConfig):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        # Store configuration and start time
        self.config = config
        self.start_time = datetime.now()
        
        # Initialize service container
        self.services = ServiceContainer()
        
        # Setup core services
        self.db = Database(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            db=config.db_name,
            debug=config.debug_mode
        )
        self.cache = BotCache(self.db)
        self.i18n = i18n
        self.rate_limiter = RateLimitManager()
        
        # Register services in container
        self.services.register('database', self.db)
        self.services.register('cache', self.cache)
        self.services.register('i18n', self.i18n)
        self.services.register('rate_limiter', self.rate_limiter)
        self.services.register('config', config)
        
        # Initialize monitoring
        self.health_checker = initialize_monitoring(self, self.db, self.cache)
        self.services.register('health_checker', self.health_checker)
        
        # Legacy attributes for backward compatibility
        self.role_reactions = {}

    async def close(self):
        logger.info("Shutting down bot...")
        
        # Stop monitoring
        if self.health_checker:
            await self.health_checker.stop_monitoring()
            logger.info("Health monitoring stopped")
        
        # Stop cache cleanup
        await self.cache.stop_cleanup_task()
        logger.info("Cache cleanup stopped")
        
        # Close database
        await self.db.close()
        logger.info("Database connection closed")
        
        await super().close()
        logger.info("Bot shutdown complete")

    @profile_performance("setup_hook")
    async def setup_hook(self):
        try:
            await self.db.connect()
            logger.info("Database connected successfully")
            
            await self.db.init_tables()
            logger.info("Database tables initialized")
            
            # Load language preferences from database
            await self.i18n.load_language_preferences(self.db)
            logger.info("Language preferences loaded from database")
            
            # Start monitoring
            await self.health_checker.start_monitoring(interval=60)
            logger.info("Health monitoring started")
            
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            self.health_checker.log_error("setup", str(e))
            raise

bot = MyBot(config)

async def load_extensions():
    extensions = [
        "cog.rename", "cog.career", "cog.scan", "cog.ping",
        "cog.avatar", "cog.roll", "cog.confession", "cog.embed", "cog.XPSystem",
        "cog.role", "cog.welcome", "cog.role_menus", "cog.ticket", "cog.clear",
        "cog.language", "cog.config", "cog.moderation", "cog.server_logs", "cog.feedback",
        "cog.disboard_reminder", "cog.disboard_config"
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"✅ Extension {extension} chargée.")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {extension}: {e}")
    
    print("✅ Chargement des extensions terminé.")

@bot.event
@profile_performance("on_ready")
async def on_ready():
    logger.info(f"Bot is ready as {bot.user}")
    logger.info(f"Connected to {len(bot.guilds)} server(s):")
    for guild in bot.guilds:
        # Remove all Unicode characters that might cause encoding issues
        import re
        safe_guild_name = re.sub(r'[^\x00-\x7F]+', '?', guild.name)
        logger.info(f"  - {safe_guild_name} (ID: {guild.id})")
    
    # Start cache cleanup task
    await bot.cache.start_cleanup_task()
    logger.info("Cache system initialized")
    
    # Debug: Check command tree state before sync
    logger.info(f"Commands in tree before sync: {len(bot.tree.get_commands())}")
    for cmd in bot.tree.get_commands():
        logger.debug(f"  - {cmd.name}: {cmd.description}")
    
    # Use only global sync to make commands available in all servers
    try:
        logger.info("Starting global command sync...")
        synced_global = await bot.tree.sync()
        logger.info(f"{len(synced_global)} commands synced globally")
        logger.info("Commands will be available in all servers within a few minutes")
        
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}")
        bot.health_checker.log_error("command_sync", str(e))
        try:
            synced = await bot.tree.sync()
            logger.info(f"{len(synced)} commands synced successfully in fallback")
        except Exception as e2:
            logger.error(f"Fallback sync failed: {e2}")
            bot.health_checker.log_error("command_sync_fallback", str(e2))
    
    logger.info("Bot startup completed successfully")
    print("successfully finished startup")
    await bot.change_presence(activity=discord.Game(name="Maybee | /config"))
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have the required permissions to perform this action.")
        return
    
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ Command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
        return
    
    # Log unexpected errors
    logger.error(f"Unexpected error in command {ctx.command}: {error}")
    await ctx.send("❌ An unexpected error occurred. Please try again later.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """Global error handler for slash commands"""
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    if isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ I don't have the required permissions to perform this action.", ephemeral=True)
        return
    
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏱️ Command is on cooldown. Try again in {error.retry_after:.1f} seconds.", ephemeral=True)
        return
    
    # Log unexpected errors
    logger.error(f"Unexpected error in slash command {interaction.command}: {error}")
    
    if not interaction.response.is_done():
        await interaction.response.send_message("❌ An unexpected error occurred. Please try again later.", ephemeral=True)
    else:
        await interaction.followup.send("❌ An unexpected error occurred. Please try again later.", ephemeral=True)

@bot.tree.command(name="health", description="Check bot health and performance metrics")
@handle_errors
@rate_limit(cooldown=30)
async def health_check(interaction: discord.Interaction):
    """Health check command for monitoring bot status"""
    if not interaction.user.guild_permissions.administrator:
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.send_message(
            _("errors.admin_only", user_id, guild_id), 
            ephemeral=True
        )
        return
    
    # Defer response as health check might take a moment
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Collect current metrics
        health_report = bot.health_checker.get_health_report()
        
        # Create embed with health information
        embed = discord.Embed(
            title="🏥 Bot Health Report",
            color=discord.Color.green() if health_report['status'] == 'healthy' else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Status
        status_emoji = "🟢" if health_report['status'] == 'healthy' else "🔴"
        embed.add_field(
            name="Status", 
            value=f"{status_emoji} {health_report['status'].title()}", 
            inline=True
        )
        
        # Uptime
        embed.add_field(
            name="Uptime", 
            value=health_report['uptime'], 
            inline=True
        )
        
        # Bot info
        bot_info = health_report['bot_info']
        embed.add_field(
            name="Bot Info",
            value=f"Guilds: {bot_info['guilds']}\nUsers: {bot_info['users']}\nLatency: {bot_info['latency']}ms",
            inline=True
        )
        
        # System metrics
        current = health_report['current_metrics']['system']
        embed.add_field(
            name="System Resources",
            value=f"CPU: {current['cpu_usage']:.1f}%\nMemory: {current['memory_usage']:.1f}%\nDisk: {current['disk_usage']:.1f}%",
            inline=True
        )
        
        # Database metrics
        db_metrics = health_report['current_metrics']['database']
        embed.add_field(
            name="Database",
            value=f"Connections: {db_metrics['connections']}\nResponse: {db_metrics['response_time']:.3f}s\nErrors: {db_metrics['errors']}",
            inline=True
        )
        
        # Performance metrics
        perf = health_report['current_metrics']['performance']
        embed.add_field(
            name="Performance",
            value=f"Avg Response: {perf['average_response_time']:.3f}s\nCache Hit Rate: {perf['cache_hit_rate']:.1f}%",
            inline=True
        )
        
        # Recent errors (if any)
        if health_report['recent_errors']:
            error_count = len(health_report['recent_errors'])
            embed.add_field(
                name="Recent Errors",
                value=f"{error_count} error(s) in the last check",
                inline=False
            )
        
        embed.set_footer(text="Health check completed")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in health check command: {e}")
        await interaction.followup.send(
            "❌ Failed to generate health report. Check logs for details.",
            ephemeral=True
        )

@bot.tree.command(name="sync", description="Synchronise les commandes slash pour ce serveur (Admin uniquement)")
@handle_errors
@rate_limit(cooldown=60)
async def sync_commands(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id if interaction.guild else None
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            _("errors.admin_only", user_id, guild_id), 
            ephemeral=True
        )
        return
    
    try:
        # Respond immediately to avoid timeout
        await interaction.response.send_message(
            "🔄 Synchronisation en cours...", 
            ephemeral=True
        )
        
        # Try global sync
        synced_global = await bot.tree.sync()
        
        # Edit the response with results
        await interaction.edit_original_response(
            content=f"✅ {len(synced_global)} commandes synchronisées globalement\n"
                   f"🔍 Commandes disponibles: {', '.join([cmd.name for cmd in synced_global])}\n"
                   f"ℹ️  Les commandes peuvent prendre quelques minutes pour apparaître dans Discord."
        )
        
    except Exception as e:
        try:
            await interaction.edit_original_response(
                content=f"❌ Erreur lors de la synchronisation: {str(e)}"
            )
        except:
            # If we can't edit, try to send a followup
            await interaction.followup.send(
                f"❌ Erreur lors de la synchronisation: {str(e)}", 
                ephemeral=True
            )

# ========== Lancement du bot ==========
async def main():
    await load_extensions()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
