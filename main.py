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

# ========== Configuration du bot ==========

TOKEN = os.getenv("DISCORD_TOKEN")
print(f"Token chargé ? {'Oui' if TOKEN else 'Non'}")
PREFIX = "?"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents = discord.Intents.all()
YAML_FILE = "data/roles.yaml"
TICKET_COUNTER_FILE = "data/ticket_counter.yaml"
GUILD_ID = "1392463988679508030"
CATEGORY = "Tickets 🔖"

# =========== Fonctions YAML ==========


class MyBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.role_reactions = {}

    async def setup_hook(self):
        # Charger ton extension ici
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Commandes slash synchronisées.")


bot = MyBot()


def save_role_reactions():
    # Convertir les clés (message IDs) en chaînes, et aussi les role_ids en chaînes
    serializable = {}
    for msg_id, emoji_map in bot.role_reactions.items():
        serializable[str(msg_id)] = {
            emoji: str(role_id)
            for emoji, role_id in emoji_map.items()
        }

    with open(YAML_FILE, "w") as f:
        yaml.dump(serializable, f)


def load_ticket_counter():
    if os.path.exists(TICKET_COUNTER_FILE):
        with open(TICKET_COUNTER_FILE, "r") as f:
            data = yaml.safe_load(f) or {}
            return data.get("ticket_counter", 0)
    return 0


def save_ticket_counter(counter):
    data = {"ticket_counter": counter}
    with open(TICKET_COUNTER_FILE, "w") as f:
        yaml.dump(data, f)


ticket_counter = load_ticket_counter()


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
    print("✅ Extensions chargées.")


async def setup_hook(self):
    guild = discord.Object(
        id=GUILD_ID)  # Remplace par l'ID de ton serveur (int)
    self.tree.copy_global_to(guild=guild)
    await self.tree.sync(guild=guild)


@bot.event
async def on_ready():
    print(f"✅ Le bot est connecté en tant que {bot.user}")
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("Commandes synchronisées.")
    await bot.change_presence(activity=discord.Game(name="by iMutig 🤓"))
    bot.role_reactions = {}

    # Charger les données du fichier YAML
    if os.path.exists(YAML_FILE):
        with open(YAML_FILE, "r") as f:
            raw_data = yaml.safe_load(f) or {}
        for message_id_str, emoji_map in raw_data.items():
            message_id = int(message_id_str)
            bot.role_reactions[message_id] = {}
            for emoji, role_id_str in emoji_map.items():
                bot.role_reactions[message_id][emoji] = int(role_id_str)
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())

    print(f"Données chargées depuis YAML: {bot.role_reactions}")
    # Vérifiez que les messages avec les réactions existent toujours
    for message_id in bot.role_reactions:
        try:
            channel = bot.get_channel(
                1393935449944227931)  # Remplacez par l'ID du canal
            if channel:
                message = await channel.fetch_message(message_id)
                print(f"Message trouvé: {message.content}")
                # Vérifiez que les réactions existent toujours
                for emoji in bot.role_reactions[message_id]:
                    print(f"Réaction trouvée: {emoji}")
        except Exception as e:
            print(f"Erreur lors de la récupération du message: {e}")


# ========== Quand le bot est prêt ==========

# ========== Système de tickets ==========


# ========== Commandes ==========
@bot.tree.command(name="setup_ticket",
                  description="Configure le système de ticket.",
                  guild=discord.Object(id=GUILD_ID))
async def setup_ticket(interaction: discord.Interaction):
    # Ici tu peux ajouter ta logique pour créer les catégories, salons, rôles, etc.
    # Exemple simple juste pour la demo :
    guild = interaction.guild
    category = await guild.create_category(CATEGORY)
    ticket_channel = await guild.create_text_channel("général-tickets",
                                                     category=category)

    await interaction.response.send_message(
        f"Système de ticket configuré dans {category.name} !", ephemeral=True)


@bot.tree.command(name="setup_ticket_panel",
                  description="Créer le panel de ticket",
                  guild=discord.Object(id=GUILD_ID))
async def setup_ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support Tickets",
        description="Clique sur le bouton ci-dessous pour créer un ticket.",
        color=discord.Color.green())

    view = TicketPanelView()
    await interaction.response.send_message(embed=embed, view=view)


# ========== Evenements Tickets ==========


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id") == "open_ticket":
            # Logique de création de ticket ici
            await interaction.response.send_message(
                "Ticket créé (placeholder).", ephemeral=True)


# ========== Classes Tickets ==========


class TicketCreateButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Créer un ticket",
                         custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Trouve la catégorie "Tickets"
        category = discord.utils.get(guild.categories, name=CATEGORY)
        if not category:
            await interaction.response.send_message(
                "❌ La catégorie des tickets n'a pas encore été créée. Merci d'utiliser /setup_ticket pour la créer.",
                ephemeral=True)
            return

        # Vérifie si un ticket existe déjà pour l'utilisateur
        existing = discord.utils.get(category.channels,
                                     name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                "Tu as déjà un ticket ouvert dans la catégorie Tickets !",
                ephemeral=True)
            return

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(view_channel=False),
            user:
            discord.PermissionOverwrite(view_channel=True,
                                        send_messages=True,
                                        read_message_history=True),
            guild.me:
            discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            overwrites=overwrites,
            category=category,
            reason="Création d'un ticket")

        embed = discord.Embed(
            title="Ticket Support",
            description=
            f"Salut {user.mention} ! Un membre du staff va te répondre rapidement.\nClique sur le bouton pour fermer le ticket.",
            color=discord.Color.blue())

        close_button = TicketCloseButton()
        view = TicketCloseView()

        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            f"Ton ticket a été créé : {channel.mention}", ephemeral=True)


class TicketCloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red,
                         label="Fermer le ticket",
                         custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await interaction.response.send_message("Fermeture dans 5 secondes...",
                                                ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket fermé par {interaction.user}")


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)  # <-- ici timeout=None
        self.add_item(TicketCreateButton())


class TicketCloseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())


# ========== Clear de messages ==========


