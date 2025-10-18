import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
import asyncio
from typing import Optional, Dict, List, Set
from datetime import datetime
from i18n import _
from .command_logger import log_command_usage
from custom_emojis import SUCCESS, ERROR, WARNING, INFO, CLOCK, CHECK, CROSS

logger = logging.getLogger(__name__)

# Images du jeu
GAME_SETUP_IMAGE = "https://static.fnac-static.com/multimedia/Images/FR/NR/1e/97/2b/2856734/1541-1/tsp20161013102534/Les-Loups-Garous-de-Thiercelieux-Asmodee.jpg"
ROLE_DISTRIBUTION_IMAGE = "https://cdn.unitycms.io/images/6SWyNzu2a8z9F1TdLk0nMP.jpg?op=ocroped&val=1200,800,1000,1000,0,0&sum=9bFR7Uq8a9A"

# Cartes des rôles
ROLE_CARDS = {
    "villageois": "https://static.wikia.nocookie.net/loupgaroumal/images/d/d6/Carte_SimpleVillaegois.png/revision/latest?cb=20210104170925&path-prefix=fr",
    "loup": "https://static.wikia.nocookie.net/loupgaroumal/images/1/1e/Carte2.png/revision/latest/scale-to-width-down/250?cb=20210104171045&path-prefix=fr",
    "voyante": "https://static.wikia.nocookie.net/loupgaroumal/images/b/be/Carte3.png/revision/latest?cb=20210104171212&path-prefix=fr",
    "chasseur": "https://static.wikia.nocookie.net/loupgaroumal/images/0/0e/Carte6.png/revision/latest?cb=20210104171604&path-prefix=fr",
    "sorciere": "https://www.regledujeu.fr/wp-content/uploads/sorciere.png",
    "cupidon": "https://www.regledujeu.fr/wp-content/uploads/cupidon.png",
    "ange": "https://www.regledujeu.fr/wp-content/uploads/ange.png",
    # Pour les rôles sans image spécifique, on utilisera l'image générale
    "petite_fille": ROLE_DISTRIBUTION_IMAGE,
    "voleur": ROLE_DISTRIBUTION_IMAGE,
}

# Rôles disponibles
ROLES = {
    "loup": {"team": "loups", "night_action": True, "emoji": "🐺"},
    "villageois": {"team": "village", "night_action": False, "emoji": "👨"},
    "voyante": {"team": "village", "night_action": True, "emoji": "🔮"},
    "chasseur": {"team": "village", "night_action": False, "emoji": "🏹"},
    "cupidon": {"team": "village", "night_action": True, "emoji": "💘"},
    "sorciere": {"team": "village", "night_action": True, "emoji": "🧙‍♀️"},
    "petite_fille": {"team": "village", "night_action": False, "emoji": "👧"},
    "voleur": {"team": "village", "night_action": True, "emoji": "🦹"},
    "ange": {"team": "ange", "night_action": False, "emoji": "👼"},
}

class LoupGarouGame:
    """Classe représentant une partie de Loup-Garou"""
    
    def __init__(self, guild_id: int, channel: discord.TextChannel, organizer: discord.Member):
        self.guild_id = guild_id
        self.channel = channel
        self.organizer = organizer
        self.players: Dict[int, discord.Member] = {}  # user_id -> Member
        self.roles: Dict[int, str] = {}  # user_id -> role
        self.alive_players: Set[int] = set()
        self.dead_players: Set[int] = set()
        self.lovers: List[int] = []  # Liste des amoureux (2 joueurs max)
        self.mayor: Optional[int] = None  # ID du maire
        self.angel_id: Optional[int] = None  # ID de l'ange
        self.angel_first_vote_passed = False  # Si le premier vote est passé pour l'ange
        self.phase = "setup"  # setup, night, day, voting, ended
        self.day_number = 0
        self.votes: Dict[int, int] = {}  # voter_id -> target_id
        self.vote_times: Dict[int, float] = {}  # voter_id -> timestamp
        self.vote_start_time: Optional[float] = None  # Début du vote
        self.night_actions: Dict[str, any] = {}  # role -> action_data
        self.game_message: Optional[discord.Message] = None
        self.sorciere_heal_used = False
        self.sorciere_poison_used = False
        self.last_victim: Optional[int] = None
        
    def add_player(self, member: discord.Member) -> bool:
        """Ajoute un joueur à la partie"""
        if member.id not in self.players and len(self.players) < 20:
            self.players[member.id] = member
            return True
        return False
    
    def remove_player(self, member: discord.Member) -> bool:
        """Retire un joueur de la partie"""
        if member.id in self.players and self.phase == "setup":
            del self.players[member.id]
            return True
        return False
    
    def assign_roles(self, role_distribution: Dict[str, int]):
        """Attribue les rôles aux joueurs"""
        available_roles = []
        for role, count in role_distribution.items():
            available_roles.extend([role] * count)
        
        random.shuffle(available_roles)
        player_ids = list(self.players.keys())
        random.shuffle(player_ids)
        
        for player_id, role in zip(player_ids, available_roles):
            self.roles[player_id] = role
            self.alive_players.add(player_id)
            
            # Identifie l'ange s'il y en a un
            if role == "ange":
                self.angel_id = player_id
    
    def kill_player(self, user_id: int):
        """Tue un joueur"""
        if user_id in self.alive_players:
            self.alive_players.remove(user_id)
            self.dead_players.add(user_id)
            
            # Si un amoureux meurt, l'autre meurt aussi
            if user_id in self.lovers:
                for lover_id in self.lovers:
                    if lover_id != user_id and lover_id in self.alive_players:
                        self.alive_players.remove(lover_id)
                        self.dead_players.add(lover_id)
    
    def check_victory(self) -> Optional[str]:
        """Vérifie si une équipe a gagné"""
        loups_alive = sum(1 for uid in self.alive_players if self.roles.get(uid) == "loup")
        village_alive = len(self.alive_players) - loups_alive
        
        if loups_alive == 0:
            return "village"
        elif loups_alive >= village_alive:
            return "loups"
        
        # Vérifie si les amoureux sont les derniers survivants
        if len(self.alive_players) == 2 and len(self.lovers) == 2:
            if all(lover_id in self.alive_players for lover_id in self.lovers):
                return "lovers"
        
        return None

