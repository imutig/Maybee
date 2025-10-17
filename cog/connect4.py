
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

    def drop_piece(self, col):
        for row in reversed(range(CONNECT4_ROWS)):
            if self.board[row][col] == 0:
                self.board[row][col] = self.turn + 1
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
        return '\n'.join(rows)

class Connect4View(discord.ui.View):
    def __init__(self, game, cog, interaction):
        super().__init__(timeout=180)
        self.game = game
        self.cog = cog
        self.interaction = interaction
        for i in range(CONNECT4_COLUMNS):
            self.add_item(Connect4Button(i, self))

    async def update_message(self):
        content = f"Puissance 4 : {self.game.players[0].mention} vs {self.game.players[1].mention}\n{self.game.render()}"
        if self.game.finished:
            content += f"\nVictoire de {self.game.winner.mention} !"
        else:
            content += f"\nC'est au tour de {self.game.players[self.game.turn].mention} !"
        await self.interaction.edit_original_response(content=content, view=(None if self.game.finished else self))

class Connect4Button(discord.ui.Button):
    def __init__(self, column, view):
        super().__init__(label=str(column+1), style=discord.ButtonStyle.primary)
        self.column = column
        self.view = view

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
        await self.view.update_message()

class Connect4(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @app_commands.command(name="connect4", description="Jouer à Puissance 4 contre un joueur ou le bot")
    @app_commands.describe(opponent="Mentionnez un joueur ou choisissez 'bot'")
    async def connect4(self, interaction: discord.Interaction, opponent: discord.User = None):
        player1 = interaction.user
        player2 = opponent if opponent else self.bot.user
        game = Connect4Game(player1, player2)
        self.active_games[interaction.channel_id] = game
        view = Connect4View(game, self, interaction)
        await interaction.response.send_message(f"Puissance 4 : {player1.mention} vs {player2.mention}\n{game.render()}\nC'est au tour de {game.players[game.turn].mention} !", view=view)

async def setup(bot):
    await bot.add_cog(Connect4(bot))
