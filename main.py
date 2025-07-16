import discord
from discord.ext import commands
import yaml
import os
import random
from collections import Counter
import secrets
import string
from discord.ui import Button, View
from discord import app_commands
import asyncio
from db import Database
from cog.ticket import TicketPanelView, TicketCloseView
from dotenv import load_dotenv
import os


# ========== Configuration du bot ==========

load_dotenv()
TOKEN = token = os.getenv("DISCORD_TOKEN")
print(f"Token chargé ? {'Oui' if TOKEN else 'Non'}")
PREFIX = "?"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents = discord.Intents.all()
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

    async def close(self):
        print("[ℹ️] Fermeture de la base de données...")
        await self.db.close()
        print("[✅] Base de données fermée.")
        await super().close()

    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(id=1392463988679508030))
        print("✅ Commandes slash synchronisées globalement.")
        await self.db.connect()

bot = MyBot()

async def load_extensions():
    await bot.load_extension("cog.meeting")
    await bot.load_extension("cog.rename")
    await bot.load_extension("cog.career")
    await bot.load_extension("cog.scan")
    await bot.load_extension("cog.ping")
    await bot.load_extension("cog.avatar")
    await bot.load_extension("cog.roll")
    await bot.load_extension("cog.confession")
    await bot.load_extension("cog.embed")
    await bot.load_extension("cog.XPSystem")
    await bot.load_extension("cog.role")
    await bot.load_extension("cog.welcome")
    await bot.load_extension("cog.rolereact")
    await bot.load_extension("cog.ticket")
    await bot.load_extension("cog.clear")
    print("✅ Extensions chargées.")

@bot.event
async def on_ready():
    print(f"✅ Le bot est connecté en tant que {bot.user}")
    print("successfully finished startup")
    await bot.change_presence(activity=discord.Game(name="by iMutig 🤓"))
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())

# ========== Lancement du bot ==========
asyncio.run(load_extensions())
bot.run(TOKEN)
