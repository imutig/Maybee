import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp

import csv
import os

def charger_mots_fr():
    chemin = os.path.join(os.path.dirname(__file__), 'motsfr.csv')
    mots = set()
    with open(chemin, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        # Trouver la colonne "ortho" même si BOM ou casse
        ortho_col = None
        for col in reader.fieldnames:
            if col.strip().lower() == 'ortho':
                ortho_col = col
                break
        if not ortho_col:
            raise Exception("Colonne 'ortho' non trouvée dans motsfr.csv")
        for row in reader:
            mot = row[ortho_col].strip().lower()
            if len(mot) == 5 and mot.isalpha():
                mots.add(mot)
    return list(mots)

MOTS_FR = charger_mots_fr()

WORD_LENGTH = 5
MAX_ATTEMPTS = 6

async def get_random_word():
    # Choisit un mot français de 5 lettres depuis le fichier
    return random.choice(MOTS_FR)

class WordleGame:
    def __init__(self, word):
        self.word = word
        self.attempts = []
        self.finished = False
        self.won = False

    def guess(self, guess):
        guess = guess.lower()
        if self.finished or len(guess) != WORD_LENGTH:
            return None
        result = []
        word_chars = list(self.word)
        guess_chars = list(guess)
        # First pass: correct position
        for i in range(WORD_LENGTH):
            if guess_chars[i] == word_chars[i]:
                result.append((guess_chars[i], 'green'))
                word_chars[i] = None
            else:
                result.append((guess_chars[i], None))
        # Second pass: correct letter, wrong position
        for i in range(WORD_LENGTH):
            if result[i][1] is None and guess_chars[i] in word_chars:
                result[i] = (guess_chars[i], 'yellow')
                word_chars[word_chars.index(guess_chars[i])] = None
            elif result[i][1] is None:
                result[i] = (guess_chars[i], 'grey')
        self.attempts.append(result)
        if guess == self.word:
            self.finished = True
            self.won = True
        elif len(self.attempts) >= MAX_ATTEMPTS:
            self.finished = True
        return result

    def render(self):
        color_map = {'green': '🟩', 'yellow': '🟨', 'grey': '⬜'}
        lines = []
        for idx, attempt in enumerate(self.attempts, 1):
            mot = ''.join(l.upper() for l, _ in attempt)
            schema = ''.join(color_map[c] for _, c in attempt)
            # Utilise un bloc de code pour aligner
            lines.append(f"{idx}. `{mot}`\n   {schema}")
        for i in range(len(self.attempts)+1, MAX_ATTEMPTS+1):
            lines.append(f"{i}. `-----`\n   {'⬜'*WORD_LENGTH}")
        return '\n'.join(lines)

class WordleView(discord.ui.View):
    def __init__(self, game, interaction):
        super().__init__(timeout=300)
        self.game = game
        self.interaction = interaction
        # Ajout des boutons après la définition des classes
        # Les boutons seront ajoutés dans Wordle.__init__ après la définition des classes


    async def update_message(self, interaction=None):
        embed = self.make_embed()
        if interaction:
            await interaction.response.edit_message(embed=embed, view=(None if self.game.finished else self))
        else:
            await self.interaction.edit_original_response(embed=embed, view=(None if self.game.finished else self))

    def make_embed(self):
        embed = discord.Embed(title="Wordle", color=discord.Color.green())
        embed.description = self.game.render()
        if self.game.finished:
            if self.game.won:
                embed.add_field(name="Résultat", value="Bravo ! Tu as trouvé le mot !", inline=False)
            else:
                embed.add_field(name="Résultat", value=f"Perdu ! Le mot était : **{self.game.word.upper()}**", inline=False)
        else:
            embed.add_field(name="Essais", value=f"{len(self.game.attempts)}/{MAX_ATTEMPTS}", inline=False)
        embed.set_footer(text="Wordle Discord")
        return embed

class WordleGuessModalButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Proposer un mot", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        if self.view.game.finished:
            await interaction.response.send_message("La partie est terminée.", ephemeral=True)
            return
        await interaction.response.send_modal(WordleGuessModal(self.view))

class WordleGuessModal(discord.ui.Modal, title="Proposer un mot"):
    guess = discord.ui.TextInput(label="Mot de 5 lettres", min_length=5, max_length=5)
    def __init__(self, view):
        super().__init__()
        self._view = view
    async def on_submit(self, interaction: discord.Interaction):
        result = self._view.game.guess(self.guess.value)
        await self._view.update_message(interaction)

class WordleForfeitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Abandonner", style=discord.ButtonStyle.danger)
    async def callback(self, interaction: discord.Interaction):
        if self.view.game.finished:
            await interaction.response.send_message("La partie est déjà terminée.", ephemeral=True)
            return
        self.view.game.finished = True
        await self.view.update_message(interaction)

class Wordle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wordle", description="Jouer à Wordle (mot de 5 lettres)")
    async def wordle(self, interaction: discord.Interaction):
        word = await get_random_word()
        game = WordleGame(word)
        view = WordleView(game, interaction)
        view.add_item(WordleGuessModalButton())
        view.add_item(WordleForfeitButton())
        await interaction.response.send_message(embed=view.make_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Wordle(bot))
