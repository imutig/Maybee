import asyncio
import aiomysql
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, host, port, user, password, db):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.pool = None
        self.max_retries = 3
        self.retry_delay = 1

    async def connect(self):
        """Create connection pool with retry logic"""
        print("[DB] Connexion à la base de données...")
        
        for attempt in range(self.max_retries):
            try:
                self.pool = await aiomysql.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    db=self.db,
                    autocommit=True,
                    maxsize=10,
                    minsize=1
                )
                print("[DB] Connexion réussie.")
                return
            except Exception as e:
                print(f"[DB][ERREUR] Connexion échouée (tentative {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise

    async def close(self):
        if self.pool:
            print("[DB] Fermeture du pool de connexions...")
            self.pool.close()
            await self.pool.wait_closed()
            print("[DB] Pool fermé.")
            
    async def query(self, query, params=None, fetchone=False, fetchall=False):
        """Execute query with improved error handling and connection management"""
        if not self.pool:
            await self.connect()
        
        print(f"[DB] Query : {query} | params : {params}")
        
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        await cur.execute(query, params)
                        if fetchone:
                            result = await cur.fetchone()
                            print(f"[DB] fetchone : {result}")
                            return result
                        if fetchall:
                            result = await cur.fetchall()
                            print(f"[DB] fetchall : {result}")
                            return result
                        await conn.commit()
                        return None
            except aiomysql.Error as e:
                print(f"[DB][ERREUR] Query error (tentative {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"[DB][ERREUR] Unexpected error: {e}")
                raise
        
        return None


    async def execute(self, query, params=None):
        """Execute query with improved error handling"""
        if not self.pool:
            await self.connect()
        
        print(f"[DB] Exécution de la requête : {query} | params : {params}")
        
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, params)
                        if query.strip().lower().startswith("select"):
                            result = await cur.fetchall()
                            print(f"[DB] Résultat : {result}")
                            return result
                        else:
                            affected = cur.rowcount
                            print(f"[DB] Lignes affectées : {affected}")
                            return affected
            except aiomysql.Error as e:
                print(f"[DB][ERREUR] Execute error (tentative {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"[DB][ERREUR] Unexpected error: {e}")
                raise
        
        return None
    
    async def health_check(self):
        """Check database connection health"""
        try:
            await self.query("SELECT 1", fetchone=True)
            return True
        except Exception as e:
            print(f"[DB][ERREUR] Health check failed: {e}")
            return False

    async def init_tables(self):
        """Initialize database tables for bot functionality"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS welcome_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                welcome_channel BIGINT DEFAULT NULL,
                welcome_message TEXT DEFAULT NULL,
                goodbye_channel BIGINT DEFAULT NULL,
                goodbye_message TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_guild (guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS role_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id BIGINT NOT NULL UNIQUE,
                user_id BIGINT NOT NULL,
                role_id BIGINT NOT NULL,
                action ENUM('add', 'remove') NOT NULL DEFAULT 'add',
                status ENUM('pending', 'approved', 'denied') NOT NULL DEFAULT 'pending',
                guild_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_message_id (message_id),
                INDEX idx_user_id (user_id),
                INDEX idx_status (status)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS confessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username VARCHAR(255) NOT NULL,
                confession TEXT NOT NULL,
                guild_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_guild_id (guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS confession_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                channel_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS role_request_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                channel_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS xp_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                xp INT NOT NULL DEFAULT 0,
                level INT NOT NULL DEFAULT 1,
                text_xp INT NOT NULL DEFAULT 0,
                voice_xp INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_guild (user_id, guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_guild_id (guild_id),
                INDEX idx_xp (xp),
                INDEX idx_level (level)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS xp_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                xp_channel BIGINT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS level_roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                level INT NOT NULL,
                role_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_guild_level (guild_id, level),
                INDEX idx_guild_id (guild_id),
                INDEX idx_level (level)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS role_reactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                emoji VARCHAR(255) NOT NULL,
                role_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_message_emoji (guild_id, message_id, emoji),
                INDEX idx_guild_id (guild_id),
                INDEX idx_message_id (message_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_languages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                language_code VARCHAR(10) NOT NULL DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS guild_languages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                language_code VARCHAR(10) NOT NULL DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS warnings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                moderator_id BIGINT NOT NULL,
                reason TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_user (guild_id, user_id),
                INDEX idx_moderator (moderator_id),
                INDEX idx_timestamp (timestamp)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timeouts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                moderator_id BIGINT NOT NULL,
                duration INT NOT NULL,
                reason TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_user (guild_id, user_id),
                INDEX idx_moderator (moderator_id),
                INDEX idx_timestamp (timestamp)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS xp_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                xp_gained INT NOT NULL,
                xp_type ENUM('text', 'voice') NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_guild (user_id, guild_id),
                INDEX idx_timestamp (timestamp),
                INDEX idx_guild_time (guild_id, timestamp)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS xp_multipliers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                multiplier_type ENUM('text', 'voice', 'both') NOT NULL,
                multiplier_value DECIMAL(3,2) NOT NULL DEFAULT 1.00,
                duration_minutes INT DEFAULT NULL,
                expires_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_type (guild_id, multiplier_type),
                INDEX idx_expires (expires_at)
            )
            """
        ]
        
        for table_sql in tables:
            try:
                await self.query(table_sql)
                print(f"[DB] Table créée/vérifiée avec succès")
            except Exception as e:
                print(f"[DB][ERREUR] Erreur lors de la création de table : {e}")