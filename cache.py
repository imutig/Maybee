import asyncio
import time
import json
import os
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PersistentCache:
    """Cache with optional persistent storage support"""
    
    def __init__(self, default_ttl: int = 300, persist_file: Optional[str] = None):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl
        self.persist_file = persist_file
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # Load from persistent storage if available
        if self.persist_file and os.path.exists(self.persist_file):
            self._load_from_file()
        
    def _load_from_file(self) -> None:
        """Load cache from persistent file"""
        try:
            with open(self.persist_file, 'r') as f:
                data = json.load(f)
                current_time = time.time()
                
                # Only load non-expired entries
                for key, (value, expiry) in data.items():
                    if current_time < expiry:
                        self.cache[key] = (value, expiry)
                        
            logger.info(f"Loaded {len(self.cache)} cache entries from {self.persist_file}")
        except Exception as e:
            logger.error(f"Error loading cache from file: {e}")
            
    def _save_to_file(self) -> None:
        """Save cache to persistent file"""
        if not self.persist_file:
            return
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.persist_file), exist_ok=True)
            
            with open(self.persist_file, 'w') as f:
                json.dump(self.cache, f)
                
        except Exception as e:
            logger.error(f"Error saving cache to file: {e}")
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                self.stats['hits'] += 1
                return value
            else:
                # Expired
                del self.cache[key]
                if self.persist_file:
                    self._save_to_file()
                
        self.stats['misses'] += 1
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None, persist: bool = True) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = self.default_ttl
            
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
        self.stats['sets'] += 1
        
        # Save to file if persistence is enabled
        if persist and self.persist_file:
            self._save_to_file()
        
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
            self.stats['deletes'] += 1
            if self.persist_file:
                self._save_to_file()
            return True
        return False
        
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        if self.persist_file:
            self._save_to_file()
        
    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if current_time >= expiry
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys and self.persist_file:
            self._save_to_file()
            
        return len(expired_keys)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'hit_rate': round(hit_rate, 2)
        }

# Backward compatibility alias
Cache = PersistentCache

class UserPreferencesCache:
    """Cache for user language preferences"""
    
    def __init__(self, bot_db, cache_ttl: int = 600):  # 10 minutes
        self.db = bot_db
        self.cache = Cache(cache_ttl)
        
    async def get_user_language(self, user_id: int, guild_id: int) -> str:
        """Get user's language preference with caching"""
        cache_key = f"user_lang_{user_id}_{guild_id}"
        
        # Try cache first
        cached_lang = self.cache.get(cache_key)
        if cached_lang:
            return cached_lang
            
        # Query database
        try:
            result = await self.db.query(
                "SELECT language FROM user_preferences WHERE user_id = %s AND guild_id = %s",
                (user_id, guild_id)
            )
            
            if result:
                language = result[0]['language']
            else:
                # Fall back to guild default
                guild_result = await self.db.query(
                    "SELECT language FROM guild_preferences WHERE guild_id = %s",
                    (guild_id,)
                )
                language = guild_result[0]['language'] if guild_result else 'en'
                
            # Cache the result
            self.cache.set(cache_key, language)
            return language
            
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return 'en'  # Default fallback
            
    async def set_user_language(self, user_id: int, guild_id: int, language: str) -> None:
        """Set user's language preference and update cache"""
        cache_key = f"user_lang_{user_id}_{guild_id}"
        
        try:
            # Update database
            await self.db.execute(
                """INSERT INTO user_preferences (user_id, guild_id, language) 
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE language = %s""",
                (user_id, guild_id, language, language)
            )
            
            # Update cache
            self.cache.set(cache_key, language)
            
        except Exception as e:
            logger.error(f"Error setting user language: {e}")
            
    def invalidate_user(self, user_id: int, guild_id: int) -> None:
        """Invalidate user's cached preferences"""
        cache_key = f"user_lang_{user_id}_{guild_id}"
        self.cache.delete(cache_key)

