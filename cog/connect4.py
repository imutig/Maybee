
import discord
from discord import app_commands
from discord.ext import commands

CONNECT4_COLUMNS = 7
CONNECT4_ROWS = 6
EMOJIS = {0: "⚪", 1: "🔴", 2: "🟡"}

class Connect4Game:
    def __init__(self, player1, player2):
        self.board = [[0 for _ in range(CONNECT4_COLUMNS)] for _ in range(CONNECT4_ROWS)]
        self.players = [player1, player2]
        self.turn = 0  # 0: player1, 1: player2
        self.winner = None
        self.finished = False
        self.last_col = None

    def drop_piece(self, col):
        for row in reversed(range(CONNECT4_ROWS)):
            if self.board[row][col] == 0:
                self.board[row][col] = self.turn + 1
                self.last_col = col
                if self.check_win(row, col):
                    self.winner = self.players[self.turn]
                    self.finished = True
                self.turn = 1 - self.turn
                return True
        return False

    def check_win(self, row, col):
        piece = self.board[row][col]
        directions = [(1,0),(0,1),(1,1),(1,-1)]
        for dr, dc in directions:
            count = 1
            for d in [1,-1]:
                r, c = row, col
                while True:
                    r += dr*d
                    c += dc*d
                    if 0 <= r < CONNECT4_ROWS and 0 <= c < CONNECT4_COLUMNS and self.board[r][c] == piece:
                        count += 1
                    else:
                        break
            if count >= 4:
                return True
        return False

    def render(self):
        rows = []
        for row in self.board:
            rows.append(''.join(EMOJIS[cell] for cell in row))
        # Ajoute les numéros de colonne en bas
        col_numbers = ''.join(f'{i+1}\u20e3' for i in range(CONNECT4_COLUMNS))
        rows.append(col_numbers)
        return '\n'.join(rows)

class Connect4View(discord.ui.View):
    def make_embed(self):
        embed = discord.Embed(title="Puissance 4", color=discord.Color.gold())
        embed.description = f"{self.game.render()}"
        embed.add_field(name="Joueurs", value=f"🔴 {self.game.players[0].mention}  vs  🟡 {self.game.players[1].mention}", inline=False)
        if self.game.last_col is not None:
            embed.add_field(name="Dernière colonne jouée", value=f"{self.game.last_col+1}", inline=True)
        if self.game.finished:
            embed.add_field(name="Résultat", value=f"Victoire de {self.game.winner.mention} !", inline=False)
        else:
            embed.add_field(name="Tour", value=f"C'est au tour de {self.game.players[self.game.turn].mention}", inline=False)
        embed.set_thumbnail(url=self.game.players[self.game.turn].display_avatar.url)
        embed.set_footer(text="Connect4 Discord")
        return embed
    def __init__(self, game, cog, interaction):
        super().__init__(timeout=180)
        self.game = game
        self.cog = cog
        self.interaction = interaction
        for i in range(CONNECT4_COLUMNS):
            self.add_item(Connect4Button(i))
        self.add_item(Connect4ForfeitButton())

class Connect4ForfeitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Abandonner", style=discord.ButtonStyle.danger, row=1)

    async def callback(self, interaction: discord.Interaction):
        game = self.view.game
        if game.finished:
            await interaction.response.send_message("La partie est déjà terminée.", ephemeral=True)
            return
        if interaction.user not in game.players:
            await interaction.response.send_message("Vous ne jouez pas dans cette partie.", ephemeral=True)
            return
        quitter = interaction.user
        gagnant = game.players[1] if quitter == game.players[0] else game.players[0]
        game.finished = True
        game.winner = gagnant
        await self.view.update_message(interaction)

    async def update_message(self, interaction=None):
        embed = self.make_embed()
        for btn in self.children:
            if isinstance(btn, Connect4Button):
                col_full = all(self.game.board[row][btn.column] != 0 for row in range(CONNECT4_ROWS))
                btn.disabled = self.game.finished or col_full
        if interaction:
            await interaction.response.edit_message(embed=embed, view=(None if self.game.finished else self))
        else:
            await self.interaction.edit_original_response(embed=embed, view=(None if self.game.finished else self))

    def make_embed(self):
        embed = discord.Embed(title="Puissance 4", color=discord.Color.gold())
        embed.description = f"{self.game.render()}"
        embed.add_field(name="Joueurs", value=f"🔴 {self.game.players[0].mention}  vs  🟡 {self.game.players[1].mention}", inline=False)
        if self.game.last_col is not None:
            embed.add_field(name="Dernière colonne jouée", value=f"{self.game.last_col+1}", inline=True)
        if self.game.finished:
            embed.add_field(name="Résultat", value=f"Victoire de {self.game.winner.mention} !", inline=False)
        else:
            embed.add_field(name="Tour", value=f"C'est au tour de {self.game.players[self.game.turn].mention}", inline=False)
        embed.set_thumbnail(url=self.game.players[self.game.turn].display_avatar.url)
        embed.set_footer(text="Connect4 Discord")
        return embed

class Connect4Button(discord.ui.Button):
    def __init__(self, column):
        super().__init__(label=str(column+1), style=discord.ButtonStyle.primary)
        self.column = column

    async def callback(self, interaction: discord.Interaction):
        game = self.view.game
        if game.finished:
            await interaction.response.send_message("La partie est terminée.", ephemeral=True)
            return
        if interaction.user != game.players[game.turn]:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        if not game.drop_piece(self.column):
            await interaction.response.send_message("Cette colonne est pleine.", ephemeral=True)
            return
        await interaction.response.edit_message(embed=self.view.make_embed(), view=(None if game.finished else self.view))
        # Si c'est au bot de jouer et la partie n'est pas finie
        if not game.finished and game.players[game.turn].bot:
            await self.bot_play()

    async def bot_play(self):
        game = self.view.game
        valid_cols = [col for col in range(CONNECT4_COLUMNS) if any(game.board[row][col] == 0 for row in range(CONNECT4_ROWS))]
        if not valid_cols:
            return
        import random
        col = random.choice(valid_cols)
        game.drop_piece(col)
        await self.view.interaction.edit_original_response(embed=self.view.make_embed(), view=(None if game.finished else self.view))

class Connect4(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @app_commands.command(name="connect4", description="Jouer à Puissance 4 contre un joueur ou le bot")
    @app_commands.describe(opponent="Mentionnez un joueur (optionnel, par défaut le bot)")
    async def connect4(self, interaction: discord.Interaction, opponent: discord.User = None):
        player1 = interaction.user
        player2 = opponent if opponent is not None else self.bot.user
        game = Connect4Game(player1, player2)
        self.active_games[interaction.channel_id] = game
        view = Connect4View(game, self, interaction)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Connect4(bot))
