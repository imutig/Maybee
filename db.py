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