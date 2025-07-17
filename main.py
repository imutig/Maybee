import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
from db import Database
from cache import BotCache
from cog.ticket import TicketPanelView, TicketCloseView
from dotenv import load_dotenv
from i18n import i18n, _

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== Configuration du bot ==========

load_dotenv()

# Validate required environment variables
required_env_vars = ["DISCORD_TOKEN", "DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Variables d'environnement manquantes: {', '.join(missing_vars)}")
    print("Veuillez créer un fichier .env")
    exit(1)

TOKEN = os.getenv("DISCORD_TOKEN")
print(f"Token chargé ? {'Oui' if TOKEN else 'Non'}")
PREFIX = "?"
CATEGORY = "Tickets 🔖"

# =========== Fonctions YAML ==========

class MyBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.role_reactions = {}
        self.db = Database(
            host=os.getenv("DB_HOST"),
            port=3306,
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            db=os.getenv("DB_NAME")
        )
        self.cache = BotCache(self.db)  # Initialize cache system
        self.i18n = i18n

    async def close(self):
        print("[ℹ️] Fermeture de la base de données...")
        await self.db.close()
        print("[✅] Base de données fermée.")
        await super().close()

    async def setup_hook(self):
        try:
            await self.db.connect()
            print("✅ Base de données connectée.")
            await self.db.init_tables()
            print("✅ Tables de la base de données initialisées.")
            
            # Load language preferences from database
            await self.i18n.load_language_preferences(self.db)
            print("✅ Préférences linguistiques chargées depuis la base de données.")
            
        except Exception as e:
            print(f"❌ Erreur lors de la connexion à la base de données: {e}")
            print("⚠️  Le bot continuera sans base de données. Certaines fonctionnalités peuvent ne pas fonctionner.")

bot = MyBot()

async def load_extensions():
    extensions = [
        "cog.meeting", "cog.rename", "cog.career", "cog.scan", "cog.ping",
        "cog.avatar", "cog.roll", "cog.confession", "cog.embed", "cog.XPSystem",
        "cog.role", "cog.welcome", "cog.rolereact", "cog.ticket", "cog.clear",
        "cog.language", "cog.config", "cog.moderation", "cog.cache"
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"✅ Extension {extension} chargée.")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {extension}: {e}")
    
    print("✅ Chargement des extensions terminé.")

@bot.event
async def on_ready():
    print(f"✅ Le bot est connecté en tant que {bot.user}")
    print(f"📊 Connecté à {len(bot.guilds)} serveur(s):")
    for guild in bot.guilds:
        print(f"  - {guild.name} (ID: {guild.id})")
    
    # Start cache cleanup task
    await bot.cache.start_cleanup_task()
    print("✅ Cache system initialized")
    
    # Debug: Check command tree state before sync
    print(f"🔍 Commandes dans l'arbre avant synchronisation: {len(bot.tree.get_commands())}")
    for cmd in bot.tree.get_commands():
        print(f"  - {cmd.name}: {cmd.description}")
    
    # Use only global sync to make commands available in all servers
    try:
        print("🌐 Synchronisation globale en cours...")
        synced_global = await bot.tree.sync()
        print(f"✅ {len(synced_global)} commandes synchronisées globalement")
        print("ℹ️  Les commandes seront disponibles dans tous les serveurs dans quelques minutes.")
        
        # Note: Guild-specific sync can override global sync and cause issues
        # Global sync makes commands available in all servers the bot is in
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes slash: {e}")
        print("⚠️  Tentative de synchronisation globale...")
        try:
            synced = await bot.tree.sync()
            print(f"✅ {len(synced)} commandes en synchronisation globale réussie.")
        except Exception as e2:
            print(f"❌ Échec de la synchronisation globale: {e2}")
        except Exception as global_e:
            print(f"❌ Erreur de synchronisation globale: {global_e}")
    
    print("successfully finished startup")
    await bot.change_presence(activity=discord.Game(name="by iMutig 🤓"))
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

@bot.tree.command(name="sync", description="Synchronise les commandes slash pour ce serveur (Admin uniquement)")
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
