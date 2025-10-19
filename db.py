import asyncio
import aiomysql
import logging
import os
import glob

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, host, port, user, password, db, debug=False):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.debug = debug
        self.pool = None
        self.max_retries = 3
        self.retry_delay = 1

    async def connect(self):
        """Create connection pool with retry logic"""
        logger.debug("Connecting to database...")
        
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
                    minsize=1,
                    init_command="SET sql_mode='STRICT_TRANS_TABLES'"
                )
                logger.debug("Database connection established")
                return
            except Exception as e:
                logger.warning(f"Connection failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise

    async def close(self):
        if self.pool:
            logger.info("Closing database connection...")
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Database connection closed")
            
    async def query(self, query, params=None, fetchone=False, fetchall=False):
        """Execute query with improved error handling and connection management"""
        if not self.pool:
            await self.connect()
        
        # Create a clean, readable log message
        query_type = self._get_query_type(query)
        clean_query = self._clean_query_for_log(query)
        
        # Log with clean formatting (only for debugging)
        if query_type == "SELECT" and self.debug:
            logger.debug(f"SELECT: {clean_query}")
        elif query_type == "CREATE":
            logger.debug(f"Creating table: {clean_query}")
        
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        await cur.execute(query, params)
                        if fetchone:
                            result = await cur.fetchone()
                            if query_type in ["INSERT", "UPDATE", "DELETE"] or self.debug:
                                if result:
                                    print(f"   ✅ Result: {self._format_result(result)}")
                                else:
                                    print(f"   ℹ️  No result returned")
                            return result
                        if fetchall:
                            result = await cur.fetchall()
                            if query_type in ["INSERT", "UPDATE", "DELETE"] or self.debug:
                                if result:
                                    logger.debug(f"Found {len(result)} record(s)")
                                    if self.debug and len(result) <= 3:
                                        for i, record in enumerate(result, 1):
                                            print(f"      Record {i}: {self._format_result(record)}")
                                else:
                                    print(f"   ℹ️  No records found")
                            return result
                        await conn.commit()
                        return None
            except aiomysql.Error as e:
                print(f"❌ Database error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                raise
        
        return None

    def _get_query_type(self, query):
        """Extract the query type for cleaner logging"""
        query_clean = query.strip().upper()
        if query_clean.startswith("SELECT"):
            return "SELECT"
        elif query_clean.startswith("INSERT"):
            return "INSERT"
        elif query_clean.startswith("UPDATE"):
            return "UPDATE"
        elif query_clean.startswith("DELETE"):
            return "DELETE"
        elif query_clean.startswith("CREATE"):
            return "CREATE"
        else:
            return "QUERY"
    
    def _clean_query_for_log(self, query):
        """Clean and format query for readable logging"""
        lines = query.strip().split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--'):
                cleaned_lines.append(line)
        
        clean_query = ' '.join(cleaned_lines)
        
        # Simplify common patterns
        if "INSERT INTO" in clean_query:
            table_match = clean_query.split("INSERT INTO")[1].split("(")[0].strip()
            return f"Adding record to {table_match}"
        elif "UPDATE" in clean_query and "SET" in clean_query:
            table_match = clean_query.split("UPDATE")[1].split("SET")[0].strip()
            return f"Updating record in {table_match}"
        elif "DELETE FROM" in clean_query:
            table_match = clean_query.split("DELETE FROM")[1].split("WHERE")[0].strip()
            return f"Deleting from {table_match}"
        elif "SELECT" in clean_query and "FROM" in clean_query:
            table_match = clean_query.split("FROM")[1].split("WHERE")[0].split("ORDER")[0].split("LIMIT")[0].strip()
            return f"Querying {table_match}"
        elif "CREATE TABLE" in clean_query:
            table_match = clean_query.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
            return f"Creating table {table_match}"
        
        return clean_query[:80] + "..." if len(clean_query) > 80 else clean_query
    
    def _format_result(self, result):
        """Format result for cleaner logging"""
        if isinstance(result, dict):
            if len(result) <= 3:
                return str(result)
            else:
                return f"{{...{len(result)} fields...}}"
        return str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
    
    def _format_params(self, params):
        """Format parameters for cleaner logging"""
        if not params:
            return "None"
        
        if isinstance(params, (list, tuple)):
            formatted_params = []
            for param in params:
                if isinstance(param, str) and len(param) > 50:
                    formatted_params.append(f'"{param[:50]}..."')
                elif isinstance(param, str):
                    formatted_params.append(f'"{param}"')
                else:
                    formatted_params.append(str(param))
            return f"({', '.join(formatted_params)})"
        else:
            return str(params)[:100] + "..." if len(str(params)) > 100 else str(params)

    async def execute(self, query, params=None):
        """Execute query with improved error handling"""
        if not self.pool:
            await self.connect()
        
        # Create a clean, readable log message
        query_type = self._get_query_type(query)
        clean_query = self._clean_query_for_log(query)
        
        # Log with clean formatting (only for debugging)
        if query_type == "SELECT" and self.debug:
            logger.debug(f"SELECT: {clean_query}")
        
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, params)
                        if query.strip().lower().startswith("select"):
                            result = await cur.fetchall()
                            if self.debug and result:
                                logger.debug(f"Found {len(result)} record(s)")
                            return result
                        else:
                            affected = cur.rowcount
                            if affected > 0:
                                logger.debug(f"{affected} row(s) affected")
                            else:
                                logger.debug("No rows affected")
                            return affected
            except aiomysql.Error as e:
                print(f"❌ Database error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                raise
        
        return None
    
    async def execute_and_get_id(self, query, params=None):
        """Execute INSERT query and return the auto-increment ID"""
        if not self.pool:
            await self.connect()
        
        # Create a clean, readable log message
        query_type = self._get_query_type(query)
        clean_query = self._clean_query_for_log(query)
        
        # Log with clean formatting (only for debugging)
        if query_type == "SELECT" and self.debug:
            logger.debug(f"SELECT: {clean_query}")
        
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, params)
                        insert_id = cur.lastrowid
                        affected = cur.rowcount
                        if affected > 0:
                            logger.debug(f"{affected} row(s) affected, ID: {insert_id}")
                        else:
                            logger.debug("No rows affected")
                        return insert_id
            except aiomysql.Error as e:
                print(f"❌ Database error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
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
            CREATE TABLE IF NOT EXISTS role_menus (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                message_id BIGINT NULL,
                title VARCHAR(256) NOT NULL,
                description TEXT,
                color VARCHAR(7) DEFAULT '#5865F2',
                placeholder VARCHAR(150) DEFAULT 'Select a role...',
                max_values INT DEFAULT 1,
                min_values INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_message_id (message_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS role_menu_options (
                id INT AUTO_INCREMENT PRIMARY KEY,
                menu_id INT NOT NULL,
                role_id BIGINT NOT NULL,
                label VARCHAR(80) NOT NULL,
                description VARCHAR(100),
                emoji VARCHAR(100),
                position INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (menu_id) REFERENCES role_menus(id) ON DELETE CASCADE,
                INDEX idx_menu_id (menu_id),
                INDEX idx_role_id (role_id)
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
            """,
            """
            CREATE TABLE IF NOT EXISTS server_logs_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                log_channel_id BIGINT DEFAULT NULL,
                log_member_join BOOLEAN DEFAULT TRUE,
                log_member_leave BOOLEAN DEFAULT TRUE,
                log_voice_join BOOLEAN DEFAULT TRUE,
                log_voice_leave BOOLEAN DEFAULT TRUE,
                log_message_delete BOOLEAN DEFAULT TRUE,
                log_message_edit BOOLEAN DEFAULT TRUE,
                log_role_changes BOOLEAN DEFAULT TRUE,
                log_nickname_changes BOOLEAN DEFAULT TRUE,
                log_channel_create BOOLEAN DEFAULT TRUE,
                log_channel_delete BOOLEAN DEFAULT TRUE,
                log_role_create BOOLEAN DEFAULT TRUE,
                log_role_delete BOOLEAN DEFAULT TRUE,
                log_role_update BOOLEAN DEFAULT TRUE,
                log_channel_update BOOLEAN DEFAULT TRUE,
                log_voice_state_changes BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS active_tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                ticket_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                file_id VARCHAR(255) DEFAULT NULL,
                status ENUM('open', 'closed', 'deleted') DEFAULT 'open',
                claimed_by BIGINT DEFAULT NULL,
                closed_by BIGINT DEFAULT NULL,
                closed_at TIMESTAMP NULL,
                reopened_by BIGINT DEFAULT NULL,
                reopened_at TIMESTAMP NULL,
                created_by BIGINT DEFAULT NULL,
                reason TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_ticket_id (ticket_id),
                INDEX idx_status (status),
                INDEX idx_user_guild (user_id, guild_id),
                INDEX idx_created_by (created_by),
                INDEX idx_claimed_by (claimed_by)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dm_logs_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT DEFAULT NULL,
                enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_guild (user_id, guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_guild_id (guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dm_logs_commands (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                command_name VARCHAR(100) NOT NULL,
                guild_id BIGINT DEFAULT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_command_guild (user_id, command_name, guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_command_name (command_name),
                INDEX idx_guild_id (guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dm_logs_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                command_name VARCHAR(100) NOT NULL,
                executor_id BIGINT NOT NULL,
                guild_id BIGINT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_executor_id (executor_id),
                INDEX idx_guild_id (guild_id),
                INDEX idx_executed_at (executed_at)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS server_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                ticket_category_id BIGINT DEFAULT NULL,
                ticket_logs_channel_id BIGINT DEFAULT NULL,
                ticket_events_log_channel_id BIGINT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                username VARCHAR(255) NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                left_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_joined_at (joined_at),
                UNIQUE KEY unique_user_guild (user_id, guild_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_channel_id (channel_id),
                INDEX idx_created_at (created_at),
                UNIQUE KEY unique_message (message_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS command_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                command_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_command_name (command_name),
                INDEX idx_created_at (created_at)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS moderation_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                moderator_id BIGINT NOT NULL,
                action_type ENUM('warn', 'ban', 'kick', 'timeout', 'unban') NOT NULL,
                reason TEXT,
                duration INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_user_id (user_id),
                INDEX idx_moderator_id (moderator_id),
                INDEX idx_action_type (action_type),
                INDEX idx_created_at (created_at)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS member_count_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                member_count INT NOT NULL,
                bot_count INT DEFAULT 0,
                human_count INT DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_id (guild_id),
                INDEX idx_recorded_at (recorded_at),
                UNIQUE KEY unique_guild_time (guild_id, recorded_at)
            )
            """
        ]
        
        for table_sql in tables:
            try:
                # Suppress warnings for table creation
                await self.query(table_sql)
            except Exception as e:
                logger.error(f"Error creating table: {e}")
        
        logger.info("Tables de la base de données initialisées avec succès")
        
        # Exécuter les migrations
        await self.run_migrations()
    
    async def run_migrations(self):
        """Execute SQL migration files from the migrations folder"""
        try:
            migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            
            if not os.path.exists(migrations_dir):
                logger.warning(f"Migrations directory not found: {migrations_dir}")
                return
            
            # Create migrations tracking table if it doesn't exist
            await self.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_filename (filename)
                )
            """)
            
            # Get list of already executed migrations
            executed = await self.query(
                "SELECT filename FROM migrations",
                fetchall=True
            )
            executed_files = {row['filename'] for row in (executed or [])}
            
            # Get all SQL files in migrations directory
            migration_files = sorted(glob.glob(os.path.join(migrations_dir, '*.sql')))
            
            for migration_file in migration_files:
                filename = os.path.basename(migration_file)
                
                # Skip if already executed
                if filename in executed_files:
                    logger.debug(f"Migration already executed: {filename}")
                    continue
                
                logger.info(f"Executing migration: {filename}")
                
                try:
                    # Read migration file
                    with open(migration_file, 'r', encoding='utf-8') as f:
                        sql = f.read()
                    
                    # Split by semicolons and execute each statement
                    statements = [s.strip() for s in sql.split(';') if s.strip()]
                    
                    for statement in statements:
                        if statement and not statement.startswith('--'):
                            await self.execute(statement)
                    
                    # Mark migration as executed
                    await self.execute(
                        "INSERT INTO migrations (filename) VALUES (%s)",
                        (filename,)
                    )
                    
                    logger.info(f"✅ Migration executed successfully: {filename}")
                    
                except Exception as e:
                    logger.error(f"❌ Error executing migration {filename}: {e}")
                    # Continue with other migrations even if one fails
                    continue
            
            logger.info("All migrations executed successfully")
            
        except Exception as e:
            logger.error(f"Error running migrations: {e}")