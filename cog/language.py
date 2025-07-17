import discord
from discord.ext import commands
from discord import app_commands
from i18n import i18n, _

class LanguageManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.i18n = i18n
        
    async def load_language_preferences(self):
        """Load language preferences from database"""
        await self.i18n.load_language_preferences(self.db)
    
    async def save_user_language(self, user_id: int, language_code: str):
        """Save user language preference to database"""
        return await self.i18n.set_user_language_db(user_id, language_code, self.db)
    
    async def save_guild_language(self, guild_id: int, language_code: str):
        """Save guild language preference to database"""
        return await self.i18n.set_guild_language_db(guild_id, language_code, self.db)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Load language preferences when bot starts"""
        await self.load_language_preferences()
    
    @app_commands.command(name="language", description="Change your language preference")
    @app_commands.describe(
        language="The language you want to use",
        server="Set language for the entire server (admin only)"
    )
    @app_commands.choices(language=[
        app_commands.Choice(name="English 🇺🇸", value="en"),
        app_commands.Choice(name="Français 🇫🇷", value="fr")
    ])
    async def set_language(self, interaction: discord.Interaction, language: str, server: bool = False):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Check if language is available
        if language not in self.i18n.languages:
            available = ", ".join(self.i18n.get_available_languages().keys())
            await interaction.response.send_message(
                _("language_system.command.invalid_language", user_id, guild_id, languages=available),
                ephemeral=True
            )
            return
        
        if server:
            # Check admin permissions for server-wide change
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    _("language_system.command.no_permission", user_id, guild_id),
                    ephemeral=True
                )
                return
            
            # Set guild language
            success = await self.save_guild_language(guild_id, language)
            if success:
                lang_name = self.i18n.languages[language]['_meta']['name']
                await interaction.response.send_message(
                    _("language_system.command.guild_success", user_id, guild_id, language=lang_name),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    _("errors.database_error", user_id, guild_id),
                    ephemeral=True
                )
        else:
            # Set user language
            success = await self.save_user_language(user_id, language)
            if success:
                lang_name = self.i18n.languages[language]['_meta']['name']
                await interaction.response.send_message(
                    _("language_system.command.user_success", user_id, guild_id, language=lang_name),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    _("errors.database_error", user_id, guild_id),
                    ephemeral=True
                )
    
    @app_commands.command(name="languages", description="Show available languages")
    async def show_languages(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Get current languages
        user_lang = self.i18n.get_user_language(user_id, guild_id)
        guild_lang = self.i18n.get_user_language(None, guild_id)
        
        # Create embed
        embed = discord.Embed(
            title=_("language_system.available.title", user_id, guild_id),
            color=discord.Color.blue()
        )
        
        # Add current language info
        user_lang_name = self.i18n.languages.get(user_lang, {}).get('_meta', {}).get('name', user_lang)
        guild_lang_name = self.i18n.languages.get(guild_lang, {}).get('_meta', {}).get('name', guild_lang)
        
        embed.add_field(
            name=_("language_system.available.current_user", user_id, guild_id, language=user_lang_name),
            value="",
            inline=False
        )
        
        if guild_id:
            embed.add_field(
                name=_("language_system.available.current_guild", user_id, guild_id, language=guild_lang_name),
                value="",
                inline=False
            )
        
        # Add available languages
        available_langs = []
        for lang_code, lang_data in self.i18n.languages.items():
            if lang_code != '_meta':
                name = lang_data.get('_meta', {}).get('name', lang_code)
                flag = lang_data.get('_meta', {}).get('flag', '🌍')
                available_langs.append(f"{flag} {name} (`{lang_code}`)")
        
        embed.add_field(
            name="Available Languages",
            value="\n".join(available_langs),
            inline=False
        )
        
        embed.add_field(
            name=_("language_system.available.change_hint", user_id, guild_id),
            value="",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LanguageManager(bot))
