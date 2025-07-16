import asyncio
import aiomysql  # si tu utilises aiomysql, sinon adapte

class Database:
    def __init__(self, host, port, user, password, db):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.pool = None

    async def connect(self):
        print("[DB] Connexion à la base de données...")
        try:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                autocommit=True,
                maxsize=10
            )
            print("[DB] Connexion réussie.")
        except Exception as e:
            print(f"[DB][ERREUR] Connexion échouée : {e}")

    async def close(self):
        if self.pool:
            print("[DB] Fermeture du pool de connexions...")
            self.pool.close()
            await self.pool.wait_closed()
            print("[DB] Pool fermé.")
            
    async def query(self, query, params=None, fetchone=False, fetchall=False):
        print(f"[DB] Query : {query} | params : {params}")
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
        except Exception as e:
            print(f"[DB][ERREUR] Query error : {e}")
            return None


    async def execute(self, query, params=None):
        print(f"[DB] Exécution de la requête : {query} | params : {params}")
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
        except Exception as e:
            print(f"[DB][ERREUR] Erreur lors de l'exécution : {e}")
            return None

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
            """
        ]
        
        for table_sql in tables:
            try:
                await self.query(table_sql)
                print(f"[DB] Table créée/vérifiée avec succès")
            except Exception as e:
                print(f"[DB][ERREUR] Erreur lors de la création de table : {e}")