@bot.tree.command(name="clear",
                  description="Supprime les messages du canal.",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.describe(nombre="Nombre de messages à supprimer (max 100)")
async def clear(interaction: discord.Interaction, nombre: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ Tu n'as pas la permission de gérer les messages.",
            ephemeral=True)
        return

    if nombre < 1 or nombre > 100:
        await interaction.response.send_message(
            "❌ Le nombre doit être entre 1 et 100.", ephemeral=True)
        return

    await interaction.response.defer(
        ephemeral=True)  # on indique à Discord qu'on traite la commande

    deleted = await interaction.channel.purge(limit=nombre)

    await interaction.followup.send(f"🧹 {len(deleted)} messages supprimés.",
                                    ephemeral=True)


# ========== Rôles par réaction ==========


@bot.tree.command(name="rolereact",
                  description="Configurer les rôles par réaction",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
async def rolereact(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Configuration des rôles par réaction 🛠️\nTape `stop` à tout moment pour terminer.",
        ephemeral=True)

    config_list = []

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    while True:
        await interaction.followup.send(
            "📌 Entre le message pour ce rôle (ou `stop` pour finir) :",
            ephemeral=True)
        try:
            msg_input = await bot.wait_for('message',
                                           check=check,
                                           timeout=300.0)
        except:
            await interaction.followup.send("⏱️ Temps écoulé.", ephemeral=True)
            return

        if msg_input.content.lower() == 'stop':
            await interaction.followup.send("Configuration terminée.",
                                            ephemeral=True)
            break

        await msg_input.delete()

        await interaction.followup.send("😊 Réaction emoji pour ce rôle :",
                                        ephemeral=True)
        try:
            emoji_input = await bot.wait_for('message',
                                             check=check,
                                             timeout=60.0)
        except:
            await interaction.followup.send("⏱️ Temps écoulé.", ephemeral=True)
            return

        if emoji_input.content.lower() == 'stop':
            await interaction.followup.send("Configuration terminée.",
                                            ephemeral=True)
            break

        await emoji_input.delete()

        await interaction.followup.send("🎭 Mentionnez le rôle à attribuer :",
                                        ephemeral=True)
        try:
            role_input = await bot.wait_for('message',
                                            check=check,
                                            timeout=60.0)
        except:
            await interaction.followup.send("⏱️ Temps écoulé.", ephemeral=True)
            return

        if role_input.content.lower() == 'stop':
            await interaction.followup.send("Configuration terminée.",
                                            ephemeral=True)
            break

        await role_input.delete()

        role_mention = role_input.content
        guild = interaction.guild
        if role_mention.startswith('<@&') and role_mention.endswith('>'):
            role_id = int(role_mention[3:-1])
            role = guild.get_role(role_id)
        else:
            role = discord.utils.get(guild.roles, name=role_mention)

        if not role:
            await interaction.followup.send(
                f"⚠️ Le rôle **{role_mention}** n'existe pas. Veuillez créer le rôle d'abord.",
                ephemeral=True)
            continue

        config_list.append({
            'message': msg_input.content,
            'emoji': emoji_input.content,
            'role': role
        })

    if not config_list:
        await interaction.followup.send("⚠️ Aucune configuration ajoutée.",
                                        ephemeral=True)
        return

    embed_desc = ""
    for item in config_list:
        embed_desc += f"{item['emoji']} → {item['role'].mention} : {item['message']}\n"

    embed = discord.Embed(
        title="Clique sur une réaction pour obtenir un rôle ✨",
        description=embed_desc,
        color=discord.Color.green())

    message = await interaction.channel.send(embed=embed)
    for item in config_list:
        await message.add_reaction(item['emoji'])

    bot.role_reactions[message.id] = {}
    for item in config_list:
        bot.role_reactions[message.id][item['emoji']] = item['role'].id

    save_role_reactions()
    confirmation_message = await interaction.channel.send(
        "✅ Configuration terminée. Les utilisateurs peuvent maintenant réagir pour obtenir un rôle."
    )
    await confirmation_message.delete(delay=5)


# ========== Evenements Rôles par réaction ==========


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    role_map = bot.role_reactions.get(payload.message_id)
    if role_map and str(payload.emoji.name) in role_map:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            print("❌ Guild introuvable")
            return

        member = guild.get_member(payload.user_id)
        if not member:
            print("❌ Membre introuvable")
            return

        role_id = role_map[str(payload.emoji.name)]
        role = guild.get_role(role_id)
        if not role:
            print(f"❌ Rôle ID {role_id} introuvable dans la guilde")
            return

        try:
            await member.add_roles(role)
            channel = bot.get_channel(payload.channel_id)
            if channel:
                msg = await channel.send(
                    f"{member.mention} 🎉 Tu as reçu le rôle **{role.name}** !")
                await msg.delete(delay=5)
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout du rôle: {e}")


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return

    role_map = bot.role_reactions.get(payload.message_id)
    if role_map and str(payload.emoji.name) in role_map:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            print("❌ Guild introuvable")
            return

        member = guild.get_member(payload.user_id)
        if not member:
            print("❌ Membre introuvable")
            return

        role_id = role_map[str(payload.emoji.name)]
        role = guild.get_role(role_id)
        if not role:
            print(f"❌ Rôle ID {role_id} introuvable dans la guilde")
            return

        try:
            await member.remove_roles(role)
            channel = bot.get_channel(payload.channel_id)
            if channel:
                msg = await channel.send(
                    f"{member.mention} ❌ Le rôle **{role.name}** t'a été retiré."
                )
                await msg.delete(delay=5)
        except Exception as e:
            print(f"❌ Erreur lors du retrait du rôle: {e}")


class TicketCreateButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Créer un ticket",
                         custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Trouve la catégorie "Tickets"
        category = discord.utils.get(guild.categories, name=CATEGORY)
        if not category:
            await interaction.response.send_message(
                "❌ La catégorie des tickets n'a pas encore été créée. Merci d'utiliser /setup_ticket pour la créer.",
                ephemeral=True)
            return

        # Vérifie si un ticket existe déjà pour l'utilisateur
        existing = discord.utils.get(category.channels,
                                     name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                "Tu as déjà un ticket ouvert dans la catégorie Tickets !",
                ephemeral=True)
            return

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(view_channel=False),
            user:
            discord.PermissionOverwrite(view_channel=True,
                                        send_messages=True,
                                        read_message_history=True),
            guild.me:
            discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            overwrites=overwrites,
            category=category,
            reason="Création d'un ticket")

        embed = discord.Embed(
            title="Ticket Support",
            description=
            f"Salut {user.mention} ! Un membre du staff va te répondre rapidement.\nClique sur le bouton pour fermer le ticket.",
            color=discord.Color.blue())

        close_button = TicketCloseButton()
        view = TicketCloseView()

        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            f"Ton ticket a été créé : {channel.mention}", ephemeral=True)


class TicketCloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red,
                         label="Fermer le ticket",
                         custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await interaction.response.send_message("Fermeture dans 5 secondes...",
                                                ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket fermé par {interaction.user}")


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)  # <-- ici timeout=None
        self.add_item(TicketCreateButton())


class TicketCloseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())


# ========== Commandes de modération ==========

# ========== Lancement du bot ==========
asyncio.run(load_extensions())
bot.run(TOKEN)
