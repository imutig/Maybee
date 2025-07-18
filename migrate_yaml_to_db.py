#!/usr/bin/env python3
"""
Migration script to convert YAML data to MySQL database
Run this script after setting up the database to migrate existing data

Enhanced with:
- Comprehensive error handling
- Connection pooling and retry logic
- Data validation and sanitization
- Transaction safety with rollback
- Progress tracking
- Backup creation before migration
"""

import os
import yaml
import asyncio
import aiomysql
import logging
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Enhanced database configuration with validation
@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create config from environment variables with validation"""
        required_vars = ['DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return cls(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            database=os.getenv('DB_NAME')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'db': self.database,
            'autocommit': False,  # Use transactions
            'maxsize': 5,
            'minsize': 1
        }

class MigrationError(Exception):
    """Custom exception for migration-specific errors"""
    pass

class DatabaseManager:
    """Enhanced database manager with connection pooling and retry logic"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self.max_retries = 3
        self.retry_delay = 2
    
    async def connect(self):
        """Create connection pool with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting database connection (attempt {attempt + 1}/{self.max_retries})")
                self.pool = await aiomysql.create_pool(**self.config.to_dict())
                logger.info("✅ Database connection pool created successfully")
                return
            except Exception as e:
                logger.error(f"❌ Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise MigrationError(f"Failed to connect to database after {self.max_retries} attempts: {e}")
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("🔌 Database connection pool closed")
    
    async def execute_transaction(self, operations: List[tuple]) -> int:
        """Execute multiple operations in a single transaction"""
        if not self.pool:
            raise MigrationError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await conn.begin()
                    affected_rows = 0
                    
                    for query, params in operations:
                        await cursor.execute(query, params)
                        affected_rows += cursor.rowcount
                    
                    await conn.commit()
                    logger.debug(f"Transaction completed successfully, {affected_rows} rows affected")
                    return affected_rows
                
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Transaction failed, rolled back: {e}")
                    raise MigrationError(f"Database transaction failed: {e}")
    
    async def test_connection(self) -> bool:
        """Test database connection and verify tables exist"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Test basic connectivity
                    await cursor.execute("SELECT 1")
                    
                    # Check if required tables exist
                    required_tables = ['welcome_config', 'confessions', 'role_requests']
                    for table in required_tables:
                        await cursor.execute(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                            (self.config.database, table)
                        )
                        result = await cursor.fetchone()
                        if result[0] == 0:
                            raise MigrationError(f"Required table '{table}' does not exist in database")
                    
                    logger.info("✅ Database connection and schema validation successful")
                    return True
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            return False

class DataValidator:
    """Validate and sanitize migration data"""
    
    @staticmethod
    def validate_guild_id(guild_id: Any) -> int:
        """Validate and convert guild ID"""
        try:
            guild_id = int(guild_id)
            if guild_id < 0 or len(str(guild_id)) < 17:  # Discord snowflake validation
                raise ValueError("Invalid guild ID format")
            return guild_id
        except (ValueError, TypeError) as e:
            raise MigrationError(f"Invalid guild ID: {guild_id} - {e}")
    
    @staticmethod
    def validate_channel_id(channel_id: Any) -> Optional[int]:
        """Validate and convert channel ID"""
        if channel_id is None:
            return None
        try:
            channel_id = int(channel_id)
            if channel_id < 0 or len(str(channel_id)) < 17:
                raise ValueError("Invalid channel ID format")
            return channel_id
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid channel ID: {channel_id} - {e}")
            return None
    
    @staticmethod
    def sanitize_message(message: str, max_length: int = 2000) -> str:
        """Sanitize message content"""
        if not isinstance(message, str):
            return ""
        
        # Remove potential harmful characters and limit length
        sanitized = message.replace('\x00', '').strip()
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length - 3] + "..."
        return sanitized

class BackupManager:
    """Create backups before migration"""
    
    @staticmethod
    def create_backup(file_path: str) -> Optional[str]:
        """Create a backup of the source file"""
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"📋 Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {file_path}: {e}")
            return None

