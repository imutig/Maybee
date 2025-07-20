"""
Service Container and Dependency Injection for Maybee
Provides centralized service management and dependency injection
"""

import logging
from typing import Dict, Any, TypeVar, Type, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found"""
    pass

class ServiceContainer:
    """Dependency injection container for managing bot services"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        logger.info("Service container initialized")
    
    def register(self, name: str, service: Any) -> None:
        """Register a service instance"""
        self._services[name] = service
        logger.debug(f"Service registered: {name}")
    
    def register_singleton(self, name: str, factory: callable) -> None:
        """Register a singleton service factory"""
        self._factories[name] = factory
        logger.debug(f"Singleton factory registered: {name}")
    
    def get(self, name: str) -> Any:
        """Get a service by name"""
        # Check for direct service instance
        if name in self._services:
            return self._services[name]
        
        # Check for singleton
        if name in self._singletons:
            return self._singletons[name]
        
        # Create singleton if factory exists
        if name in self._factories:
            instance = self._factories[name]()
            self._singletons[name] = instance
            logger.debug(f"Singleton created: {name}")
            return instance
        
        raise ServiceNotFoundError(f"Service '{name}' not found")
    
    def get_typed(self, service_type: Type[T]) -> T:
        """Get a service by type"""
        type_name = service_type.__name__.lower()
        return self.get(type_name)
    
    def has(self, name: str) -> bool:
        """Check if service exists"""
        return name in self._services or name in self._singletons or name in self._factories
    
    def list_services(self) -> Dict[str, str]:
        """List all registered services"""
        services = {}
        for name in self._services:
            services[name] = "instance"
        for name in self._singletons:
            services[name] = "singleton"
        for name in self._factories:
            services[name] = "factory"
        return services

