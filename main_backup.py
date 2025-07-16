import discord
from discord.ext import commands
import os
import asyncio
from db import Database
from cog.ticket import TicketPanelView, TicketCloseView
from dotenv import load_dotenv
from i18n import i18n


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
        self.i18n = i18n

    async def close(self):
        print("[ℹ️] Fermeture de la base de données...")
        await self.db.close()
        print("[✅] Base de données fermée.")
        await super().close()

    async def setup_hook(self):
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            db=os.getenv("DB_NAME")
        )

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
        except Exception as e:
            print(f"❌ Erreur lors de la connexion à la base de données: {e}")
            print("⚠️  Le bot continuera sans base de données. Certaines fonctionnalités peuvent ne pas fonctionner.")
        
        try:
            # Sync commands for each guild for instant availability
            if self.guilds:
                print("🔄 Synchronisation des commandes slash pour chaque serveur...")
                for guild in self.guilds:
                    await self.tree.sync(guild=guild)
                    print(f"✅ Commandes synchronisées pour {guild.name} (ID: {guild.id})")
                print(f"✅ Synchronisation terminée pour {len(self.guilds)} serveur(s).")
            else:
                print("⚠️  Aucun serveur trouvé, synchronisation globale...")
                await self.tree.sync()
                print("✅ Commandes slash synchronisées globalement.")
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des commandes slash: {e}")
            print("⚠️  Tentative de synchronisation globale...")
            try:
                await self.tree.sync()
                print("✅ Synchronisation globale réussie.")
            except Exception as global_e:
                print(f"❌ Erreur de synchronisation globale: {global_e}")

bot = MyBot()

async def load_extensions():
    extensions = [
        "cog.meeting", "cog.rename", "cog.career", "cog.scan", "cog.ping",
        "cog.avatar", "cog.roll", "cog.confession", "cog.embed", "cog.XPSystem",
        "cog.role", "cog.welcome", "cog.rolereact", "cog.ticket", "cog.clear"
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
    print("successfully finished startup")
    await bot.change_presence(activity=discord.Game(name="by iMutig 🤓"))
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())

@bot.tree.command(name="sync", description="Synchronise les commandes slash pour ce serveur (Admin uniquement)")
async def sync_commands(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Vous devez être administrateur pour utiliser cette commande.", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        synced = await bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send(f"✅ {len(synced)} commandes synchronisées pour ce serveur!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de la synchronisation: {e}", ephemeral=True)

# ========== Lancement du bot ==========
async def main():
    await load_extensions()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
