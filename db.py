import asyncio
import aiomysql
import logging

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
        print("🔌 Connecting to database...")
        
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
                print("✅ Database connection established")
                return
            except Exception as e:
                print(f"❌ Connection failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise

    async def close(self):
        if self.pool:
            print("🔌 Closing database connection...")
            self.pool.close()
            await self.pool.wait_closed()
            print("✅ Database connection closed")
            
    async def query(self, query, params=None, fetchone=False, fetchall=False):
        """Execute query with improved error handling and connection management"""
        if not self.pool:
            await self.connect()
        
        # Create a clean, readable log message
        query_type = self._get_query_type(query)
        clean_query = self._clean_query_for_log(query)
        
        # Log with clean formatting
        if query_type in ["INSERT", "UPDATE", "DELETE"]:
            print(f"🔄 {query_type}: {clean_query}")
            if params:
                print(f"   📝 Values: {self._format_params(params)}")
        elif query_type == "SELECT" and self.debug:
            print(f"🔍 {query_type}: {clean_query}")
        elif query_type == "CREATE":
            print(f"🔧 {query_type}: {clean_query}")
        
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
                                    print(f"   ✅ Found {len(result)} record(s)")
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
        
        # Log with clean formatting
        if query_type in ["INSERT", "UPDATE", "DELETE"]:
            print(f"🔄 {query_type}: {clean_query}")
            if params:
                print(f"   📝 Values: {self._format_params(params)}")
        elif query_type == "SELECT" and self.debug:
            print(f"🔍 {query_type}: {clean_query}")
        
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, params)
                        if query.strip().lower().startswith("select"):
                            result = await cur.fetchall()
                            if self.debug and result:
                                print(f"   ✅ Found {len(result)} record(s)")
                            return result
                        else:
                            affected = cur.rowcount
                            if affected > 0:
                                print(f"   ✅ {affected} row(s) affected")
                            else:
                                print(f"   ℹ️  No rows affected")
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        ]
        
        for table_sql in tables:
            try:
                await self.query(table_sql)
                # Table creation logging is handled by query method
            except Exception as e:
                print(f"❌ Error creating table: {e}")
        
        print("🗃️  Database tables initialized successfully")