class ProgressTracker:
    """Track migration progress"""
    
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed_items = 0
        self.errors = 0
        self.start_time = datetime.now()
    
    def update(self, success: bool = True):
        """Update progress"""
        self.processed_items += 1
        if not success:
            self.errors += 1
        
        if self.processed_items % 10 == 0 or self.processed_items == self.total_items:
            self.print_progress()
    
    def print_progress(self):
        """Print current progress"""
        percentage = (self.processed_items / self.total_items) * 100
        elapsed = datetime.now() - self.start_time
        
        logger.info(f"📊 Progress: {self.processed_items}/{self.total_items} ({percentage:.1f}%) "
                   f"- Errors: {self.errors} - Elapsed: {elapsed}")

async def migrate_welcome_data(db_manager: DatabaseManager) -> bool:
    """Migrate welcome.yaml data to database with enhanced error handling"""
    welcome_file = "config/welcome.yaml"
    if not os.path.exists(welcome_file):
        logger.warning("❌ Fichier welcome.yaml introuvable")
        return False
    
    # Create backup
    backup_path = BackupManager.create_backup(welcome_file)
    if backup_path:
        logger.info(f"📋 Backup created at: {backup_path}")
    
    try:
        with open(welcome_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        if not data:
            logger.info("ℹ️ Aucune donnée de bienvenue à migrer")
            return True
        
        # Validate and prepare operations
        operations = []
        progress = ProgressTracker(len(data))
        validator = DataValidator()
        
        for guild_id_str, config in data.items():
            try:
                guild_id = validator.validate_guild_id(guild_id_str)
                welcome_channel = validator.validate_channel_id(config.get('welcome_channel'))
                welcome_message = validator.sanitize_message(config.get('welcome_message', ''))
                goodbye_channel = validator.validate_channel_id(config.get('goodbye_channel'))
                goodbye_message = validator.sanitize_message(config.get('goodbye_message', ''))
                
                operations.append((
                    """INSERT INTO welcome_config (guild_id, welcome_channel, welcome_message, goodbye_channel, goodbye_message)
                       VALUES (%s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                       welcome_channel = VALUES(welcome_channel),
                       welcome_message = VALUES(welcome_message),
                       goodbye_channel = VALUES(goodbye_channel),
                       goodbye_message = VALUES(goodbye_message)""",
                    (guild_id, welcome_channel, welcome_message, goodbye_channel, goodbye_message)
                ))
                
                progress.update(True)
                
            except MigrationError as e:
                logger.error(f"❌ Error processing guild {guild_id_str}: {e}")
                progress.update(False)
                continue
        
        if operations:
            affected_rows = await db_manager.execute_transaction(operations)
            logger.info(f"✅ Migré {len(operations)} configurations de bienvenue ({affected_rows} rows affected)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration des données de bienvenue: {e}")
        return False

async def migrate_confession_data(db_manager: DatabaseManager) -> bool:
    """Migrate confessions.yaml data to database with enhanced error handling"""
    confession_file = "data/confessions.yaml"
    if not os.path.exists(confession_file):
        logger.warning("❌ Fichier confessions.yaml introuvable")
        return False
    
    # Create backup
    backup_path = BackupManager.create_backup(confession_file)
    
    try:
        with open(confession_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or []
        
        if not data:
            logger.info("ℹ️ Aucune confession à migrer")
            return True
        
        # Validate and prepare operations
        operations = []
        progress = ProgressTracker(len(data))
        validator = DataValidator()
        
        # Note: We don't have guild_id in the old format, using 0 as default
        # You should manually update with correct guild_id after migration
        default_guild_id = 0
        
        for confession in data:
            try:
                if not isinstance(confession, dict):
                    logger.warning(f"Invalid confession format: {confession}")
                    progress.update(False)
                    continue
                
                username = validator.sanitize_message(confession.get('user', 'Anonymous'), 255)
                message = validator.sanitize_message(confession.get('confession', ''), 2000)
                
                if not message:  # Skip empty confessions
                    progress.update(False)
                    continue
                
                # Extract user ID from username if possible (format: username#discriminator)
                user_id = 0  # Default unknown user
                
                operations.append((
                    """INSERT INTO confessions (user_id, username, confession, guild_id)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, username, message, default_guild_id)
                ))
                
                progress.update(True)
                
            except Exception as e:
                logger.error(f"❌ Error processing confession: {e}")
                progress.update(False)
                continue
        
        if operations:
            affected_rows = await db_manager.execute_transaction(operations)
            logger.info(f"✅ Migré {len(operations)} confessions ({affected_rows} rows affected)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration des confessions: {e}")
        return False

async def migrate_role_requests(db_manager: DatabaseManager) -> bool:
    """Migrate role_requests.yaml data to database with enhanced error handling"""
    role_file = "data/role_requests.yaml"
    if not os.path.exists(role_file):
        logger.warning("❌ Fichier role_requests.yaml introuvable")
        return False
    
    # Create backup
    backup_path = BackupManager.create_backup(role_file)
    
    try:
        with open(role_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        if not data:
            logger.info("ℹ️ Aucune demande de rôle à migrer")
            return True
        
        # Validate and prepare operations
        operations = []
        progress = ProgressTracker(len(data))
        validator = DataValidator()
        
        # Note: We don't have guild_id in the old format, using 0 as default
        default_guild_id = 0
        
        for message_id_str, request in data.items():
            try:
                if not isinstance(request, dict):
                    logger.warning(f"Invalid request format for message {message_id_str}: {request}")
                    progress.update(False)
                    continue
                
                message_id = validator.validate_guild_id(message_id_str)  # Same validation as guild_id
                user_id = validator.validate_guild_id(request.get('user_id', 0))
                role_id = validator.validate_guild_id(request.get('role_id', 0))
                action = request.get('action', 'add')
                
                # Validate action
                if action not in ['add', 'remove']:
                    logger.warning(f"Invalid action '{action}' for message {message_id_str}")
                    action = 'add'
                
                operations.append((
                    """INSERT INTO role_requests (message_id, user_id, role_id, action, guild_id, status)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                       user_id = VALUES(user_id),
                       role_id = VALUES(role_id),
                       action = VALUES(action)""",
                    (message_id, user_id, role_id, action, default_guild_id, 'pending')
                ))
                
                progress.update(True)
                
            except Exception as e:
                logger.error(f"❌ Error processing role request {message_id_str}: {e}")
                progress.update(False)
                continue
        
        if operations:
            affected_rows = await db_manager.execute_transaction(operations)
            logger.info(f"✅ Migré {len(operations)} demandes de rôles ({affected_rows} rows affected)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration des demandes de rôles: {e}")
        return False

async def main():
    """Enhanced main migration function with comprehensive error handling"""
    logger.info("🔄 Début de la migration des données YAML vers MySQL...")
    
    try:
        # Initialize database configuration
        db_config = DatabaseConfig.from_env()
        logger.info(f"📊 Database configuration loaded: {db_config.host}:{db_config.port}/{db_config.database}")
        
        # Initialize database manager
        db_manager = DatabaseManager(db_config)
        await db_manager.connect()
        
        # Test database connection and schema
        if not await db_manager.test_connection():
            raise MigrationError("Database connection test failed")
        
        # Run migrations with progress tracking
        migration_results = []
        
        logger.info("📋 Starting welcome data migration...")
        migration_results.append(("Welcome Data", await migrate_welcome_data(db_manager)))
        
        logger.info("📋 Starting confession data migration...")
        migration_results.append(("Confession Data", await migrate_confession_data(db_manager)))
        
        logger.info("📋 Starting role requests migration...")
        migration_results.append(("Role Requests", await migrate_role_requests(db_manager)))
        
        # Summary report
        logger.info("\n" + "="*50)
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("="*50)
        
        success_count = 0
        for name, success in migration_results:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"{name}: {status}")
            if success:
                success_count += 1
        
        logger.info(f"\nMigrations completed: {success_count}/{len(migration_results)}")
        
        if success_count == len(migration_results):
            logger.info("🎉 All migrations completed successfully!")
            logger.info("\nℹ️ Next steps:")
            logger.info("1. Verify migrated data in your database")
            logger.info("2. Update any hardcoded guild_id values (currently set to 0)")
            logger.info("3. Test your bot with the new database")
            logger.info("4. Archive or delete the YAML files after verification:")
            logger.info("   - config/welcome.yaml")
            logger.info("   - data/confessions.yaml")
            logger.info("   - data/role_requests.yaml")
        else:
            logger.error("⚠️ Some migrations failed. Check the logs above for details.")
        
        # Close database connection
        await db_manager.close()
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except MigrationError as e:
        logger.error(f"❌ Migration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error during migration: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