class ConfigurationCache:
    """Cache for bot configurations"""
    
    def __init__(self, bot_db, cache_ttl: int = 300):  # 5 minutes
        self.db = bot_db
        self.cache = Cache(cache_ttl)
        
    async def get_config(self, guild_id: int, config_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration with caching"""
        cache_key = f"config_{guild_id}_{config_type}"
        
        # Try cache first
        cached_config = self.cache.get(cache_key)
        if cached_config:
            return cached_config
            
        # Query database based on config type
        try:
            table_map = {
                'welcome': 'welcome_config',
                'confession': 'confession_config',
                'role_requests': 'role_requests_config',
                'xp': 'xp_config',
                'ticket': 'ticket_config'
            }
            
            if config_type not in table_map:
                return None
                
            result = await self.db.query(
                f"SELECT * FROM {table_map[config_type]} WHERE guild_id = %s",
                (guild_id,)
            )
            
            config = result[0] if result else None
            
            # Cache the result
            self.cache.set(cache_key, config)
            return config
            
        except Exception as e:
            logger.error(f"Error getting config {config_type}: {e}")
            return None
            
    async def set_config(self, guild_id: int, config_type: str, config_data: Dict[str, Any]) -> None:
        """Set configuration and update cache"""
        cache_key = f"config_{guild_id}_{config_type}"
        
        # Update cache
        self.cache.set(cache_key, config_data)
        
    def invalidate_config(self, guild_id: int, config_type: str) -> None:
        """Invalidate configuration cache"""
        cache_key = f"config_{guild_id}_{config_type}"
        self.cache.delete(cache_key)

class BotCache:
    """Main cache manager for the bot with persistent storage for important data"""
    
    def __init__(self, bot_db):
        self.db = bot_db
        
        # Create cache directory with error handling
        cache_dir = "cache_data"
        try:
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"Cache directory created/verified: {cache_dir}")
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
            cache_dir = None  # Disable persistence if directory creation fails
        
        # Initialize caches with different persistence settings
        self.user_prefs = UserPreferencesCache(bot_db)
        self.config = ConfigurationCache(bot_db)
        
        # Persistent cache for leaderboards and important data (longer TTL)
        if cache_dir:
            self.leaderboards = PersistentCache(
                default_ttl=1800,  # 30 minutes
                persist_file=os.path.join(cache_dir, "leaderboards.json")
            )
        else:
            # Fallback to memory-only cache if persistence fails
            self.leaderboards = PersistentCache(default_ttl=1800)
            logger.warning("Leaderboard cache will be memory-only (persistence disabled)")
        
        # General purpose cache (shorter TTL, in-memory only)
        self.general = PersistentCache(300)  # 5 minutes, no persistence
        
        # Start cleanup task
        self.cleanup_task = None
        
    async def start_cleanup_task(self):
        """Start the cleanup task"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def stop_cleanup_task(self):
        """Stop the cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            
    async def _cleanup_loop(self):
        """Background task to cleanup expired cache entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Cleanup all caches
                expired_user_prefs = self.user_prefs.cache.cleanup_expired()
                expired_config = self.config.cache.cleanup_expired()
                expired_leaderboards = self.leaderboards.cleanup_expired()
                expired_general = self.general.cleanup_expired()
                
                total_expired = expired_user_prefs + expired_config + expired_leaderboards + expired_general
                if total_expired > 0:
                    logger.info(f"Cache cleanup: {total_expired} expired entries removed")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)
                
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            'user_preferences': self.user_prefs.cache.get_stats(),
            'configuration': self.config.cache.get_stats(),
            'leaderboards': self.leaderboards.get_stats(),
            'general': self.general.get_stats()
        }
        
    def clear_all(self) -> None:
        """Clear all caches"""
        self.user_prefs.cache.clear()
        self.config.cache.clear()
        self.leaderboards.clear()
        self.general.clear()
        logger.info("All caches cleared")
