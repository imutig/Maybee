import discord
from discord.ext import commands
from discord import app_commands
import random


class Roll(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll",
                          description="Lance un dé entre 1 et 100")
    async def roll(self, interaction: discord.Interaction):
        result = random.randint(1, 100)
        await interaction.response.send_message(
            f"🎲 {interaction.user.mention} a lancé un dé et obtenu : **{result}**"
        )


async def setup(bot):
    await bot.add_cog(Roll(bot))
