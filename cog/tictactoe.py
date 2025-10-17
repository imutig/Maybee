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
        self.buttons = []
        for r in range(3):
            for c in range(3):
                btn = TicTacToeButton(r, c, self, label=EMOJIS[game.board[r][c]])
                self.add_item(btn)
                self.buttons.append(btn)
    self.add_item(TicTacToeForfeitButton())

class TicTacToeForfeitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Abandonner", style=discord.ButtonStyle.danger, row=3)

    async def callback(self, interaction: discord.Interaction):
        game = self.view.view.game
        if game.finished:
            await interaction.response.send_message("La partie est déjà terminée.", ephemeral=True)
            return
        # Seul un joueur peut abandonner
        if interaction.user not in game.players:
            await interaction.response.send_message("Vous ne jouez pas dans cette partie.", ephemeral=True)
            return
        quitter = interaction.user
        gagnant = game.players[1] if quitter == game.players[0] else game.players[0]
        game.finished = True
        game.winner = gagnant
        await self.view.view.update_message(interaction)

    async def update_message(self, interaction=None):
        # Met à jour les labels des boutons selon l'état du plateau
        for btn in self.buttons:
            btn.label = EMOJIS[self.game.board[btn.row][btn.col]]
            btn.disabled = self.game.board[btn.row][btn.col] != 0 or self.game.finished
        embed = self.make_embed()
        if interaction:
            await interaction.response.edit_message(embed=embed, view=(None if self.game.finished else self))
        else:
            await self.interaction.edit_original_response(embed=embed, view=(None if self.game.finished else self))

    def make_embed(self):
        embed = discord.Embed(title="TicTacToe", color=discord.Color.blurple())
        embed.description = f"{self.game.render()}"
        embed.add_field(name="Joueurs", value=f"❌ {self.game.players[0].mention}  vs  ⭕ {self.game.players[1].mention}", inline=False)
        if self.game.finished:
            if self.game.winner:
                embed.add_field(name="Résultat", value=f"Victoire de {self.game.winner.mention} !", inline=False)
            else:
                embed.add_field(name="Résultat", value="Match nul !", inline=False)
        else:
            embed.add_field(name="Tour", value=f"C'est au tour de {self.game.players[self.game.turn].mention}", inline=False)
        embed.set_thumbnail(url=self.game.players[self.game.turn].display_avatar.url)
        embed.set_footer(text="TicTacToe Discord")
        return embed

import random
class TicTacToeButton(discord.ui.Button):
    def __init__(self, row, col, view, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)
        self.row = row
        self.col = col

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
        await self.view.update_message(interaction)
        # Si c'est au bot de jouer et la partie n'est pas finie
        if not game.finished and game.players[game.turn].bot:
            await self.bot_play()

    async def bot_play(self):
        game = self.view.game
        empty = [(r, c) for r in range(3) for c in range(3) if game.board[r][c] == 0]
        if not empty:
            return
        row, col = random.choice(empty)
        game.play(row, col)
        await self.view.update_message()

class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tictactoe", description="Jouer à TicTacToe contre un joueur ou le bot")
    @app_commands.describe(opponent="Mentionnez un joueur (optionnel, par défaut le bot)")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.User = None):
        player1 = interaction.user
        player2 = opponent if opponent is not None else self.bot.user
        game = TicTacToeGame(player1, player2)
        view = TicTacToeView(game, interaction)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

async def setup(bot):
    await bot.add_cog(TicTacToe(bot))
