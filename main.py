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
# Services module removed during cleanup
# Monitoring module removed during cleanup
from cog.command_logger import log_command_usage

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

# Configure logging with separate console and file handlers
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler for detailed logs
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler for important logs only
console_handler = UnicodeStreamHandler()
console_handler.setLevel(logging.INFO)

# Custom formatter with colors and emojis
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability"""
    
    def __init__(self):
        super().__init__()
        # Check if terminal supports colors
        self.supports_color = self._supports_color()
        
        # Color codes (ANSI escape sequences)
        self.COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m',     # Reset
            'BOLD': '\033[1m',      # Bold
            'YELLOW': '\033[33m'    # Yellow for brackets
        }
        
        # Emojis for different log levels (Unicode compatible)
        self.EMOJIS = {
            'DEBUG': "[O]",
            'INFO': "[i]",
            'WARNING': "[/!\]",
            'ERROR': "[!]",
            'CRITICAL': "[!!!]"
        }
    
    def _supports_color(self):
        """Check if the terminal supports colors"""
        import os
        import sys
        
        # Force color support for Git Bash and Windows Terminal
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Always enable colors for interactive terminals
            return True
        
        # Check environment variables
        if os.getenv('TERM') in ['xterm', 'xterm-color', 'xterm-256color', 'screen', 'screen-256color']:
            return True
        
        # Windows 10+ with ANSI support
        if os.name == 'nt' and os.getenv('ANSICON') is not None:
            return True
        
        # Git Bash on Windows
        if os.getenv('MSYSTEM') is not None:
            return True
            
        return False
    
    def format(self, record):
        # Get color and emoji for the log level
        color = self.COLORS.get(record.levelname, '') if self.supports_color else ''
        emoji = self.EMOJIS.get(record.levelname, '')
        reset = self.COLORS['RESET'] if self.supports_color else ''
        bold = self.COLORS['BOLD'] if self.supports_color else ''
        yellow = self.COLORS['YELLOW'] if self.supports_color else ''
        
        # Format the message with yellow brackets, bold brackets, color text
        if record.levelname == 'INFO':
            # For INFO messages: yellow bold brackets, green text
            return f"{yellow}{bold}[{reset}{color}{bold}i{reset}{yellow}{bold}]{reset} {color}{record.getMessage()}{reset}"
        else:
            # For other levels: yellow bold brackets with colored inner text
            if record.levelname == 'WARNING':
                return f"{yellow}{bold}[{reset}{color}{bold}!{reset}{yellow}{bold}]{reset} {color}{record.levelname}:{reset} {color}{record.getMessage()}{reset}"
            elif record.levelname == 'ERROR':
                return f"{yellow}{bold}[{reset}{color}{bold}!!{reset}{yellow}{bold}]{reset} {color}{record.levelname}:{reset} {color}{record.getMessage()}{reset}"
            elif record.levelname == 'CRITICAL':
                return f"{yellow}{bold}[{reset}{color}{bold}!!!{reset}{yellow}{bold}]{reset} {color}{record.levelname}:{reset} {color}{record.getMessage()}{reset}"
            elif record.levelname == 'DEBUG':
                return f"{yellow}{bold}[{reset}{color}{bold}-{reset}{yellow}{bold}]{reset} {color}{record.levelname}:{reset} {color}{record.getMessage()}{reset}"
            else:
                return f"{yellow}{bold}[{reset}{color}{bold}{record.levelname}{reset}{yellow}{bold}]{reset} {color}{record.levelname}:{reset} {color}{record.getMessage()}{reset}"

console_formatter = ColoredFormatter()
console_handler.setFormatter(console_formatter)

# Fonction utilitaire pour unifier les logs dans toute l'application
def log_command_execution(user_name: str, command_name: str):
    """Log uniforme pour l'utilisation des commandes"""
    print(f"\033[33m\033[1m[\033[0m\033[32m\033[1mi\033[0m\033[33m\033[1m]\033[0m \033[32mUtilisateur \033[33m\033[1m{user_name}\033[0m \033[32ma utilisé \033[33m\033[1m/{command_name}\033[0m")

