"""
Input validation utilities for MaybeBot
Provides common validation functions for user inputs
"""

import re
import discord
from typing import Optional, Union

class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_channel_id(channel_id: str) -> Optional[int]:
        """Validate and convert channel ID string to integer"""
        try:
            # Remove any non-numeric characters
            clean_id = re.sub(r'[^\d]', '', channel_id)
            if not clean_id:
                return None
            
            channel_id_int = int(clean_id)
            
            # Discord snowflake IDs should be 17-19 digits
            if len(str(channel_id_int)) < 17 or len(str(channel_id_int)) > 19:
                return None
                
            return channel_id_int
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_role_id(role_id: str) -> Optional[int]:
        """Validate and convert role ID string to integer"""
        try:
            # Remove any non-numeric characters
            clean_id = re.sub(r'[^\d]', '', role_id)
            if not clean_id:
                return None
            
            role_id_int = int(clean_id)
            
            # Discord snowflake IDs should be 17-19 digits
            if len(str(role_id_int)) < 17 or len(str(role_id_int)) > 19:
                return None
                
            return role_id_int
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_level(level: str) -> Optional[int]:
        """Validate level input"""
        try:
            level_int = int(level)
            if level_int < 1 or level_int > 1000:  # Reasonable level limits
                return None
            return level_int
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def sanitize_message(message: str) -> str:
        """Sanitize user message input"""
        if not message:
            return ""
        
        # Remove potential markdown abuse
        message = message.replace('`', '\\`')
        message = message.replace('*', '\\*')
        message = message.replace('_', '\\_')
        message = message.replace('~', '\\~')
        
        # Limit length
        if len(message) > 2000:
            message = message[:1997] + "..."
        
        return message.strip()
    
    @staticmethod
    def validate_color(color: str) -> Optional[discord.Color]:
        """Validate color input"""
        try:
            # Hex color
            if color.startswith('#'):
                return discord.Color(int(color[1:], 16))
            
            # Named color
            if hasattr(discord.Color, color.lower()):
                return getattr(discord.Color, color.lower())()
            
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_permission_level(user: discord.Member, required_permission: str) -> bool:
        """Validate user permission level"""
        if not user or not user.guild_permissions:
            return False
        
        permission_map = {
            'administrator': user.guild_permissions.administrator,
            'manage_channels': user.guild_permissions.manage_channels,
            'manage_roles': user.guild_permissions.manage_roles,
            'manage_messages': user.guild_permissions.manage_messages,
            'manage_guild': user.guild_permissions.manage_guild,
            'kick_members': user.guild_permissions.kick_members,
            'ban_members': user.guild_permissions.ban_members,
        }
        
        return permission_map.get(required_permission, False)
    
    @staticmethod
    def validate_emoji(emoji: str) -> bool:
        """Validate emoji format"""
        # Unicode emoji pattern
        unicode_emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U0002702-\U000027B0\U000024C2-\U0001F251]+'
        )
        
        # Custom emoji pattern <:name:id>
        custom_emoji_pattern = re.compile(r'<a?:\w+:\d+>')
        
        return (unicode_emoji_pattern.match(emoji) is not None or 
                custom_emoji_pattern.match(emoji) is not None)
    
    @staticmethod
    def rate_limit_check(user_id: int, command: str, cooldown_dict: dict, cooldown_seconds: int = 5) -> bool:
        """Check if user is rate limited for a command"""
        import time
        
        key = f"{user_id}:{command}"
        current_time = time.time()
        
        if key in cooldown_dict:
            if current_time - cooldown_dict[key] < cooldown_seconds:
                return False  # User is rate limited
        
        cooldown_dict[key] = current_time
        return True  # User is not rate limited
