import discord
from discord import app_commands
from discord.ext import commands

EMOJIS = {0: "⬜", 1: "❌", 2: "⭕"}

class TicTacToeGame:
    def __init__(self, player1, player2):
        self.board = [[0 for _ in range(3)] for _ in range(3)]
        self.players = [player1, player2]
        self.turn = 0  # 0: player1, 1: player2
        self.winner = None
        self.finished = False
        self.moves = 0

    def play(self, row, col):
        if self.board[row][col] != 0 or self.finished:
            return False
        self.board[row][col] = self.turn + 1
        self.moves += 1
        if self.check_win(row, col):
            self.winner = self.players[self.turn]
            self.finished = True
        elif self.moves == 9:
            self.finished = True  # Draw
        self.turn = 1 - self.turn
        return True

    def check_win(self, row, col):
        piece = self.board[row][col]
        # Check row, col, diagonals
        if all(self.board[row][c] == piece for c in range(3)):
            return True
        if all(self.board[r][col] == piece for r in range(3)):
            return True
        if row == col and all(self.board[i][i] == piece for i in range(3)):
            return True
        if row + col == 2 and all(self.board[i][2-i] == piece for i in range(3)):
            return True
        return False

    def render(self):
        return '\n'.join(''.join(EMOJIS[cell] for cell in row) for row in self.board)

class TicTacToeView(discord.ui.View):
    def __init__(self, game, interaction):
        super().__init__(timeout=120)
        self.game = game
        self.interaction = interaction
        for r in range(3):
            for c in range(3):
                self.add_item(TicTacToeButton(r, c, self))

    async def update_message(self):
        content = f"TicTacToe : {self.game.players[0].mention} vs {self.game.players[1].mention}\n{self.game.render()}"
        if self.game.finished:
            if self.game.winner:
                content += f"\nVictoire de {self.game.winner.mention} !"
            else:
                content += "\nMatch nul !"
        else:
            content += f"\nC'est au tour de {self.game.players[self.game.turn].mention} !"
        await self.interaction.edit_original_response(content=content, view=(None if self.game.finished else self))

class TicTacToeButton(discord.ui.Button):
    def __init__(self, row, col, view):
        super().__init__(label="", style=discord.ButtonStyle.secondary, row=row)
        self.row = row
        self.col = col
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        game = self.view.game
        if game.finished:
            await interaction.response.send_message("La partie est terminée.", ephemeral=True)
            return
        if interaction.user != game.players[game.turn]:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        if not game.play(self.row, self.col):
            await interaction.response.send_message("Case déjà prise.", ephemeral=True)
            return
        await self.view.update_message()

class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tictactoe", description="Jouer à TicTacToe contre un joueur ou le bot")
    @app_commands.describe(opponent="Mentionnez un joueur ou choisissez 'bot'")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.User = None):
        player1 = interaction.user
        player2 = opponent if opponent else self.bot.user
        game = TicTacToeGame(player1, player2)
        view = TicTacToeView(game, interaction)
        await interaction.response.send_message(f"TicTacToe : {player1.mention} vs {player2.mention}\n{game.render()}\nC'est au tour de {game.players[game.turn].mention} !", view=view)

async def setup(bot):
    await bot.add_cog(TicTacToe(bot))