def log_info(message: str):
    """Log INFO uniforme"""
    print(f"\033[33m\033[1m[\033[0m\033[32m\033[1mi\033[0m\033[33m\033[1m]\033[0m \033[32m{message}\033[0m")

def log_warning(message: str):
    """Log WARNING uniforme"""
    print(f"\033[33m\033[1m[\033[0m\033[33m\033[1mWARN\033[0m\033[33m\033[1m]\033[0m \033[33mWARNING:\033[0m \033[33m{message}\033[0m")

def log_error(message: str):
    """Log ERROR uniforme"""
    print(f"\033[33m\033[1m[\033[0m\033[31m\033[1mERROR\033[0m\033[33m\033[1m]\033[0m \033[31mERROR:\033[0m \033[31m{message}\033[0m")

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Configure Discord.py to be less verbose
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)
logging.getLogger('discord.client').setLevel(logging.WARNING)

# Configure other loggers to be less verbose
logging.getLogger('aiomysql').setLevel(logging.ERROR)
logging.getLogger('googleapiclient').setLevel(logging.WARNING)

# Suppress MySQL warnings
import warnings
warnings.filterwarnings('ignore', category=Warning, module='aiomysql')


# ========== Configuration du bot ==========

# Load configuration from environment
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = "?"

if not TOKEN:
    logger.error("DISCORD_TOKEN not found in environment variables")
    exit(1)

logger.info("Configuration loaded successfully")
CATEGORY = "Tickets 🔖"

# =========== Fonctions YAML ==========

class MyBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        # Store start time
        self.start_time = datetime.now()
        
        # Setup core services
        self.db = Database(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASS', ''),
            db=os.getenv('DB_NAME', 'maybebot'),
            debug=os.getenv('DEBUG', 'False').lower() == 'true'
        )
        self.cache = BotCache(self.db)
        self.i18n = i18n
        
        # Legacy attributes for backward compatibility
        self.role_reactions = {}

    async def close(self):
        logger.info("Shutting down bot...")
        
        # Monitoring removed during cleanup
        
        # Stop cache cleanup
        await self.cache.stop_cleanup_task()
        logger.info("Cache cleanup stopped")
        
        # Close database
        await self.db.close()
        logger.info("Database connection closed")
        
        await super().close()
        logger.info("Bot shutdown complete")

    async def setup_hook(self):
        try:
            logger.info("Connecting to database...")
            await self.db.connect()
            logger.info("Database connected successfully")
            
            await self.db.init_tables()
            logger.info("Database tables initialized")
            
            # Load language preferences from database
            await self.i18n.load_language_preferences(self.db)
            logger.info("Language preferences loaded from database")
            
            # Monitoring removed during cleanup
            
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            print(f"❌ Database connection failed: {e}")
            raise

bot = MyBot()

async def load_extensions():
    extensions = [
        "cog.rename", "cog.scan", "cog.ping", "cog.dashboard",
        "cog.avatar", "cog.confession", "cog.XPSystem",
        "cog.role", "cog.welcome", "cog.role_menus", "cog.ticket", "cog.clear",
        "cog.config", "cog.moderation", "cog.server_logs", "cog.feedback",
        "cog.disboard_reminder", "cog.disboard_config", "cog.dm_logs"
    ]
    
    loaded_count = 0
    failed_count = 0
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            loaded_count += 1
            logger.debug(f"Extension {extension} loaded successfully")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to load extension {extension}: {e}")
    
    logger.info(f"Extensions loaded: {loaded_count} successful, {failed_count} failed")

@bot.event
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
        try:
            synced = await bot.tree.sync()
            logger.info(f"{len(synced)} commands synced successfully in fallback")
        except Exception as e2:
            logger.error(f"Fallback sync failed: {e2}")
    
    logger.info("Bot startup completed successfully")
    await bot.change_presence(activity=discord.Game(name="/dashboard | /config"))
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



# ========== Lancement du bot ==========
async def main():
    await load_extensions()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