@dataclass
class BotConfig:
    """Enhanced bot configuration with validation"""
    # Discord
    discord_token: str
    guild_id: Optional[int] = None
    
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""
    
    # Cache
    cache_ttl: int = 300
    persistent_cache: bool = True
    cache_directory: str = "cache_data"
    
    # Features
    debug_mode: bool = False
    log_level: str = "INFO"
    default_language: str = "en"
    
    # Performance
    max_db_connections: int = 10
    min_db_connections: int = 1
    command_cooldown: int = 5
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create configuration from environment variables"""
        import os
        
        # Validate required variables
        required_vars = ["DISCORD_TOKEN", "DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN"),
            guild_id=int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") else None,
            db_host=os.getenv("DB_HOST"),
            db_port=int(os.getenv("DB_PORT", 3306)),
            db_user=os.getenv("DB_USER"),
            db_password=os.getenv("DB_PASS"),
            db_name=os.getenv("DB_NAME"),
            cache_ttl=int(os.getenv("CACHE_TTL", 300)),
            persistent_cache=os.getenv("PERSISTENT_CACHE", "true").lower() == "true",
            cache_directory=os.getenv("CACHE_DIR", "cache_data"),
            debug_mode=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            default_language=os.getenv("DEFAULT_LANGUAGE", "en"),
            max_db_connections=int(os.getenv("MAX_DB_CONNECTIONS", 10)),
            min_db_connections=int(os.getenv("MIN_DB_CONNECTIONS", 1)),
            command_cooldown=int(os.getenv("COMMAND_COOLDOWN", 5))
        )

class BotException(Exception):
    """Base exception for bot-specific errors"""
    pass

class DatabaseError(BotException):
    """Database operation failed"""
    pass

class ValidationError(BotException):
    """Input validation failed"""
    pass

class PermissionError(BotException):
    """Insufficient permissions"""
    pass

class RateLimitError(BotException):
    """Rate limit exceeded"""
    pass

class ServiceError(BotException):
    """Service operation failed"""
    pass

def handle_errors(func):
    """Decorator for centralized error handling in commands"""
    import functools
    import discord
    from i18n import _
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Try to extract interaction from args
        interaction = None
        for arg in args:
            if isinstance(arg, discord.Interaction):
                interaction = arg
                break
        
        if not interaction:
            # If no interaction found, just execute the function
            return await func(*args, **kwargs)
        
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}", ephemeral=True
            ) if not interaction.response.is_done() else await interaction.followup.send(
                f"❌ {str(e)}", ephemeral=True
            )
        except PermissionError as e:
            await interaction.response.send_message(
                _("errors.no_permission", interaction.user.id, interaction.guild.id if interaction.guild else None),
                ephemeral=True
            ) if not interaction.response.is_done() else await interaction.followup.send(
                _("errors.no_permission", interaction.user.id, interaction.guild.id if interaction.guild else None),
                ephemeral=True
            )
        except RateLimitError as e:
            await interaction.response.send_message(
                f"⏱️ {str(e)}", ephemeral=True
            ) if not interaction.response.is_done() else await interaction.followup.send(
                f"⏱️ {str(e)}", ephemeral=True
            )
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            await interaction.response.send_message(
                _("errors.database_error", interaction.user.id, interaction.guild.id if interaction.guild else None),
                ephemeral=True
            ) if not interaction.response.is_done() else await interaction.followup.send(
                _("errors.database_error", interaction.user.id, interaction.guild.id if interaction.guild else None),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            await interaction.response.send_message(
                _("errors.unknown_error", interaction.user.id, interaction.guild.id if interaction.guild else None),
                ephemeral=True
            ) if not interaction.response.is_done() else await interaction.followup.send(
                _("errors.unknown_error", interaction.user.id, interaction.guild.id if interaction.guild else None),
                ephemeral=True
            )
    
    return wrapper

class RateLimitManager:
    """Rate limiting for commands and actions"""
    
    def __init__(self):
        self.cooldowns: Dict[str, float] = {}
        self.global_cooldowns: Dict[int, float] = {}
    
    def is_rate_limited(self, user_id: int, command: str, cooldown: int = 5) -> bool:
        """Check if user is rate limited for a command"""
        import time
        
        key = f"{user_id}:{command}"
        current_time = time.time()
        
        if key in self.cooldowns:
            if current_time - self.cooldowns[key] < cooldown:
                return True
        
        self.cooldowns[key] = current_time
        return False
    
    def is_globally_rate_limited(self, user_id: int, cooldown: int = 1) -> bool:
        """Check if user is globally rate limited"""
        import time
        
        current_time = time.time()
        
        if user_id in self.global_cooldowns:
            if current_time - self.global_cooldowns[user_id] < cooldown:
                return True
        
        self.global_cooldowns[user_id] = current_time
        return False
    
    def cleanup_expired(self):
        """Clean up expired cooldowns"""
        import time
        
        current_time = time.time()
        
        # Clean command cooldowns (keep last 10 minutes)
        expired_keys = [
            key for key, timestamp in self.cooldowns.items()
            if current_time - timestamp > 600
        ]
        for key in expired_keys:
            del self.cooldowns[key]
        
        # Clean global cooldowns (keep last 5 minutes)
        expired_users = [
            user_id for user_id, timestamp in self.global_cooldowns.items()
            if current_time - timestamp > 300
        ]
        for user_id in expired_users:
            del self.global_cooldowns[user_id]

class ValidationMixin:
    """Mixin class for common validation methods"""
    
    @staticmethod
    async def validate_permissions(interaction, required_perm: str) -> bool:
        """Validate user permissions"""
        if not hasattr(interaction.user, 'guild_permissions'):
            raise PermissionError("Cannot check permissions outside of guild")
        
        if not getattr(interaction.user.guild_permissions, required_perm, False):
            raise PermissionError(f"Missing permission: {required_perm}")
        
        return True
    
    @staticmethod
    def validate_user_input(text: str, max_length: int = 2000, min_length: int = 1) -> str:
        """Validate and sanitize user input"""
        if not text or len(text.strip()) < min_length:
            raise ValidationError(f"Input must be at least {min_length} characters")
        
        if len(text) > max_length:
            raise ValidationError(f"Input cannot exceed {max_length} characters")
        
        # Basic sanitization
        sanitized = text.replace('\x00', '').strip()
        return sanitized
    
    @staticmethod
    def validate_snowflake(snowflake_str: str) -> int:
        """Validate Discord snowflake ID"""
        try:
            snowflake = int(snowflake_str)
            if snowflake < 0 or len(str(snowflake)) < 17:
                raise ValidationError("Invalid Discord ID format")
            return snowflake
        except ValueError:
            raise ValidationError("ID must be a number")

def rate_limit(cooldown: int = 5, global_cooldown: int = 1):
    """Decorator for rate limiting commands"""
    def decorator(func):
        import functools
        import discord
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find interaction and rate limit manager
            interaction = None
            rate_limiter = None
            
            for arg in args:
                if isinstance(arg, discord.Interaction):
                    interaction = arg
                if hasattr(arg, 'services') and hasattr(arg.services, 'get'):
                    try:
                        rate_limiter = arg.services.get('rate_limiter')
                    except:
                        pass
            
            if interaction and rate_limiter:
                # Check global rate limit
                if rate_limiter.is_globally_rate_limited(interaction.user.id, global_cooldown):
                    raise RateLimitError("You're doing that too fast!")
                
                # Check command-specific rate limit
                if rate_limiter.is_rate_limited(interaction.user.id, func.__name__, cooldown):
                    raise RateLimitError(f"Command on cooldown. Try again in {cooldown} seconds.")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