class GameSetupView(discord.ui.View):
    """Vue pour configurer et démarrer une partie"""
    
    def __init__(self, game: LoupGarouGame, cog):
        super().__init__(timeout=300)
        self.game = game
        self.cog = cog
        self.role_distribution = {"loup": 1, "villageois": 3, "voyante": 1}
    
    @discord.ui.button(label="Rejoindre", style=discord.ButtonStyle.green, emoji="✅")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game.add_player(interaction.user):
            await interaction.response.send_message(
                _("loupgarou.joined", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
            await self.update_game_message()
        else:
            await interaction.response.send_message(
                _("loupgarou.already_joined", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
    
    @discord.ui.button(label="Quitter", style=discord.ButtonStyle.red, emoji="❌")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game.remove_player(interaction.user):
            await interaction.response.send_message(
                _("loupgarou.left", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
            await self.update_game_message()
        else:
            await interaction.response.send_message(
                _("loupgarou.not_in_game", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
    
    @discord.ui.button(label="Configurer", style=discord.ButtonStyle.blurple, emoji="⚙️")
    async def config_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.organizer.id:
            await interaction.response.send_message(
                _("loupgarou.only_organizer", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
            return
        
        modal = RoleConfigModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Lancer", style=discord.ButtonStyle.primary, emoji="🎮")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.organizer.id:
            await interaction.response.send_message(
                _("loupgarou.only_organizer", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
            return
        
        if len(self.game.players) < 4:
            await interaction.response.send_message(
                _("loupgarou.not_enough_players", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
            return
        
        # Vérifie que la distribution des rôles correspond au nombre de joueurs
        total_roles = sum(self.role_distribution.values())
        if total_roles != len(self.game.players):
            await interaction.response.send_message(
                _("loupgarou.role_mismatch", interaction.user.id, self.game.guild_id)
                .format(total_roles, len(self.game.players)),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        self.stop()
        await self.cog.start_game(self.game, self.role_distribution)
    
    async def update_game_message(self):
        """Met à jour le message de configuration"""
        if self.game.game_message:
            embed = self.create_embed()
            await self.game.game_message.edit(embed=embed, view=self)
    
    def create_embed(self) -> discord.Embed:
        """Crée l'embed de configuration"""
        embed = discord.Embed(
            title=f"🐺 {_('loupgarou.game_title', self.game.organizer.id, self.game.guild_id)}",
            description=_("loupgarou.game_description", self.game.organizer.id, self.game.guild_id),
            color=discord.Color.dark_red()
        )
        
        # Ajoute l'image du jeu
        embed.set_image(url=GAME_SETUP_IMAGE)
        
        players_list = "\n".join([f"• {member.mention}" for member in self.game.players.values()])
        embed.add_field(
            name=f"👥 {_('loupgarou.players', self.game.organizer.id, self.game.guild_id)} ({len(self.game.players)})",
            value=players_list if players_list else _("loupgarou.no_players", self.game.organizer.id, self.game.guild_id),
            inline=False
        )
        
        roles_text = "\n".join([
            f"{ROLES[role]['emoji']} **{_(f'loupgarou.role.{role}', self.game.organizer.id, self.game.guild_id)}**: {count}"
            for role, count in self.role_distribution.items()
        ])
        embed.add_field(
            name=f"🎭 {_('loupgarou.roles', self.game.organizer.id, self.game.guild_id)}",
            value=roles_text,
            inline=False
        )
        
        embed.set_footer(text=_("loupgarou.organizer", self.game.organizer.id, self.game.guild_id).format(self.game.organizer.name))
        
        return embed

class RoleConfigModal(discord.ui.Modal):
    """Modal pour configurer la distribution des rôles"""
    
    def __init__(self, view: GameSetupView):
        super().__init__(title="Configuration des rôles")
        self.view = view
        
        # Ajoute des champs pour chaque rôle
        self.loups = discord.ui.TextInput(
            label="Nombre de Loups-Garous",
            placeholder="1",
            default=str(view.role_distribution.get("loup", 1)),
            min_length=1,
            max_length=2
        )
        self.add_item(self.loups)
        
        self.villageois = discord.ui.TextInput(
            label="Nombre de Villageois",
            placeholder="3",
            default=str(view.role_distribution.get("villageois", 3)),
            min_length=1,
            max_length=2
        )
        self.add_item(self.villageois)
        
        self.voyante = discord.ui.TextInput(
            label="Nombre de Voyantes",
            placeholder="0 ou 1",
            default=str(view.role_distribution.get("voyante", 0)),
            min_length=1,
            max_length=1
        )
        self.add_item(self.voyante)
        
        self.chasseur = discord.ui.TextInput(
            label="Nombre de Chasseurs",
            placeholder="0 ou 1",
            default=str(view.role_distribution.get("chasseur", 0)),
            min_length=1,
            max_length=1
        )
        self.add_item(self.chasseur)
        
        self.sorciere = discord.ui.TextInput(
            label="Nombre de Sorcières",
            placeholder="0 ou 1",
            default=str(view.role_distribution.get("sorciere", 0)),
            min_length=1,
            max_length=1
        )
        self.add_item(self.sorciere)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.view.role_distribution = {}
            
            loup_count = int(self.loups.value)
            if loup_count > 0:
                self.view.role_distribution["loup"] = loup_count
            
            villageois_count = int(self.villageois.value)
            if villageois_count > 0:
                self.view.role_distribution["villageois"] = villageois_count
            
            voyante_count = int(self.voyante.value)
            if voyante_count > 0:
                self.view.role_distribution["voyante"] = voyante_count
            
            chasseur_count = int(self.chasseur.value)
            if chasseur_count > 0:
                self.view.role_distribution["chasseur"] = chasseur_count
            
            sorciere_count = int(self.sorciere.value)
            if sorciere_count > 0:
                self.view.role_distribution["sorciere"] = sorciere_count
            
            await interaction.response.send_message(
                _("loupgarou.config_updated", interaction.user.id, self.view.game.guild_id),
                ephemeral=True
            )
            await self.view.update_game_message()
        
        except ValueError:
            await interaction.response.send_message(
                _("loupgarou.invalid_numbers", interaction.user.id, self.view.game.guild_id),
                ephemeral=True
            )

class VoteView(discord.ui.View):
    """Vue pour voter pendant la phase de jour"""
    
    def __init__(self, game: LoupGarouGame, cog):
        super().__init__(timeout=120)
        self.game = game
        self.cog = cog
        self.vote_complete = asyncio.Event()
        
        # Crée un select avec tous les joueurs vivants
        options = [
            discord.SelectOption(
                label=self.game.players[uid].display_name,
                value=str(uid),
                emoji="❓"
            )
            for uid in self.game.alive_players
        ]
        
        self.player_select = discord.ui.Select(
            placeholder="Choisissez qui éliminer...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.player_select.callback = self.vote_callback
        self.add_item(self.player_select)
    
    async def vote_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in self.game.alive_players:
            await interaction.response.send_message(
                _("loupgarou.dead_cant_vote", interaction.user.id, self.game.guild_id),
                ephemeral=True
            )
            return
        
        target_id = int(self.player_select.values[0])
        self.game.votes[interaction.user.id] = target_id
        
        # Enregistre le temps du vote
        import time
        if self.game.vote_start_time:
            self.game.vote_times[interaction.user.id] = time.time() - self.game.vote_start_time
        
        await interaction.response.send_message(
            _("loupgarou.vote_registered", interaction.user.id, self.game.guild_id)
            .format(self.game.players[target_id].display_name),
            ephemeral=True
        )
        
        # Vérifie si tous les joueurs vivants ont voté
        if len(self.game.votes) >= len(self.game.alive_players):
            self.vote_complete.set()
            self.stop()

class LoupGarou(commands.Cog):
    """Cog pour le jeu du Loup-Garou"""
    
    def __init__(self, bot):
        self.bot = bot
        self.games: Dict[int, LoupGarouGame] = {}  # guild_id -> game
    
    @app_commands.command(name="loupgarou", description="Lance une partie de Loup-Garou")
    @log_command_usage
    async def loupgarou(self, interaction: discord.Interaction):
        """Commande pour lancer une partie de Loup-Garou"""
        
        # Vérifie qu'il n'y a pas déjà une partie en cours
        if interaction.guild_id in self.games:
            await interaction.response.send_message(
                f"{ERROR} {_('loupgarou.game_already_running', interaction.user.id, interaction.guild_id)}",
                ephemeral=True
            )
            return
        
        # Crée une nouvelle partie
        game = LoupGarouGame(interaction.guild_id, interaction.channel, interaction.user)
        game.add_player(interaction.user)  # L'organisateur rejoint automatiquement
        self.games[interaction.guild_id] = game
        
        # Crée la vue de configuration
        view = GameSetupView(game, self)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        game.game_message = await interaction.original_response()
        
        logger.info(f"Partie de Loup-Garou créée dans {interaction.guild.name} par {interaction.user.name}")
    
    @app_commands.command(name="loupgarou-stop", description="Arrête la partie de Loup-Garou en cours")
    @app_commands.checks.has_permissions(administrator=True)
    @log_command_usage
    async def loupgarou_stop(self, interaction: discord.Interaction):
        """Arrête une partie en cours"""
        
        if interaction.guild_id not in self.games:
            await interaction.response.send_message(
                f"{ERROR} {_('loupgarou.no_game_running', interaction.user.id, interaction.guild_id)}",
                ephemeral=True
            )
            return
        
        game = self.games[interaction.guild_id]
        
        # Seul l'organisateur ou un admin peut arrêter
        if interaction.user.id != game.organizer.id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                f"{ERROR} {_('loupgarou.only_organizer', interaction.user.id, interaction.guild_id)}",
                ephemeral=True
            )
            return
        
        del self.games[interaction.guild_id]
        
        await interaction.response.send_message(
            f"{SUCCESS} {_('loupgarou.game_stopped', interaction.user.id, interaction.guild_id)}"
        )
        
        logger.info(f"Partie de Loup-Garou arrêtée dans {interaction.guild.name}")
    
    async def start_game(self, game: LoupGarouGame, role_distribution: Dict[str, int]):
        """Démarre la partie"""
        game.phase = "starting"
        game.assign_roles(role_distribution)
        
        # Vérifie d'abord que tous les joueurs peuvent recevoir des MPs
        failed_players = []
        for user_id in game.players.keys():
            member = game.players[user_id]
            try:
                await member.send("🎮 Vérification des messages privés... Vous recevrez bientôt votre rôle !")
            except discord.Forbidden:
                failed_players.append(member)
        
        # Si des joueurs ne peuvent pas recevoir de MPs, annule la partie
        if failed_players:
            error_msg = f"{ERROR} **Impossible de démarrer la partie !**\n\n"
            error_msg += "Les joueurs suivants doivent activer leurs messages privés :\n"
            error_msg += "\n".join([f"• {member.mention}" for member in failed_players])
            error_msg += "\n\n*Demandez-leur d'activer les MPs dans les paramètres du serveur, puis relancez la partie.*"
            
            await game.channel.send(error_msg)
            
            # Annule la partie
            if game.guild_id in self.games:
                del self.games[game.guild_id]
            
            logger.warning(f"Partie annulée - joueurs sans MPs: {[m.name for m in failed_players]}")
            return
        
        # Envoie les rôles aux joueurs en MP
        for user_id, role in game.roles.items():
            member = game.players[user_id]
            try:
                embed = discord.Embed(
                    title=f"{ROLES[role]['emoji']} {_(f'loupgarou.role.{role}', None, game.guild_id)}",
                    description=_(f"loupgarou.role_description.{role}", None, game.guild_id),
                    color=discord.Color.dark_red() if role == "loup" else discord.Color.blue()
                )
                embed.set_footer(text=_("loupgarou.role_secret", None, game.guild_id))
                
                # Ajoute l'image de la carte du rôle
                if role in ROLE_CARDS:
                    embed.set_image(url=ROLE_CARDS[role])
                
                await member.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Impossible d'envoyer le rôle à {member.name}")
        
        # Annonce le début de la partie
        embed = discord.Embed(
            title=f"🌙 {_('loupgarou.game_started', game.organizer.id, game.guild_id)}",
            description=_("loupgarou.game_started_description", game.organizer.id, game.guild_id),
            color=discord.Color.dark_blue()
        )
        # Ajoute l'image de distribution des rôles
        embed.set_image(url=ROLE_DISTRIBUTION_IMAGE)
        await game.channel.send(embed=embed)
        
        # Gestion de Cupidon si présent
        if "cupidon" in role_distribution and role_distribution["cupidon"] > 0:
            await self.cupidon_phase(game)
        
        # Élection du maire
        await self.mayor_election(game)
        
        # Commence la première nuit
        await self.night_phase(game)
    
    async def cupidon_phase(self, game: LoupGarouGame):
        """Phase de Cupidon pour désigner les amoureux"""
        cupidon_id = next((uid for uid, role in game.roles.items() if role == "cupidon"), None)
        if not cupidon_id:
            return
        
        cupidon = game.players[cupidon_id]
        
        # Crée un select pour choisir 2 joueurs
        options = [
            discord.SelectOption(
                label=game.players[uid].display_name,
                value=str(uid),
                emoji="💘"
            )
            for uid in game.alive_players
        ]
        
        view = discord.ui.View(timeout=60)
        select = discord.ui.Select(
            placeholder="Choisissez les deux amoureux...",
            options=options,
            min_values=2,
            max_values=2
        )
        
        lovers_chosen = asyncio.Event()
        
        async def cupidon_callback(interaction: discord.Interaction):
            if interaction.user.id != cupidon_id:
                await interaction.response.send_message("Ce n'est pas à vous de choisir !", ephemeral=True)
                return
            
            game.lovers = [int(val) for val in select.values]
            await interaction.response.send_message(
                f"💘 Vous avez désigné {game.players[game.lovers[0]].mention} et {game.players[game.lovers[1]].mention} comme amoureux !",
                ephemeral=True
            )
            lovers_chosen.set()
        
        select.callback = cupidon_callback
        view.add_item(select)
        
        try:
            await cupidon.send("💘 **Cupidon**, choisissez deux joueurs qui seront liés par l'amour !", view=view)
            
            # Attend le choix avec timeout
            try:
                await asyncio.wait_for(lovers_chosen.wait(), timeout=60)
            except asyncio.TimeoutError:
                # Si pas de choix, sélection aléatoire
                game.lovers = random.sample(list(game.alive_players), 2)
            
            # Informe les amoureux
            for lover_id in game.lovers:
                lover = game.players[lover_id]
                other_lover_id = game.lovers[0] if game.lovers[1] == lover_id else game.lovers[1]
                other_lover = game.players[other_lover_id]
                
                try:
                    await lover.send(f"💘 Vous êtes tombé(e) amoureux(se) de {other_lover.mention} !")
                except discord.Forbidden:
                    pass
        
        except discord.Forbidden:
            logger.warning(f"Impossible d'envoyer un message à Cupidon")
    
    async def mayor_election(self, game: LoupGarouGame):
        """Élection du maire"""
        embed = discord.Embed(
            title="🎖️ Élection du Maire",
            description=_("loupgarou.mayor_election_description", None, game.guild_id),
            color=discord.Color.gold()
        )
        await game.channel.send(embed=embed)
        
        # Créer les options de vote
        options = [
            discord.SelectOption(
                label=game.players[uid].display_name,
                value=str(uid),
                emoji="🎖️"
            )
            for uid in game.alive_players
        ]
        
        view = discord.ui.View(timeout=60)
        select = discord.ui.Select(
            placeholder=_("loupgarou.mayor_vote_placeholder", None, game.guild_id),
            options=options,
            min_values=1,
            max_values=1
        )
        
        mayor_votes: Dict[int, int] = {}  # voter_id -> candidate_id
        vote_complete = asyncio.Event()
        
        async def mayor_callback(interaction: discord.Interaction):
            if interaction.user.id not in game.alive_players:
                await interaction.response.send_message(
                    _("loupgarou.dead_cant_vote", None, game.guild_id),
                    ephemeral=True
                )
                return
            
            candidate_id = int(select.values[0])
            mayor_votes[interaction.user.id] = candidate_id
            
            await interaction.response.send_message(
                _("loupgarou.mayor_vote_registered", None, game.guild_id).format(
                    game.players[candidate_id].display_name
                ),
                ephemeral=True
            )
            
            # Vérifier si tous les joueurs ont voté
            if len(mayor_votes) >= len(game.alive_players):
                vote_complete.set()
        
        select.callback = mayor_callback
        view.add_item(select)
        
        vote_message = await game.channel.send(
            _("loupgarou.mayor_voting_phase", None, game.guild_id),
            view=view
        )
        
        try:
            await asyncio.wait_for(vote_complete.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
        
        # Compter les votes
        vote_counts: Dict[int, int] = {}
        for candidate_id in mayor_votes.values():
            vote_counts[candidate_id] = vote_counts.get(candidate_id, 0) + 1
        
        # Trouver le gagnant
        if vote_counts:
            max_votes = max(vote_counts.values())
            winners = [cid for cid, count in vote_counts.items() if count == max_votes]
            
            if len(winners) > 1:
                # Égalité, choix aléatoire
                game.mayor = random.choice(winners)
            else:
                game.mayor = winners[0]
        else:
            # Personne n'a voté, choix aléatoire
            game.mayor = random.choice(list(game.alive_players))
        
        # Annoncer le maire
        mayor = game.players[game.mayor]
        embed = discord.Embed(
            title="🎖️ " + _("loupgarou.mayor_elected", None, game.guild_id),
            description=_("loupgarou.mayor_elected_description", None, game.guild_id).format(mayor.mention),
            color=discord.Color.gold()
        )
        await game.channel.send(embed=embed)
    
    async def night_phase(self, game: LoupGarouGame):
        """Phase de nuit"""
        game.phase = "night"
        game.day_number += 1
        game.night_actions = {}
        
        embed = discord.Embed(
            title=f"🌙 {_('loupgarou.night_falls', game.organizer.id, game.guild_id).format(game.day_number)}",
            description=_("loupgarou.night_description", game.organizer.id, game.guild_id),
            color=discord.Color.dark_blue()
        )
        await game.channel.send(embed=embed)
        
        # Phase des loups-garous
        status_msg = await game.channel.send("🐺 **Les loups-garous se réveillent et choisissent leur victime...**")
        await self.werewolves_action(game)
        await status_msg.edit(content="🐺 ~~Les loups-garous se réveillent et choisissent leur victime...~~ ✅")
        
        # Phase de la voyante
        if any(game.roles.get(uid) == "voyante" for uid in game.alive_players):
            status_msg = await game.channel.send("🔮 **La voyante se réveille et espionne un joueur...**")
            await self.seer_action(game)
            await status_msg.edit(content="🔮 ~~La voyante se réveille et espionne un joueur...~~ ✅")
        
        # Phase de la sorcière
        if any(game.roles.get(uid) == "sorciere" for uid in game.alive_players):
            status_msg = await game.channel.send("🧙‍♀️ **La sorcière se réveille et décide d'utiliser ses potions...**")
            await self.witch_action(game)
            await status_msg.edit(content="🧙‍♀️ ~~La sorcière se réveille et décide d'utiliser ses potions...~~ ✅")
        
        # Attend un peu avant de passer au jour
        await asyncio.sleep(5)
        
        # Résolution de la nuit
        await self.resolve_night(game)
    
    async def werewolves_action(self, game: LoupGarouGame):
        """Action des loups-garous pendant la nuit"""
        werewolves = [uid for uid in game.alive_players if game.roles[uid] == "loup"]
        if not werewolves:
            return
        
        # Crée un select pour choisir une victime
        non_werewolf_players = [uid for uid in game.alive_players if game.roles[uid] != "loup"]
        if not non_werewolf_players:
            return
        
        options = [
            discord.SelectOption(
                label=game.players[uid].display_name,
                value=str(uid),
                emoji="🎯"
            )
            for uid in non_werewolf_players
        ]
        
        view = discord.ui.View(timeout=45)
        select = discord.ui.Select(
            placeholder="Choisissez votre victime...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        votes = {}
        vote_event = asyncio.Event()
        
        async def wolf_callback(interaction: discord.Interaction):
            if interaction.user.id not in werewolves:
                await interaction.response.send_message("Vous n'êtes pas un loup-garou !", ephemeral=True)
                return
            
            victim_id = int(select.values[0])
            votes[interaction.user.id] = victim_id
            
            await interaction.response.send_message(
                f"Vous avez voté pour {game.players[victim_id].display_name}",
                ephemeral=True
            )
            
            # Si tous les loups ont voté
            if len(votes) == len(werewolves):
                vote_event.set()
        
        select.callback = wolf_callback
        view.add_item(select)
        
        # Envoie le message à chaque loup
        for wolf_id in werewolves:
            wolf = game.players[wolf_id]
            try:
                await wolf.send("🐺 **Loups-Garous**, choisissez votre victime pour cette nuit !", view=view)
            except discord.Forbidden:
                logger.warning(f"Impossible d'envoyer un message au loup {wolf.name}")
        
        # Attend les votes avec timeout
        try:
            await asyncio.wait_for(vote_event.wait(), timeout=45)
        except asyncio.TimeoutError:
            pass
        
        # Détermine la victime (vote majoritaire ou aléatoire)
        if votes:
            from collections import Counter
            vote_counts = Counter(votes.values())
            victim_id = vote_counts.most_common(1)[0][0]
            game.night_actions["werewolves"] = victim_id
    
    async def seer_action(self, game: LoupGarouGame):
        """Action de la voyante pendant la nuit"""
        seer_id = next((uid for uid in game.alive_players if game.roles[uid] == "voyante"), None)
        if not seer_id:
            return
        
        seer = game.players[seer_id]
        
        # Crée un select pour choisir un joueur à espionner
        other_players = [uid for uid in game.alive_players if uid != seer_id]
        options = [
            discord.SelectOption(
                label=game.players[uid].display_name,
                value=str(uid),
                emoji="❓"
            )
            for uid in other_players
        ]
        
        view = discord.ui.View(timeout=30)
        select = discord.ui.Select(
            placeholder="Choisissez un joueur à espionner...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        vision_event = asyncio.Event()
        
        async def seer_callback(interaction: discord.Interaction):
            if interaction.user.id != seer_id:
                await interaction.response.send_message("Vous n'êtes pas la voyante !", ephemeral=True)
                return
            
            target_id = int(select.values[0])
            target_role = game.roles[target_id]
            role_name = _(f'loupgarou.role.{target_role}', seer_id, game.guild_id)
            role_emoji = ROLES[target_role]["emoji"]
            
            await interaction.response.send_message(
                f"🔮 Vous avez espionné {game.players[target_id].display_name}.\n"
                f"**Rôle révélé :** {role_emoji} **{role_name}**",
                ephemeral=True
            )
            vision_event.set()
        
        select.callback = seer_callback
        view.add_item(select)
        
        try:
            await seer.send("🔮 **Voyante**, choisissez un joueur à espionner cette nuit !", view=view)
            
            try:
                await asyncio.wait_for(vision_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass
        
        except discord.Forbidden:
            logger.warning(f"Impossible d'envoyer un message à la voyante")
    
    async def witch_action(self, game: LoupGarouGame):
        """Action de la sorcière pendant la nuit"""
        witch_id = next((uid for uid in game.alive_players if game.roles[uid] == "sorciere"), None)
        if not witch_id:
            return
        
        witch = game.players[witch_id]
        victim_id = game.night_actions.get("werewolves")
        
        # La sorcière peut voir qui va mourir et utiliser ses potions
        buttons = []
        
        if not game.sorciere_heal_used and victim_id:
            buttons.append(discord.ui.Button(label="💚 Sauver", style=discord.ButtonStyle.green, custom_id="heal"))
        
        if not game.sorciere_poison_used:
            buttons.append(discord.ui.Button(label="☠️ Empoisonner", style=discord.ButtonStyle.red, custom_id="poison"))
        
        buttons.append(discord.ui.Button(label="⏭️ Passer", style=discord.ButtonStyle.gray, custom_id="skip"))
        
        if not buttons or (len(buttons) == 1 and buttons[0].custom_id == "skip"):
            return
        
        view = discord.ui.View(timeout=30)
        for button in buttons:
            view.add_item(button)
        
        witch_event = asyncio.Event()
        
        async def witch_callback(interaction: discord.Interaction):
            if interaction.user.id != witch_id:
                await interaction.response.send_message("Vous n'êtes pas la sorcière !", ephemeral=True)
                return
            
            action = interaction.data["custom_id"]
            
            if action == "heal":
                game.night_actions["witch_heal"] = victim_id
                game.sorciere_heal_used = True
                await interaction.response.send_message("💚 Vous avez sauvé la victime !", ephemeral=True)
            
            elif action == "poison":
                # Demande qui empoisonner
                poison_options = [
                    discord.SelectOption(
                        label=game.players[uid].display_name,
                        value=str(uid),
                        emoji="☠️"
                    )
                    for uid in game.alive_players if uid != witch_id
                ]
                
                poison_view = discord.ui.View(timeout=20)
                poison_select = discord.ui.Select(
                    placeholder="Choisissez qui empoisonner...",
                    options=poison_options,
                    min_values=1,
                    max_values=1
                )
                
                async def poison_callback(poison_interaction: discord.Interaction):
                    poison_target = int(poison_select.values[0])
                    game.night_actions["witch_poison"] = poison_target
                    game.sorciere_poison_used = True
                    await poison_interaction.response.send_message(
                        f"☠️ Vous avez empoisonné {game.players[poison_target].display_name} !",
                        ephemeral=True
                    )
                    witch_event.set()
                
                poison_select.callback = poison_callback
                poison_view.add_item(poison_select)
                
                await interaction.response.send_message("☠️ Choisissez qui empoisonner :", view=poison_view, ephemeral=True)
                return
            
            else:  # skip
                await interaction.response.send_message("Vous n'utilisez aucune potion.", ephemeral=True)
            
            witch_event.set()
        
        for button in buttons:
            button.callback = witch_callback
        
        message = "🧙‍♀️ **Sorcière**, c'est votre tour !"
        if victim_id:
            message += f"\n\nLes loups ont choisi {game.players[victim_id].display_name} comme victime."
        
        try:
            await witch.send(message, view=view)
            
            try:
                await asyncio.wait_for(witch_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass
        
        except discord.Forbidden:
            logger.warning(f"Impossible d'envoyer un message à la sorcière")
    
    async def resolve_night(self, game: LoupGarouGame):
        """Résout les actions de la nuit"""
        victims = []
        
        # Victime des loups
        werewolf_victim = game.night_actions.get("werewolves")
        if werewolf_victim:
            # Vérifie si la sorcière a sauvé
            if game.night_actions.get("witch_heal") != werewolf_victim:
                victims.append(werewolf_victim)
                game.last_victim = werewolf_victim
        
        # Victime de la sorcière
        witch_victim = game.night_actions.get("witch_poison")
        if witch_victim:
            victims.append(witch_victim)
        
        # Tue les victimes
        for victim_id in victims:
            game.kill_player(victim_id)
        
        # Annonce les morts
        await self.announce_deaths(game, victims)
        
        # Vérifie la victoire
        winner = game.check_victory()
        if winner:
            await self.end_game(game, winner)
            return
        
        # Passe au jour
        await self.day_phase(game)
    
    async def announce_deaths(self, game: LoupGarouGame, victims: List[int]):
        """Annonce les morts de la nuit"""
        embed = discord.Embed(
            title=f"☀️ {_('loupgarou.day_breaks', game.organizer.id, game.guild_id)}",
            color=discord.Color.gold()
        )
        
        if not victims:
            embed.description = _("loupgarou.no_deaths", game.organizer.id, game.guild_id)
        else:
            deaths_text = []
            for victim_id in victims:
                victim = game.players[victim_id]
                role = game.roles[victim_id]
                deaths_text.append(f"💀 {victim.mention} ({ROLES[role]['emoji']} {_(f'loupgarou.role.{role}', game.organizer.id, game.guild_id)})")
            
            embed.description = "\n".join(deaths_text)
            
            # Si une seule victime, ajoute sa photo de profil
            if len(victims) == 1:
                victim = game.players[victims[0]]
                embed.set_thumbnail(url=victim.display_avatar.url)
        
        await game.channel.send(embed=embed)
        
        # Chasseur peut tirer
        for victim_id in victims:
            if game.roles[victim_id] == "chasseur":
                await self.hunter_action(game, victim_id)
    
    async def hunter_action(self, game: LoupGarouGame, hunter_id: int):
        """Le chasseur tire sur quelqu'un en mourant"""
        hunter = game.players[hunter_id]
        
        options = [
            discord.SelectOption(
                label=game.players[uid].display_name,
                value=str(uid),
                emoji="🎯"
            )
            for uid in game.alive_players
        ]
        
        view = discord.ui.View(timeout=30)
        select = discord.ui.Select(
            placeholder="Choisissez qui abattre...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        shot_event = asyncio.Event()
        target = [None]
        
        async def hunter_callback(interaction: discord.Interaction):
            if interaction.user.id != hunter_id:
                await interaction.response.send_message("Vous n'êtes pas le chasseur !", ephemeral=True)
                return
            
            target[0] = int(select.values[0])
            await interaction.response.send_message(
                f"🏹 Vous avez tiré sur {game.players[target[0]].display_name} !",
                ephemeral=True
            )
            shot_event.set()
        
        select.callback = hunter_callback
        view.add_item(select)
        
        try:
            await hunter.send("🏹 **Chasseur**, vous êtes mort ! Choisissez qui abattre avec vous !", view=view)
            
            try:
                await asyncio.wait_for(shot_event.wait(), timeout=30)
                
                if target[0]:
                    game.kill_player(target[0])
                    victim = game.players[target[0]]
                    role = game.roles[target[0]]
                    
                    embed = discord.Embed(
                        title="🏹 Le chasseur tire !",
                        description=f"{hunter.mention} abat {victim.mention} ({ROLES[role]['emoji']} {_(f'loupgarou.role.{role}', game.organizer.id, game.guild_id)}) !",
                        color=discord.Color.orange()
                    )
                    embed.set_thumbnail(url=victim.display_avatar.url)
                    await game.channel.send(embed=embed)
            
            except asyncio.TimeoutError:
                pass
        
        except discord.Forbidden:
            logger.warning(f"Impossible d'envoyer un message au chasseur")
    
    async def day_phase(self, game: LoupGarouGame):
        """Phase de jour - discussion et vote"""
        game.phase = "day"
        
        embed = discord.Embed(
            title=f"☀️ {_('loupgarou.day_phase', game.organizer.id, game.guild_id).format(game.day_number)}",
            description=_("loupgarou.day_description", game.organizer.id, game.guild_id),
            color=discord.Color.gold()
        )
        
        # Liste les joueurs vivants
        alive_list = "\n".join([
            f"• {game.players[uid].mention}"
            for uid in game.alive_players
        ])
        embed.add_field(
            name=f"👥 {_('loupgarou.alive_players', game.organizer.id, game.guild_id)} ({len(game.alive_players)})",
            value=alive_list,
            inline=False
        )
        
        discussion_msg = await game.channel.send(embed=embed)
        
        # Attend un peu pour la discussion avec compte à rebours
        discussion_time = 60
        for remaining in range(discussion_time, 0, -15):
            if remaining < discussion_time:
                embed.set_footer(text=f"⏱️ Discussion - Temps restant: {remaining}s")
                try:
                    await discussion_msg.edit(embed=embed)
                except:
                    pass
            await asyncio.sleep(min(15, remaining))
        
        # Phase de vote
        await self.voting_phase(game)
    
    async def voting_phase(self, game: LoupGarouGame):
        """Phase de vote pour éliminer un joueur"""
        game.phase = "voting"
        game.votes = {}
        game.vote_times = {}
        
        import time
        game.vote_start_time = time.time()
        
        embed = discord.Embed(
            title=f"🗳️ {_('loupgarou.voting_phase', game.organizer.id, game.guild_id)}",
            description=_("loupgarou.voting_description", game.organizer.id, game.guild_id),
            color=discord.Color.blue()
        )
        
        view = VoteView(game, self)
        vote_message = await game.channel.send(embed=embed, view=view)
        
        # Attend les votes avec compte à rebours
        timeout = 120
        start_time = asyncio.get_event_loop().time()
        
        try:
            while True:
                # Attend soit la fin du timeout, soit que tous aient voté
                remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining <= 0:
                    break
                
                try:
                    await asyncio.wait_for(view.vote_complete.wait(), timeout=min(remaining, 30))
                    # Tous ont voté !
                    break
                except asyncio.TimeoutError:
                    # Met à jour le compte à rebours toutes les 30s
                    remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                    if remaining > 0:
                        embed.set_footer(text=f"⏱️ Temps restant: {int(remaining)}s | Votes: {len(game.votes)}/{len(game.alive_players)}")
                        try:
                            await vote_message.edit(embed=embed)
                        except:
                            pass
        except Exception as e:
            logger.error(f"Erreur pendant le vote: {e}")
        
        # Mise à jour finale pour afficher le compte correct
        embed.set_footer(text=f"✅ Vote terminé | Votes: {len(game.votes)}/{len(game.alive_players)}")
        try:
            await vote_message.edit(embed=embed)
        except:
            pass
        
        # Compte les votes
        await self.resolve_vote(game)
    
    async def resolve_vote(self, game: LoupGarouGame):
        """Résout le vote du village"""
        if not game.votes:
            embed = discord.Embed(
                title=f"{INFO} {_('loupgarou.no_votes', game.organizer.id, game.guild_id)}",
                description=_("loupgarou.no_elimination", game.organizer.id, game.guild_id),
                color=discord.Color.blue()
            )
            await game.channel.send(embed=embed)
        else:
            from collections import Counter
            vote_counts = Counter(game.votes.values())
            
            # Affiche les résultats avec comptage
            results_text = []
            for target_id, count in vote_counts.most_common():
                target = game.players[target_id]
                results_text.append(f"• {target.mention}: **{count}** vote(s)")
            
            # Détail des votes (qui a voté pour qui et quand)
            vote_details = []
            # Trie par temps de vote
            sorted_voters = sorted(game.vote_times.items(), key=lambda x: x[1])
            for voter_id, vote_time in sorted_voters:
                voter = game.players[voter_id]
                target = game.players[game.votes[voter_id]]
                minutes = int(vote_time // 60)
                seconds = int(vote_time % 60)
                time_str = f"{minutes}m{seconds}s" if minutes > 0 else f"{seconds}s"
                vote_details.append(f"• {voter.mention} → {target.mention} *(après {time_str})*")
            
            # Détermine l'éliminé
            max_votes = vote_counts.most_common(1)[0][1]
            top_voted = [uid for uid, count in vote_counts.items() if count == max_votes]
            
            if len(top_voted) > 1:
                # Égalité - le maire décide
                embed = discord.Embed(
                    title=f"{INFO} {_('loupgarou.vote_tie', game.organizer.id, game.guild_id)}",
                    description="\n".join(results_text),
                    color=discord.Color.blue()
                )
                if vote_details:
                    embed.add_field(
                        name="📊 Détail des votes",
                        value="\n".join(vote_details),
                        inline=False
                    )
                await game.channel.send(embed=embed)
                
                # Le maire décide
                if game.mayor and game.mayor in game.alive_players:
                    mayor = game.players[game.mayor]
                    
                    # Créer les options pour le maire
                    options = [
                        discord.SelectOption(
                            label=game.players[uid].display_name,
                            value=str(uid),
                            emoji="⚖️"
                        )
                        for uid in top_voted if uid in game.alive_players
                    ]
                    
                    view = discord.ui.View(timeout=30)
                    select = discord.ui.Select(
                        placeholder=_("loupgarou.mayor_decide_placeholder", None, game.guild_id),
                        options=options,
                        min_values=1,
                        max_values=1
                    )
                    
                    decision_made = asyncio.Event()
                    chosen_id = [None]
                    
                    async def mayor_decision_callback(interaction: discord.Interaction):
                        if interaction.user.id != game.mayor:
                            await interaction.response.send_message(
                                _("loupgarou.only_mayor_can_decide", None, game.guild_id),
                                ephemeral=True
                            )
                            return
                        
                        chosen_id[0] = int(select.values[0])
                        await interaction.response.send_message(
                            _("loupgarou.mayor_decision_made", None, game.guild_id),
                            ephemeral=True
                        )
                        decision_made.set()
                    
                    select.callback = mayor_decision_callback
                    view.add_item(select)
                    
                    embed = discord.Embed(
                        title="🎖️ " + _("loupgarou.mayor_decides", None, game.guild_id),
                        description=_("loupgarou.mayor_decides_description", None, game.guild_id).format(mayor.mention),
                        color=discord.Color.gold()
                    )
                    await game.channel.send(embed=embed, view=view)
                    
                    try:
                        await asyncio.wait_for(decision_made.wait(), timeout=30)
                        if chosen_id[0]:
                            eliminated_id = chosen_id[0]
                        else:
                            # Timeout, choix aléatoire
                            eliminated_id = random.choice(top_voted)
                    except asyncio.TimeoutError:
                        # Timeout, choix aléatoire
                        eliminated_id = random.choice(top_voted)
                    
                    # Annoncer la décision du maire
                    eliminated = game.players[eliminated_id]
                    role = game.roles[eliminated_id]
                    game.kill_player(eliminated_id)
                    
                    embed = discord.Embed(
                        title=f"🎖️ {_('loupgarou.mayor_decision', None, game.guild_id)}",
                        description=(
                            f"{mayor.mention} a décidé d'éliminer {eliminated.mention} !\n" +
                            f"C'était {ROLES[role]['emoji']} **{_(f'loupgarou.role.{role}', None, game.guild_id)}**"
                        ),
                        color=discord.Color.red()
                    )
                    embed.set_thumbnail(url=eliminated.display_avatar.url)
                    await game.channel.send(embed=embed)
                    
                    # Vérifier si c'est l'ange au premier vote
                    if game.angel_id == eliminated_id and not game.angel_first_vote_passed:
                        await self.angel_wins(game, eliminated_id)
                        return
                    
                    # Chasseur peut tirer
                    if role == "chasseur":
                        await self.hunter_action(game, eliminated_id)
                else:
                    # Pas de maire, personne n'est éliminé
                    pass
            else:
                eliminated_id = top_voted[0]
                eliminated = game.players[eliminated_id]
                role = game.roles[eliminated_id]
                
                game.kill_player(eliminated_id)
                
                embed = discord.Embed(
                    title=f"⚖️ {_('loupgarou.player_eliminated', game.organizer.id, game.guild_id)}",
                    description=(
                        f"**{_('loupgarou.vote_results', game.organizer.id, game.guild_id)}:**\n" +
                        "\n".join(results_text) +
                        f"\n\n{eliminated.mention} a été éliminé(e) !\n" +
                        f"C'était {ROLES[role]['emoji']} **{_(f'loupgarou.role.{role}', game.organizer.id, game.guild_id)}**"
                    ),
                    color=discord.Color.red()
                )
                # Ajoute la photo de profil du mort
                embed.set_thumbnail(url=eliminated.display_avatar.url)
                
                # Ajoute le détail des votes
                if vote_details:
                    embed.add_field(
                        name="📊 Détail des votes",
                        value="\n".join(vote_details),
                        inline=False
                    )
                
                await game.channel.send(embed=embed)
                
                # Vérifier si c'est l'ange au premier vote
                if game.angel_id == eliminated_id and not game.angel_first_vote_passed:
                    await self.angel_wins(game, eliminated_id)
                    return
                
                # Chasseur peut tirer
                if role == "chasseur":
                    await self.hunter_action(game, eliminated_id)
        
        # Marquer que le premier vote est passé (pour l'ange)
        if not game.angel_first_vote_passed:
            game.angel_first_vote_passed = True
        
        # Vérifie la victoire
        winner = game.check_victory()
        if winner:
            await self.end_game(game, winner)
            return
        
        # Retourne à la nuit
        await asyncio.sleep(5)
        await self.night_phase(game)
    
    async def angel_wins(self, game: LoupGarouGame, angel_id: int):
        """L'ange gagne en solo"""
        game.phase = "ended"
        
        angel = game.players[angel_id]
        
        embed = discord.Embed(
            title=f"👼 {_('loupgarou.angel_wins', None, game.guild_id)}",
            description=_("loupgarou.angel_wins_description", None, game.guild_id).format(angel.mention),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=angel.display_avatar.url)
        
        # Affiche tous les rôles
        roles_text = []
        for user_id, role in game.roles.items():
            member = game.players[user_id]
            status = "💀" if user_id in game.dead_players else "✅"
            roles_text.append(
                f"{status} {member.mention}: {ROLES[role]['emoji']} {_(f'loupgarou.role.{role}', None, game.guild_id)}"
            )
        
        embed.add_field(
            name=f"🎭 {_('loupgarou.roles_reveal', None, game.guild_id)}",
            value="\n".join(roles_text),
            inline=False
        )
        
        await game.channel.send(embed=embed)
        
        # Supprime la partie de la liste
        if game.guild_id in self.games:
            del self.games[game.guild_id]
    
    async def end_game(self, game: LoupGarouGame, winner: str):
        """Termine la partie"""
        game.phase = "ended"
        
        if winner == "village":
            title = f"🎉 {_('loupgarou.village_wins', game.organizer.id, game.guild_id)}"
            color = discord.Color.green()
        elif winner == "loups":
            title = f"🐺 {_('loupgarou.werewolves_win', game.organizer.id, game.guild_id)}"
            color = discord.Color.dark_red()
        else:  # lovers
            title = f"💘 {_('loupgarou.lovers_win', game.organizer.id, game.guild_id)}"
            color = discord.Color.purple()
        
        embed = discord.Embed(
            title=title,
            description=_("loupgarou.game_over", game.organizer.id, game.guild_id),
            color=color
        )
        
        # Affiche tous les rôles
        roles_text = []
        for user_id, role in game.roles.items():
            member = game.players[user_id]
            status = "💀" if user_id in game.dead_players else "✅"
            roles_text.append(
                f"{status} {member.mention}: {ROLES[role]['emoji']} {_(f'loupgarou.role.{role}', game.organizer.id, game.guild_id)}"
            )
        
        embed.add_field(
            name=f"🎭 {_('loupgarou.roles_reveal', game.organizer.id, game.guild_id)}",
            value="\n".join(roles_text),
            inline=False
        )
        
        await game.channel.send(embed=embed)
        
        # Supprime la partie
        if game.guild_id in self.games:
            del self.games[game.guild_id]
        
        logger.info(f"Partie de Loup-Garou terminée dans la guilde {game.guild_id} - Victoire: {winner}")

async def setup(bot):
    await bot.add_cog(LoupGarou(bot))
