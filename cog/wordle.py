import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp

WORD_LENGTH = 5
MAX_ATTEMPTS = 6

async def get_random_word():
    # Utilise l'API https://random-word-api.herokuapp.com/word?length=5
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://random-word-api.herokuapp.com/word?length={WORD_LENGTH}") as resp:
            data = await resp.json()
            return data[0].lower()

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
        # Emoji rendering
        color_map = {'green': '🟩', 'yellow': '🟨', 'grey': '⬜'}
        lines = []
        for attempt in self.attempts:
            line = ''
            for letter, color in attempt:
                if color:
                    line += color_map[color] + letter.upper()
                else:
                    line += '⬜' + letter.upper()
            lines.append(line)
        for _ in range(MAX_ATTEMPTS - len(self.attempts)):
            lines.append('⬜' * WORD_LENGTH * 2)
        return '\n'.join(lines)

class WordleView(discord.ui.View):
    def __init__(self, game, interaction):
        super().__init__(timeout=300)
        self.game = game
        self.interaction = interaction
        self.add_item(WordleGuessModalButton(self))
        self.add_item(WordleForfeitButton(self))

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
    def __init__(self, view):
        super().__init__(label="Proposer un mot", style=discord.ButtonStyle.primary)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        if self.view.game.finished:
            await interaction.response.send_message("La partie est terminée.", ephemeral=True)
            return
        await interaction.response.send_modal(WordleGuessModal(self.view))

class WordleGuessModal(discord.ui.Modal, title="Proposer un mot"):
    guess = discord.ui.TextInput(label="Mot de 5 lettres", min_length=5, max_length=5)
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        result = self.view.game.guess(self.guess.value)
        await self.view.update_message(interaction)

class WordleForfeitButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="Abandonner", style=discord.ButtonStyle.danger)
        self.view = view
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
        await interaction.response.send_message(embed=view.make_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Wordle(bot))
