#!/usr/bin/env python3
"""
Internationalization (i18n) system for Maybee
Supports multiple languages with fallback to English
"""

import json
import os
from typing import Dict, Any, Optional
import discord

class I18n:
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self.languages: Dict[str, Dict[str, Any]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> language code
        self.guild_languages: Dict[int, str] = {}  # guild_id -> language code
        self.load_languages()
    
    def load_languages(self):
        """Load all language files from the languages directory"""
        languages_dir = "languages"
        if not os.path.exists(languages_dir):
            os.makedirs(languages_dir)
            return
        
        for filename in os.listdir(languages_dir):
            if filename.endswith('.json'):
                language_code = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(languages_dir, filename), 'r', encoding='utf-8') as f:
                        self.languages[language_code] = json.load(f)
                    print(f"✅ Langue chargée: {language_code}")
                except Exception as e:
                    print(f"❌ Erreur lors du chargement de {filename}: {e}")
    
    def get_user_language(self, user_id: int, guild_id: int = None) -> str:
        """Get user's preferred language, fallback to guild language, then default"""
        # Check user preference first
        if user_id in self.user_languages:
            return self.user_languages[user_id]
        
        # Check guild preference
        if guild_id and guild_id in self.guild_languages:
            return self.guild_languages[guild_id]
        
        # Return default language
        return self.default_language
    
    def set_user_language(self, user_id: int, language: str):
        """Set user's preferred language"""
        if language in self.languages:
            self.user_languages[user_id] = language
            return True
        return False
    
    async def set_user_language_db(self, user_id: int, language: str, db):
        """Set user's preferred language and save to database"""
        if language in self.languages:
            self.user_languages[user_id] = language
            try:
                await db.execute(
                    "INSERT INTO user_languages (user_id, language_code) VALUES (%s, %s) ON DUPLICATE KEY UPDATE language_code = %s",
                    (user_id, language, language)
                )
                return True
            except Exception as e:
                print(f"❌ Error saving user language preference: {e}")
                return False
        return False
    
    def set_guild_language(self, guild_id: int, language: str):
        """Set guild's default language"""
        if language in self.languages:
            self.guild_languages[guild_id] = language
            return True
        return False
    
    async def set_guild_language_db(self, guild_id: int, language: str, db):
        """Set guild's default language and save to database"""
        if language in self.languages:
            self.guild_languages[guild_id] = language
            try:
                await db.execute(
                    "INSERT INTO guild_languages (guild_id, language_code) VALUES (%s, %s) ON DUPLICATE KEY UPDATE language_code = %s",
                    (guild_id, language, language)
                )
                return True
            except Exception as e:
                print(f"❌ Error saving guild language preference: {e}")
                return False
        return False
    
    async def load_language_preferences(self, db):
        """Load user and guild language preferences from database"""
        try:
            # Load user language preferences
            user_results = await db.fetch_all("SELECT user_id, language_code FROM user_languages")
            if user_results:
                for row in user_results:
                    # Handle both dict and tuple formats
                    if isinstance(row, dict):
                        self.user_languages[row["user_id"]] = row["language_code"]
                    else:
                        self.user_languages[row[0]] = row[1]
                print(f"✅ Loaded {len(user_results)} user language preferences")
            
            # Load guild language preferences
            guild_results = await db.fetch_all("SELECT guild_id, language_code FROM guild_languages")
            if guild_results:
                for row in guild_results:
                    # Handle both dict and tuple formats
                    if isinstance(row, dict):
                        self.guild_languages[row["guild_id"]] = row["language_code"]
                    else:
                        self.guild_languages[row[0]] = row[1]
                print(f"✅ Loaded {len(guild_results)} guild language preferences")
                
        except Exception as e:
            print(f"❌ Error loading language preferences from database: {e}")
            # Don't raise the exception, just log it and continue
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get list of available languages with their names"""
        available = {}
        for lang_code, lang_data in self.languages.items():
            available[lang_code] = lang_data.get('_meta', {}).get('name', lang_code)
        return available
    
    def t(self, key: str, user_id: int = None, guild_id: int = None, **kwargs) -> str:
        """
        Translate a key to the user's preferred language
        
        Args:
            key: Translation key (e.g., 'commands.ping.response')
            user_id: User ID for language preference
            guild_id: Guild ID for language preference
            **kwargs: Variables to format into the translation
        
        Returns:
            Translated string
        """
        # Get user's language
        lang = self.get_user_language(user_id, guild_id)
        
        # Get translation
        translation = self._get_translation(key, lang)
        
        # Format with variables if provided
        if kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError):
                # If formatting fails, return the translation as-is
                return translation
        
        return translation
    
    def _get_translation(self, key: str, language: str) -> str:
        """Get translation for a specific key and language"""
        # Try to get from preferred language
        if language in self.languages:
            translation = self._get_nested_value(self.languages[language], key)
            if translation:
                return translation
        
        # Fallback to default language
        if self.default_language in self.languages:
            translation = self._get_nested_value(self.languages[self.default_language], key)
            if translation:
                return translation
        
        # If all else fails, return the key itself
        return key
    
    def _get_nested_value(self, data: Dict, key: str) -> Optional[str]:
        """Get value from nested dictionary using dot notation"""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_discord_locale_mapping(self) -> Dict[discord.Locale, str]:
        """Get mapping of Discord locales to our language codes"""
        return {
            discord.Locale.american_english: "en",
            discord.Locale.british_english: "en",
            discord.Locale.french: "fr",
            discord.Locale.german: "de",
            discord.Locale.spanish: "es",
            discord.Locale.italian: "it",
            discord.Locale.portuguese_brazil: "pt",
            discord.Locale.russian: "ru",
            discord.Locale.japanese: "ja",
            discord.Locale.korean: "ko",
            discord.Locale.chinese: "zh"
        }
    
    def get_language_from_interaction(self, interaction: discord.Interaction) -> str:
        """Get language from Discord interaction locale"""
        locale_mapping = self.get_discord_locale_mapping()
        discord_locale = interaction.locale
        
        # Try to map Discord locale to our language
        if discord_locale in locale_mapping:
            lang_code = locale_mapping[discord_locale]
            if lang_code in self.languages:
                return lang_code
        
        # Fallback to user/guild preference
        return self.get_user_language(interaction.user.id, interaction.guild.id if interaction.guild else None)

# Global instance
i18n = I18n()

# Convenience function for easy access
def _(key: str, user_id: int = None, guild_id: int = None, **kwargs) -> str:
    """Shorthand for i18n.t()"""
    return i18n.t(key, user_id, guild_id, **kwargs)
