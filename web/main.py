"""
MaybeBot Web Dashboard - Main FastAPI Application
Professional web interface for bot configuration and management
"""

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from jose import JWTError, jwt
import secrets
from pydantic import BaseModel
import aiomysql
from pathlib import Path
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()  # Load from current directory (web/.env)
load_dotenv("../.env")  # Load from parent directory (main .env)

# Import bot modules
import sys
sys.path.append('..')
from db import Database

# Language support
SUPPORTED_LANGUAGES = ['en', 'fr']
DEFAULT_LANGUAGE = 'en'

def load_language_file(language_code: str) -> Dict[str, Any]:
    """Load language file for the web dashboard"""
    try:
        language_file = Path(__file__).parent / "languages" / f"{language_code}.json"
        if language_file.exists():
            with open(language_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Fallback to English if language file doesn't exist
            with open(Path(__file__).parent / "languages" / "en.json", 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading language file for {language_code}: {e}")
        # Return basic fallback
        return {"_meta": {"name": "English", "code": "en", "flag": "🇺🇸"}}

def detect_browser_language(accept_language: str) -> str:
    """Detect browser language from Accept-Language header"""
    if not accept_language:
        return DEFAULT_LANGUAGE
    
    # Parse Accept-Language header
    # Format: "en-US,en;q=0.9,fr;q=0.8"
    languages = []
    for lang in accept_language.split(','):
        lang = lang.strip()
        if ';' in lang:
            lang_code, quality = lang.split(';', 1)
            try:
                quality = float(quality.split('=')[1])
            except (ValueError, IndexError):
                quality = 1.0
        else:
            lang_code, quality = lang, 1.0
        
        # Extract main language code (e.g., "en" from "en-US")
        main_lang = lang_code.split('-')[0].lower()
        if main_lang in SUPPORTED_LANGUAGES:
            languages.append((main_lang, quality))
    
    # Sort by quality and return the best match
    if languages:
        languages.sort(key=lambda x: x[1], reverse=True)
        return languages[0][0]
    
    return DEFAULT_LANGUAGE

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    await create_guild_config_table()
    await create_moderation_tables()
    await create_user_languages_table()
    yield
    # Shutdown
    if database:
        await database.close()

app = FastAPI(
    title="MaybeBot Dashboard",
    description="Professional web interface for MaybeBot configuration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load environment variables
load_dotenv()

# Try to load from different possible .env files
if not os.getenv("DISCORD_TOKEN"):
    # Try railway specific env file
    if os.path.exists(".env.railway"):
        load_dotenv(".env.railway")
    # Try parent directory .env
    elif os.path.exists("../.env"):
        load_dotenv("../.env")

# Security
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Discord OAuth2 settings
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/auth/discord/callback")

# Get and clean the Discord bot token
_raw_token = os.getenv("DISCORD_TOKEN")
if _raw_token:
    # Clean the token of any potential formatting issues
    DISCORD_BOT_TOKEN = _raw_token.strip()
    # Remove any potential key=value format
    if '=' in DISCORD_BOT_TOKEN and 'DISCORD_TOKEN=' in DISCORD_BOT_TOKEN:
        DISCORD_BOT_TOKEN = DISCORD_BOT_TOKEN.split('=', 1)[1].strip()
    # Remove any quotes
    DISCORD_BOT_TOKEN = DISCORD_BOT_TOKEN.strip('"').strip("'")
else:
    DISCORD_BOT_TOKEN = None

# Debug: Print environment variable status (without exposing values)
print(f"🔍 Environment variables loaded:")
print(f"  - DISCORD_TOKEN: {'✅ Found' if DISCORD_BOT_TOKEN else '❌ Missing'}")
if DISCORD_BOT_TOKEN:
    print(f"  - Token length: {len(DISCORD_BOT_TOKEN)}")
    print(f"  - Token prefix: '{DISCORD_BOT_TOKEN[:10]}...' (should start with MTM)")
print(f"  - DB_HOST: {'✅ Found' if os.getenv('DB_HOST') else '❌ Missing'}")
print(f"  - DB_USER: {'✅ Found' if os.getenv('DB_USER') else '❌ Missing'}")
print(f"  - DISCORD_CLIENT_ID: {'✅ Found' if DISCORD_CLIENT_ID else '❌ Missing'}")
print(f"  - DISCORD_CLIENT_SECRET: {'✅ Found' if DISCORD_CLIENT_SECRET else '❌ Missing'}")

# Database
database = None

# Pydantic models
class User(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str]
    guilds: List[Dict[str, Any]] = []

class GuildConfig(BaseModel):
    guild_id: str
    xp_enabled: bool = True
    xp_multiplier: float = 1.0
    level_up_message: bool = True
    level_up_channel: Optional[str] = None
    moderation_enabled: bool = True
    welcome_enabled: bool = False
    welcome_channel: Optional[str] = None
    welcome_message: str = "Welcome {user} to {server}!"
    logs_enabled: bool = False
    logs_channel: Optional[str] = None

class XPSettings(BaseModel):
    enabled: bool = True
    xp_channel: Optional[str] = None
    level_up_message: bool = True
    level_up_channel: Optional[str] = None
    multiplier: float = 1.0

class XPConfig(BaseModel):
    guild_id: Optional[str] = None  # Make optional since it's in the URL
    enabled: Optional[bool] = True
    xp_channel: Optional[str] = None
    level_up_message: Optional[bool] = True
    level_up_channel: Optional[str] = None
    multiplier: Optional[float] = 1.0

class ModerationSettings(BaseModel):
    enabled: bool
    auto_mod: bool = False
    spam_protection: bool = True
    link_protection: bool = False
    caps_protection: bool = False
    logs_channel: Optional[str] = None

class WelcomeSettings(BaseModel):
    welcome_enabled: bool = False
    goodbye_enabled: bool = False
    welcome_channel: Optional[str] = None
    welcome_message: str = "Welcome {user} to {server}!"
    goodbye_channel: Optional[str] = None
    goodbye_message: str = "Goodbye {user}, we'll miss you!"

class ServerLogsSettings(BaseModel):
    enabled: bool = False
    channel_id: Optional[str] = None
    message_delete: bool = True
    message_edit: bool = True
    member_join: bool = True
    member_leave: bool = True
    member_update: bool = True
    voice_state_update: bool = True
    role_create: bool = True
    role_delete: bool = True
    role_update: bool = True
    channel_create: bool = True
    channel_delete: bool = True
    channel_update: bool = True

class ModerationAction(BaseModel):
    action: str  # "warn", "timeout", "kick", "ban"
    user_id: str
    reason: str = "No reason provided"
    duration: Optional[int] = None  # For timeout (in minutes)
    channel_id: Optional[str] = None  # Channel to send moderation messages to

class LanguagePreference(BaseModel):
    language: str  # Language code (e.g., "en", "fr")

class UserLanguage(BaseModel):
    user_id: str
    language: str = DEFAULT_LANGUAGE

# Utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return credentials.credentials  # Return the full token
    except JWTError:
        raise credentials_exception

async def get_user_guilds(access_token: str) -> List[Dict]:
    """Get user's Discord guilds"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
            if response.status_code == 200:
                guilds = response.json()
                # Filter guilds where user has admin permissions
                admin_guilds = []
                for guild in guilds:
                    permissions = int(guild.get("permissions", 0))
                    if permissions & 0x8:  # Administrator permission
                        admin_guilds.append(guild)
                return admin_guilds
            else:
                print(f"Discord API error when fetching user guilds: {response.status_code}")
                return []
    except httpx.ReadTimeout:
        print("Timeout when fetching user guilds from Discord API")
        return []
    except Exception as e:
        print(f"Error fetching user guilds: {e}")
        return []

async def get_bot_guilds() -> List[str]:
    """Get guilds where the bot is present from database"""
    try:
        # Get distinct guild IDs from the database where the bot has been active
        guilds_data = await database.query(
            "SELECT DISTINCT guild_id FROM xp_data", 
            fetchall=True
        )
        return [str(guild['guild_id']) for guild in guilds_data] if guilds_data else []
    except Exception as e:
        print(f"Error getting bot guilds from database: {e}")
        return []

# Database initialization
async def init_database():
    global database
    database = Database(
        host=os.getenv('DB_HOST'),
        port=3306,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME')
    )
    await database.connect()
    
    # Add helper methods to database object
    async def fetch_one(query, params=None):
        return await database.query(query, params, fetchone=True)
    
    async def fetch_all(query, params=None):
        return await database.query(query, params, fetchall=True)
    
    # Bind helper methods to database object
    database.fetch_one = fetch_one
    database.fetch_all = fetch_all

async def create_guild_config_table():
    """Create the guild_config table if it doesn't exist"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id VARCHAR(20) PRIMARY KEY,
        xp_enabled BOOLEAN DEFAULT TRUE,
        xp_multiplier FLOAT DEFAULT 1.0,
        level_up_message BOOLEAN DEFAULT TRUE,
        level_up_channel VARCHAR(20) NULL,
        moderation_enabled BOOLEAN DEFAULT TRUE,
        welcome_enabled BOOLEAN DEFAULT FALSE,
        welcome_channel VARCHAR(20) NULL,
        welcome_message VARCHAR(500) DEFAULT 'Welcome {user} to {server}!',
        logs_enabled BOOLEAN DEFAULT FALSE,
        logs_channel VARCHAR(20) NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    
    try:
        await database.execute(create_table_sql)
        print("✅ Guild config table created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating guild_config table: {e}")
        return False

async def create_moderation_tables():
    """Create moderation tables if they don't exist"""
    warnings_table = """
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
    """
    
    timeouts_table = """
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
    """
    
    try:
        await database.execute(warnings_table)
        await database.execute(timeouts_table)
        print("✅ Moderation tables created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating moderation tables: {e}")
        return False

async def create_user_languages_table():
    """Create the user_languages table if it doesn't exist"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS user_languages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        language_code VARCHAR(10) NOT NULL DEFAULT 'en',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id)
    )
    """
    
    try:
        await database.execute(create_table_sql)
        print("✅ User languages table created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating user_languages table: {e}")
        return False

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/auth/discord")
async def discord_auth():
    """Redirect to Discord OAuth2"""
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify guilds"
    )
    return RedirectResponse(discord_login_url)

@app.get("/auth/discord/callback")
async def discord_callback(code: str):
    """Handle Discord OAuth2 callback"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Exchange code for access token
            token_data = {
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            }
            
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get access token")
            
            token_json = token_response.json()
            access_token = token_json["access_token"]
            
            # Get user information
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user information")
            
            user_data = user_response.json()
            
            # Create JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            jwt_token = create_access_token(
                data={"sub": user_data["id"], "discord_token": access_token}, 
                expires_delta=access_token_expires
            )
            
            # Redirect to dashboard with token
            response = RedirectResponse("/dashboard", status_code=302)
            response.set_cookie(
                key="access_token", 
                value=jwt_token, 
                httponly=False,  # Allow JavaScript to read the cookie for dashboard functionality
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
            return response
            
    except httpx.ReadTimeout:
        print("Timeout error during Discord OAuth callback")
        raise HTTPException(status_code=503, detail="Discord API timeout. Please try again.")
    except httpx.RequestError as e:
        print(f"Request error during Discord OAuth callback: {e}")
        raise HTTPException(status_code=503, detail="Discord API connection error. Please try again.")
    except Exception as e:
        print(f"Unexpected error during Discord OAuth callback: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed. Please try again.")

@app.get("/api/user/me")
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user information"""
    try:
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        discord_token = payload.get("discord_token")
        
        if not discord_token:
            raise HTTPException(status_code=401, detail="No Discord token")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get user info
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {discord_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            
            user_data = user_response.json()
            
            # Get user guilds and filter by bot presence
            user_guilds = await get_user_guilds(discord_token)
            bot_guilds = await get_bot_guilds()
            
            print(f"🔍 Debug: User guilds count: {len(user_guilds)}")
            print(f"🔍 Debug: Bot guilds count: {len(bot_guilds)}")
            print(f"🔍 Debug: Bot guild IDs: {bot_guilds}")
            
            # Only show guilds where both user has admin and bot is present
            manageable_guilds = [
                guild for guild in user_guilds 
                if guild["id"] in bot_guilds
            ]
            
            print(f"🔍 Debug: Manageable guilds count: {len(manageable_guilds)}")
            if manageable_guilds:
                print(f"🔍 Debug: Manageable guild names: {[g.get('name', 'Unknown') for g in manageable_guilds]}")
            
            return {
                "id": user_data["id"],
                "username": user_data["username"],
                "discriminator": user_data.get("discriminator", "0"),
                "avatar": user_data.get("avatar"),
                "guilds": manageable_guilds
            }
    
    except httpx.ReadTimeout:
        print("Timeout error when fetching user info from Discord")
        raise HTTPException(status_code=503, detail="Discord API timeout. Please try again.")
    except httpx.RequestError as e:
        print(f"Request error when fetching user info: {e}")
        raise HTTPException(status_code=503, detail="Discord API connection error. Please try again.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Unexpected error in get_current_user_info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/guild/{guild_id}/config")
async def get_guild_config(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get guild configuration"""
    try:
        # Verify user has access to this guild
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get config from database
        config_data = await database.fetch_one(
            "SELECT * FROM guild_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # Get XP config from xp_config table
        xp_config_data = await database.fetch_one(
            "SELECT * FROM xp_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # Default configuration
        default_config = {
            "guild_id": guild_id,
            "xp_enabled": True,
            "xp_multiplier": 1.0,
            "level_up_message": True,
            "level_up_channel": None,
            "xp_channel": None,
            "moderation_enabled": True,
            "welcome_enabled": False,
            "welcome_channel": None,
            "welcome_message": "Welcome {user} to {server}!",
            "logs_enabled": False,
            "logs_channel": None
        }
        
        # Update with actual config data if it exists
        if config_data:
            try:
                config_dict = dict(config_data)
                # Ensure string conversion for channel IDs
                if 'level_up_channel' in config_dict and config_dict['level_up_channel']:
                    config_dict['level_up_channel'] = str(config_dict['level_up_channel'])
                if 'welcome_channel' in config_dict and config_dict['welcome_channel']:
                    config_dict['welcome_channel'] = str(config_dict['welcome_channel'])
                if 'logs_channel' in config_dict and config_dict['logs_channel']:
                    config_dict['logs_channel'] = str(config_dict['logs_channel'])
                default_config.update(config_dict)
            except Exception as config_convert_error:
                print(f"Config conversion error: {config_convert_error}")
        
        # Update with XP-specific config if it exists
        if xp_config_data:
            try:
                default_config["xp_channel"] = str(xp_config_data[1]) if xp_config_data[1] else None
            except Exception as xp_convert_error:
                print(f"XP config conversion error: {xp_convert_error}")
        
        return default_config
        
    except Exception as e:
        print(f"Config error details: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"Config error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/config")
async def update_guild_config(
    guild_id: str, 
    config: GuildConfig, 
    current_user: str = Depends(get_current_user)
):
    """Update guild configuration"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Update config in database
        await database.execute(
            """INSERT INTO guild_config 
               (guild_id, xp_enabled, xp_multiplier, level_up_message, level_up_channel,
                moderation_enabled, welcome_enabled, welcome_channel, welcome_message,
                logs_enabled, logs_channel, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               xp_enabled = VALUES(xp_enabled),
               xp_multiplier = VALUES(xp_multiplier),
               level_up_message = VALUES(level_up_message),
               level_up_channel = VALUES(level_up_channel),
               moderation_enabled = VALUES(moderation_enabled),
               welcome_enabled = VALUES(welcome_enabled),
               welcome_channel = VALUES(welcome_channel),
               welcome_message = VALUES(welcome_message),
               logs_enabled = VALUES(logs_enabled),
               logs_channel = VALUES(logs_channel),
               updated_at = VALUES(updated_at)""",
            (guild_id, config.xp_enabled, config.xp_multiplier, config.level_up_message,
            config.level_up_channel, config.moderation_enabled, config.welcome_enabled,
            config.welcome_channel, config.welcome_message, config.logs_enabled,
            config.logs_channel, datetime.utcnow())
        )
        
        return {"message": "Configuration updated successfully"}
        
    except Exception as e:
        print(f"Config update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/stats")
async def get_guild_stats(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get guild statistics"""
    try:
        # Verify access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get various stats
        stats = {}
        
        # Total members with XP
        member_count = await database.fetch_one(
            "SELECT COUNT(*) as count FROM xp_data WHERE guild_id = %s",
            (guild_id,)
        )
        stats["total_members"] = member_count["count"] if member_count else 0
        
        # Total XP given
        total_xp = await database.fetch_one(
            "SELECT SUM(xp) as total FROM xp_data WHERE guild_id = %s",
            (guild_id,)
        )
        stats["total_xp"] = total_xp["total"] if total_xp and total_xp["total"] else 0
        
        # Average level
        avg_level = await database.fetch_one(
            "SELECT AVG(level) as avg FROM xp_data WHERE guild_id = %s",
            (guild_id,)
        )
        stats["average_level"] = round(avg_level["avg"], 1) if avg_level and avg_level["avg"] else 0
        
        # Activity last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = await database.fetch_one(
            "SELECT COUNT(*) as count FROM xp_history WHERE guild_id = %s AND timestamp >= %s",
            (guild_id, week_ago)
        )
        stats["recent_activity"] = recent_activity["count"] if recent_activity else 0
        
        # Top 5 users
        top_users = await database.fetch_all(
            "SELECT user_id, xp, level FROM xp_data WHERE guild_id = %s ORDER BY xp DESC LIMIT 5",
            (guild_id,)
        )
        # Convert user_id to string to prevent JavaScript precision loss with large integers
        stats["top_users"] = []
        if top_users:
            for user in top_users:
                user_dict = dict(user)
                user_dict["user_id"] = str(user_dict["user_id"])  # Convert to string for JavaScript
                stats["top_users"].append(user_dict)
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/channels")
async def get_guild_channels(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get guild channels for configuration"""
    try:
        print(f"Fetching channels for guild {guild_id}")
        
        # Debug the bot token
        bot_token = DISCORD_BOT_TOKEN
        print(f"Bot token exists: {bool(bot_token)}")
        if bot_token:
            print(f"🔍 Raw token length: {len(bot_token)}")
            print(f"🔍 Token starts with: '{bot_token[:5]}...'" if bot_token else "❌ No token")
            print(f"🔍 Token ends with: '...{bot_token[-5:]}'" if bot_token else "❌ No token")
            
            # Clean the token
            bot_token = bot_token.strip()
            if bot_token and not bot_token.startswith('MTM'):
                print(f"⚠️  Token doesn't start with expected prefix. First 10 chars: '{bot_token[:10]}'")
                # Try to fix common issues
                if '=' in bot_token and 'DISCORD_TOKEN=' in bot_token:
                    bot_token = bot_token.split('=', 1)[1]
                    print(f"🔧 Cleaned token from env format: '{bot_token[:10]}...'")
            
            print(f"🔍 Using cleaned token: '{bot_token[:10]}...'")
        
        # Try to get Discord guild channels via bot token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://discord.com/api/guilds/{guild_id}/channels",
                headers={"Authorization": f"Bot {bot_token}"}
            )
            
            print(f"Discord API response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Discord API error: {response.text}")
            
            if response.status_code == 200:
                channels = response.json()
                print(f"Total channels found: {len(channels)}")
                # Filter to text channels only
                text_channels = [
                    {"id": ch["id"], "name": ch["name"]} 
                    for ch in channels 
                    if ch["type"] == 0  # Text channel
                ]
                print(f"Text channels found: {len(text_channels)}")
                return text_channels
            else:
                # Fallback to mock channels if API fails
                print("Using fallback mock channels due to API error")
                return [
                    {"id": "1234567890123456789", "name": "general"},
                    {"id": "1234567890123456790", "name": "announcements"},
                    {"id": "1234567890123456791", "name": "bot-commands"},
                    {"id": "1234567890123456792", "name": "level-ups"},
                    {"id": "1234567890123456793", "name": "xp-tracking"},
                    {"id": "1234567890123456794", "name": "chat"}
                ]
                
    except Exception as e:
        print(f"Error fetching channels: {e}")
        # Return mock channels as fallback
        return [
            {"id": "1234567890123456789", "name": "general"},
            {"id": "1234567890123456790", "name": "announcements"},
            {"id": "1234567890123456791", "name": "bot-commands"},
            {"id": "1234567890123456792", "name": "level-ups"},
            {"id": "1234567890123456793", "name": "xp-tracking"},
            {"id": "1234567890123456794", "name": "chat"}
        ]

@app.get("/api/guild/{guild_id}/xp")
async def get_xp_config(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get XP system configuration for a guild"""
    try:
        # Verify user has access to this guild
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get XP config from xp_config table
        xp_config_data = await database.fetch_one(
            "SELECT * FROM xp_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # Get general config for level up settings
        general_config = await database.fetch_one(
            "SELECT * FROM guild_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        return {
            "guild_id": guild_id,
            "enabled": True,  # XP is enabled by default
            "xp_channel": str(xp_config_data[1]) if xp_config_data and xp_config_data[1] else None,
            "level_up_message": general_config.get('level_up_message', True) if general_config else True,
            "level_up_channel": general_config.get('level_up_channel') if general_config else None,
            "multiplier": general_config.get('xp_multiplier', 1.0) if general_config else 1.0
        }
        
    except Exception as e:
        print(f"XP config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/xp")
async def update_xp_config(
    guild_id: str, 
    config: XPConfig, 
    current_user: str = Depends(get_current_user)
):
    """Update XP system configuration for a guild"""
    print(f"Received XP config update for guild {guild_id}")
    print(f"Config data: {config}")
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Update or insert XP channel config
        if config.xp_channel:
            await database.execute(
                """INSERT INTO xp_config (guild_id, xp_channel) 
                   VALUES (%s, %s) 
                   ON DUPLICATE KEY UPDATE xp_channel = VALUES(xp_channel)""",
                (guild_id, int(config.xp_channel))
            )
        else:
            # Remove XP config if no channel specified
            await database.execute(
                "DELETE FROM xp_config WHERE guild_id = %s",
                (guild_id,)
            )
        
        # Update general config with level up settings
        await database.execute(
            """INSERT INTO guild_config 
               (guild_id, xp_enabled, xp_multiplier, level_up_message, level_up_channel,
                moderation_enabled, welcome_enabled, welcome_channel, welcome_message,
                logs_enabled, logs_channel, updated_at)
               VALUES (%s, %s, %s, %s, %s, TRUE, FALSE, NULL, 'Welcome {user} to {server}!', FALSE, NULL, %s)
               ON DUPLICATE KEY UPDATE
               xp_enabled = VALUES(xp_enabled),
               xp_multiplier = VALUES(xp_multiplier),
               level_up_message = VALUES(level_up_message),
               level_up_channel = VALUES(level_up_channel),
               updated_at = VALUES(updated_at)""",
            (guild_id, config.enabled, config.multiplier, config.level_up_message,
            config.level_up_channel, datetime.utcnow())
        )
        
        return {"message": "XP configuration updated successfully"}
        
    except Exception as e:
        print(f"XP config update error details: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"XP config update traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/xp/test-levelup")
async def send_test_levelup_message(
    guild_id: str, 
    current_user: str = Depends(get_current_user)
):
    """Send a test level up message to verify XP configuration"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get user info for the test message
        user_data = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = user_data.get("sub")
        
        # Get XP config
        xp_config = await database.fetch_one(
            "SELECT * FROM xp_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        general_config = await database.fetch_one(
            "SELECT * FROM guild_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        print(f"🔍 Debug: general_config = {general_config}")
        print(f"🔍 Debug: general_config length = {len(general_config) if general_config else 0}")
        
        # If no guild config exists, create a default one
        if not general_config:
            print(f"⚠️ No guild config found for {guild_id}, creating default")
            await database.execute(
                """INSERT INTO guild_config 
                (guild_id, xp_enabled, xp_multiplier, level_up_message, level_up_channel, 
                 moderation_enabled, welcome_enabled, welcome_channel, welcome_message, 
                 logs_enabled, logs_channel) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (guild_id, True, 1.0, True, None, True, False, None, 
                 'Welcome {user} to {server}!', False, None)
            )
            # Fetch the newly created config
            general_config = await database.fetch_one(
                "SELECT * FROM guild_config WHERE guild_id = %s",
                (guild_id,)
            )
        
        # Determine which channel to send to
        target_channel = None
        if general_config and general_config.get('level_up_channel'):  # level_up_channel
            target_channel = general_config['level_up_channel']
        elif xp_config and len(xp_config) > 1 and xp_config[1]:  # xp_channel
            target_channel = xp_config[1]
        
        if not target_channel:
            return {"message": "No XP or level up channel configured. Please set up a channel first.", "success": False}
        
        # Send message via Discord bot
        bot_token = DISCORD_BOT_TOKEN  # Use the global variable
        if not bot_token:
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        # Send test message through Discord API
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json"
            }
            
            embed_data = {
                "embeds": [{
                    "title": "🎉 Level Up! (Test Message)",
                    "description": f"<@{user_id}> just reached **Level 5**! 🐝",
                    "color": 0xFFD700,  # Gold color
                    "fields": [
                        {
                            "name": "Total XP",
                            "value": "1,250 XP",
                            "inline": True
                        },
                        {
                            "name": "Next Level",
                            "value": "1,500 XP needed",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "This is a test message from Maybee Dashboard"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            response = await client.post(
                f"https://discord.com/api/v10/channels/{target_channel}/messages",
                headers=headers,
                json=embed_data
            )
            
            if response.status_code == 200:
                return {
                    "message": f"Test level up message sent successfully to <#{target_channel}>!",
                    "success": True,
                    "channel_id": str(target_channel)
                }
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                return {
                    "message": f"Failed to send test message. Error: {error_data}",
                    "success": False
                }
        
    except Exception as e:
        print(f"Test levelup error details: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"Test levelup traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/language-test", response_class=HTMLResponse)
async def language_test_page(request: Request):
    """Language test page - for testing language functionality"""
    return templates.TemplateResponse("language-test.html", {"request": request})

async def verify_guild_access(guild_id: str, current_user: str) -> bool:
    """Verify user has access to a guild through Discord API or bot presence"""
    try:
        print(f"🔍 Verifying guild access for guild {guild_id}")
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        discord_token = payload.get("discord_token")
        print(f"🔍 Discord token available: {bool(discord_token)}")
        
        user_guilds = await get_user_guilds(discord_token)
        bot_guilds = await get_bot_guilds()
        
        print(f"🔍 User guilds count: {len(user_guilds)}")
        print(f"🔍 Bot guilds: {bot_guilds}")
        
        # Check if user has access through Discord API OR if the guild is in bot's list
        has_user_access = any(guild["id"] == guild_id for guild in user_guilds)
        has_bot_access = guild_id in bot_guilds
        
        print(f"🔍 User access: {has_user_access}, Bot access: {has_bot_access}")
        
        result = has_user_access or has_bot_access
        print(f"🔍 Final access result: {result}")
        
        return result
    except Exception as e:
        print(f"❌ Exception in verify_guild_access: {e}")
        return False

# Welcome System API Endpoints
@app.get("/api/guild/{guild_id}/welcome")
async def get_welcome_config(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get welcome configuration for a guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get welcome config from welcome_config table (primary source)
        welcome_config = await database.fetch_one(
            "SELECT * FROM welcome_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # Also check guild_config table for consistency
        guild_config = await database.fetch_one(
            "SELECT * FROM guild_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        if welcome_config:
            return {
                "enabled": True,
                "welcome_channel": str(welcome_config["welcome_channel"]) if welcome_config["welcome_channel"] else None,
                "welcome_message": welcome_config["welcome_message"] or "Welcome {user} to {server}!",
                "goodbye_channel": str(welcome_config["goodbye_channel"]) if welcome_config["goodbye_channel"] else None,
                "goodbye_message": welcome_config["goodbye_message"] or "Goodbye {user}, we'll miss you!"
            }
        elif guild_config and guild_config.get("welcome_enabled") and guild_config.get("welcome_channel"):
            # If no welcome_config but guild_config has welcome settings, use those
            return {
                "enabled": guild_config.get("welcome_enabled", False),
                "welcome_channel": str(guild_config["welcome_channel"]) if guild_config["welcome_channel"] else None,
                "welcome_message": guild_config.get("welcome_message", "Welcome {user} to {server}!"),
                "goodbye_channel": None,
                "goodbye_message": "Goodbye {user}, we'll miss you!"
            }
        else:
            return {
                "enabled": False,
                "welcome_channel": None,
                "welcome_message": "Welcome {user} to {server}!",
                "goodbye_channel": None,
                "goodbye_message": "Goodbye {user}, we'll miss you!"
            }
    
    except Exception as e:
        print(f"Welcome config get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/welcome")
async def update_welcome_config(
    guild_id: str,
    config: WelcomeSettings,
    current_user: str = Depends(get_current_user)
):
    """Update welcome configuration for a guild"""
    try:
        print(f"Received welcome config update for guild {guild_id}")
        print(f"Config data: welcome_enabled={config.welcome_enabled} goodbye_enabled={config.goodbye_enabled} welcome_channel='{config.welcome_channel}' welcome_message='{config.welcome_message}' goodbye_channel='{config.goodbye_channel}' goodbye_message='{config.goodbye_message}'")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        if config.welcome_enabled or config.goodbye_enabled:
            # Insert or update welcome config
            await database.execute(
                """INSERT INTO welcome_config 
                   (guild_id, welcome_channel, welcome_message, goodbye_channel, goodbye_message, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   welcome_channel = VALUES(welcome_channel),
                   welcome_message = VALUES(welcome_message),
                   goodbye_channel = VALUES(goodbye_channel),
                   goodbye_message = VALUES(goodbye_message),
                   updated_at = VALUES(updated_at)""",
                (guild_id, 
                 int(config.welcome_channel) if config.welcome_channel else None,
                 config.welcome_message,
                 int(config.goodbye_channel) if config.goodbye_channel else None,
                 config.goodbye_message,
                 datetime.utcnow())
            )
        else:
            # Delete welcome config if disabled
            await database.execute(
                "DELETE FROM welcome_config WHERE guild_id = %s",
                (guild_id,)
            )
        
        # Update general config
        await database.execute(
            """INSERT INTO guild_config 
               (guild_id, welcome_enabled, welcome_channel, welcome_message, updated_at)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               welcome_enabled = VALUES(welcome_enabled),
               welcome_channel = VALUES(welcome_channel),
               welcome_message = VALUES(welcome_message),
               updated_at = VALUES(updated_at)""",
            (guild_id, config.welcome_enabled, 
             int(config.welcome_channel) if config.welcome_channel else None,
             config.welcome_message, datetime.utcnow())
        )
        
        return {"message": "Welcome configuration updated successfully"}
        
    except Exception as e:
        print(f"Welcome config update error: {e}")
        import traceback
        print(f"Welcome config update traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/welcome/test")
async def send_test_welcome_message(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Send a test welcome message to verify configuration"""
    try:
        print(f"🔍 Testing welcome message for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get user info for the test message
        user_data = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = user_data.get("sub")
        
        # Get welcome config from welcome_config table first
        welcome_config = await database.fetch_one(
            "SELECT * FROM welcome_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # If no welcome_config, check guild_config table
        if not welcome_config:
            print(f"🔍 No welcome_config found, checking guild_config table...")
            guild_config = await database.fetch_one(
                "SELECT * FROM guild_config WHERE guild_id = %s",
                (guild_id,)
            )
            
            if guild_config and guild_config.get("welcome_channel"):
                print(f"🔍 Found welcome channel in guild_config: {guild_config['welcome_channel']}")
                target_channel = guild_config["welcome_channel"]
                welcome_message = guild_config.get("welcome_message", "Welcome {user} to {server}!")
            else:
                print(f"❌ No welcome channel found in guild_config")
                return {"message": "No welcome channel configured. Please set up a welcome channel first.", "success": False}
        else:
            print(f"🔍 Found welcome_config: {welcome_config}")
            target_channel = welcome_config["welcome_channel"]
            welcome_message = welcome_config.get("welcome_message", "Welcome {user} to {server}!")
        
        if not target_channel:
            return {"message": "No welcome channel configured. Please set up a welcome channel first.", "success": False}
        
        print(f"🔍 Using target channel: {target_channel}")
        print(f"🔍 Using welcome message: {welcome_message}")
        
        # Get bot token
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        print(f"🔍 Bot token available: {bool(bot_token)}")
        
        # Get guild info for server name
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
            
            print(f"🔍 Getting guild info for guild {guild_id}")
            # Get guild info for server name
            guild_response = await client.get(
                f"https://discord.com/api/v10/guilds/{guild_id}",
                headers=headers
            )
            
            print(f"🔍 Guild response status: {guild_response.status_code}")
            guild_name = "Unknown Server"
            if guild_response.status_code == 200:
                guild_data = guild_response.json()
                guild_name = guild_data.get("name", "Unknown Server")
                print(f"🔍 Guild name: {guild_name}")
            
            # Get user info for avatar
            user_response = await client.get(
                f"https://discord.com/api/v10/users/{user_id}",
                headers=headers
            )
            
            user_avatar_url = None
            if user_response.status_code == 200:
                user_data = user_response.json()
                avatar_hash = user_data.get("avatar")
                if avatar_hash:
                    user_avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=256"
                print(f"🔍 User avatar URL: {user_avatar_url}")
            
            # Format the welcome message
            formatted_message = welcome_message.replace("{user}", f"<@{user_id}>").replace("{server}", guild_name)
            print(f"🔍 Formatted message: {formatted_message}")
            
            # Create embed with user avatar
            embed_data = {
                "embeds": [{
                    "title": "🎉 Welcome Message Test",
                    "description": formatted_message,
                    "color": 0x00FF00,  # Green color
                    "thumbnail": {
                        "url": user_avatar_url
                    } if user_avatar_url else None,
                    "footer": {
                        "text": "This is a test message from MaybeBot Dashboard"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            # Remove thumbnail field if no avatar
            if not user_avatar_url:
                del embed_data["embeds"][0]["thumbnail"]
            
            print(f"🔍 Sending message to channel {target_channel}")
            print(f"🔍 Message payload: {embed_data}")
            
            response = await client.post(
                f"https://discord.com/api/v10/channels/{target_channel}/messages",
                headers=headers,
                json=embed_data
            )
            
            print(f"🔍 Discord API response status: {response.status_code}")
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Discord API error: {error_text}")
            
            if response.status_code == 200:
                print(f"✅ Message sent successfully to channel {target_channel}")
                return {
                    "message": f"Test welcome message sent successfully to <#{target_channel}>!",
                    "success": True,
                    "channel_id": str(target_channel),
                    "formatted_message": formatted_message
                }
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                print(f"❌ Failed to send message: {error_data}")
                return {
                    "message": f"Failed to send test message. Error: {error_data}",
                    "success": False
                }
    
    except Exception as e:
        print(f"❌ Test welcome error: {e}")
        import traceback
        print(f"❌ Test welcome traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Server Logs API Endpoints
@app.get("/api/guild/{guild_id}/logs")
async def get_server_logs_config(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get server logs configuration for a guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get server logs config from server_logs_config table (primary source)
        logs_config = await database.fetch_one(
            "SELECT * FROM server_logs_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # Also check guild_config table for consistency
        guild_config = await database.fetch_one(
            "SELECT * FROM guild_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        if logs_config:
            return {
                "enabled": True,
                "channel_id": str(logs_config["log_channel_id"]) if logs_config["log_channel_id"] else None,
                "message_delete": logs_config["log_message_delete"],
                "message_edit": logs_config["log_message_edit"],
                "member_join": logs_config["log_member_join"],
                "member_leave": logs_config["log_member_leave"],
                "member_update": logs_config.get("log_member_update", True),
                "voice_state_update": logs_config.get("log_voice_state_update", True),
                "role_create": logs_config.get("log_role_create", True),
                "role_delete": logs_config.get("log_role_delete", True),
                "role_update": logs_config["log_role_changes"],
                "channel_create": logs_config["log_channel_create"],
                "channel_delete": logs_config["log_channel_delete"],
                "channel_update": logs_config.get("log_channel_update", True)
            }
        elif guild_config and guild_config.get("logs_enabled") and guild_config.get("logs_channel"):
            # If no server_logs_config but guild_config has logs settings, use those
            return {
                "enabled": guild_config.get("logs_enabled", False),
                "channel_id": str(guild_config["logs_channel"]) if guild_config["logs_channel"] else None,
                "message_delete": True,
                "message_edit": True,
                "member_join": True,
                "member_leave": True,
                "member_update": True,
                "voice_state_update": True,
                "role_create": True,
                "role_delete": True,
                "role_update": True,
                "channel_create": True,
                "channel_delete": True,
                "channel_update": True
            }
        else:
            return {
                "enabled": False,
                "channel_id": None,
                "message_delete": True,
                "message_edit": True,
                "member_join": True,
                "member_leave": True,
                "member_update": True,
                "voice_state_update": True,
                "role_create": True,
                "role_delete": True,
                "role_update": True,
                "channel_create": True,
                "channel_delete": True,
                "channel_update": True
            }
    
    except Exception as e:
        print(f"Server logs config get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/logs")
async def update_server_logs_config(
    guild_id: str,
    config: ServerLogsSettings,
    current_user: str = Depends(get_current_user)
):
    """Update server logs configuration for a guild"""
    try:
        print(f"Received server logs config update for guild {guild_id}")
        print(f"Config data: {config}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        if config.enabled:
            # Insert or update server logs config
            await database.execute(
                """INSERT INTO server_logs_config 
                   (guild_id, log_channel_id, log_member_join, log_member_leave, log_voice_join, log_voice_leave,
                    log_message_delete, log_message_edit, log_role_changes, log_nickname_changes,
                    log_channel_create, log_channel_delete, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   log_channel_id = %s,
                   log_member_join = %s,
                   log_member_leave = %s,
                   log_voice_join = %s,
                   log_voice_leave = %s,
                   log_message_delete = %s,
                   log_message_edit = %s,
                   log_role_changes = %s,
                   log_nickname_changes = %s,
                   log_channel_create = %s,
                   log_channel_delete = %s,
                   updated_at = %s""",
                (guild_id, 
                 int(config.channel_id) if config.channel_id else None,
                 config.member_join, config.member_leave,
                 config.voice_state_update, config.voice_state_update,  # Map to existing fields
                 config.message_delete, config.message_edit,
                 config.role_update, config.member_update,  # Map role_update to role_changes, member_update to nickname_changes
                 config.channel_create, config.channel_delete,
                 datetime.utcnow(),
                 # ON DUPLICATE KEY UPDATE values
                 int(config.channel_id) if config.channel_id else None,
                 config.member_join, config.member_leave,
                 config.voice_state_update, config.voice_state_update,
                 config.message_delete, config.message_edit,
                 config.role_update, config.member_update,
                 config.channel_create, config.channel_delete,
                 datetime.utcnow())
            )
        else:
            # Delete server logs config if disabled
            await database.execute(
                "DELETE FROM server_logs_config WHERE guild_id = %s",
                (guild_id,)
            )
        
        # Update general config for bot sync
        await database.execute(
            """INSERT INTO guild_config 
               (guild_id, logs_enabled, logs_channel, updated_at)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               logs_enabled = %s,
               logs_channel = %s,
               updated_at = %s""",
            (guild_id, config.enabled, 
             int(config.channel_id) if config.channel_id else None,
             datetime.utcnow(),
             # ON DUPLICATE KEY UPDATE values
             config.enabled,
             int(config.channel_id) if config.channel_id else None,
             datetime.utcnow())
        )
        
        return {"message": "Server logs configuration updated successfully"}
        
    except Exception as e:
        print(f"Server logs config update error: {e}")
        import traceback
        print(f"Server logs config update traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Moderation API Endpoints
@app.get("/api/guild/{guild_id}/members")
async def get_guild_members(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get guild members for moderation"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get bot token from environment
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            print("❌ No Discord bot token found")
            return {"members": []}
        
        # Debug: Check for token corruption
        print(f"🔍 Raw token length: {len(bot_token) if bot_token else 0}")
        print(f"🔍 Token starts with: '{bot_token[:5]}...'" if bot_token else "❌ No token")
        print(f"🔍 Token ends with: '...{bot_token[-5:]}'" if bot_token else "❌ No token")
        print(f"🔍 Environment raw: '{os.getenv('DISCORD_TOKEN')[:5]}...{os.getenv('DISCORD_TOKEN')[-5:]}'" if os.getenv('DISCORD_TOKEN') else 'NOT FOUND')
        
        # Clean the token - remove any whitespace or invisible characters
        bot_token = bot_token.strip() if bot_token else None
        if bot_token and not bot_token.startswith('MTM'):
            print(f"⚠️  Token doesn't start with expected prefix. First 10 chars: '{bot_token[:10]}'")
            # Try to fix common issues
            if '=' in bot_token and bot_token.startswith('DISCORD_TOKEN='):
                bot_token = bot_token.split('=', 1)[1]
                print(f"🔧 Cleaned token from env format: '{bot_token[:10]}...'")
        
        print(f"🔍 Using cleaned bot token: {bot_token[:20]}..." if bot_token else "❌ No bot token found")
        print(f"🔍 Guild ID being accessed: {guild_id}")
        
        # Get guild members from Discord API
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, let's check if the bot is in the guild
            guild_response = await client.get(
                f"https://discord.com/api/v10/guilds/{guild_id}",
                headers={"Authorization": f"Bot {bot_token}"}
            )
            
            print(f"Guild info response status: {guild_response.status_code}")
            if guild_response.status_code != 200:
                print(f"❌ Bot not in guild or guild access denied: {guild_response.status_code}")
                error_detail = guild_response.json() if guild_response.headers.get('content-type') == 'application/json' else guild_response.text
                print(f"Guild error details: {error_detail}")
                return {"members": []}
            
            guild_info = guild_response.json()
            print(f"✅ Bot has access to guild: {guild_info.get('name', 'Unknown')}")
            
            # Now try to get members
            response = await client.get(
                f"https://discord.com/api/v10/guilds/{guild_id}/members",
                headers={"Authorization": f"Bot {bot_token}"},
                params={"limit": 100}
            )
            
            print(f"Discord API members response status: {response.status_code}")
            
            if response.status_code == 200:
                members = response.json()
                print(f"Successfully fetched {len(members)} members")
                # Filter out bots and format member data
                member_list = []
                for member in members:
                    if not member["user"].get("bot", False):
                        member_list.append({
                            "id": member["user"]["id"],
                            "username": member["user"]["username"],
                            "display_name": member.get("nick", member["user"]["username"]),
                            "avatar": member["user"].get("avatar"),
                            "joined_at": member.get("joined_at")
                        })
                
                print(f"Filtered to {len(member_list)} non-bot members")
                return {"members": member_list}
            elif response.status_code == 403:
                # Bot doesn't have permission to view members
                print(f"❌ Bot lacks permission to view members in guild {guild_id}")
                return {"members": []}
            elif response.status_code == 401:
                # Bot token is invalid or bot needs GUILD_MEMBERS intent
                error_detail = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                print(f"❌ Bot unauthorized to view members in guild {guild_id}")
                print(f"Error details: {error_detail}")
                return {"members": []}
            else:
                print(f"❌ Discord API error: {response.status_code}")
                error_detail = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                print(f"Error details: {error_detail}")
                return {"members": []}
    
    except Exception as e:
        print(f"Get guild members error: {e}")
        import traceback
        print(f"Get guild members traceback: {traceback.format_exc()}")
        # Return empty list instead of error for better UX
        return {"members": []}

@app.get("/api/bot-status")
async def get_bot_status():
    """Check if the bot token is valid"""
    try:
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            return {"valid": False, "error": "No bot token configured"}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {bot_token}"}
            )
            
            if response.status_code == 200:
                bot_info = response.json()
                return {
                    "valid": True,
                    "bot_id": bot_info.get("id"),
                    "bot_username": bot_info.get("username"),
                    "bot_discriminator": bot_info.get("discriminator")
                }
            else:
                return {
                    "valid": False,
                    "error": f"Invalid token: {response.status_code}",
                    "details": response.text
                }
    except Exception as e:
        return {"valid": False, "error": str(e)}

@app.get("/api/guild/{guild_id}/bot-info")
async def get_bot_guild_info(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get bot information for a specific guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get bot token from environment
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            return {"error": "Bot token not configured"}
        
        # Get guild info from Discord API
        async with httpx.AsyncClient(timeout=10.0) as client:
            guild_response = await client.get(
                f"https://discord.com/api/v10/guilds/{guild_id}",
                headers={"Authorization": f"Bot {bot_token}"}
            )
            
            if guild_response.status_code == 200:
                guild_data = guild_response.json()
                
                # Try to get bot member info
                bot_member_response = await client.get(
                    f"https://discord.com/api/v10/users/@me",
                    headers={"Authorization": f"Bot {bot_token}"}
                )
                
                bot_info = {"id": "unknown"}
                if bot_member_response.status_code == 200:
                    bot_info = bot_member_response.json()
                
                # Try to get bot's permissions in the guild
                bot_guild_member_response = await client.get(
                    f"https://discord.com/api/v10/guilds/{guild_id}/members/{bot_info['id']}",
                    headers={"Authorization": f"Bot {bot_token}"}
                )
                
                permissions = "Unknown"
                if bot_guild_member_response.status_code == 200:
                    bot_member_data = bot_guild_member_response.json()
                    permissions = bot_member_data.get("permissions", "Unknown")
                
                return {
                    "guild_name": guild_data.get("name"),
                    "bot_id": bot_info.get("id"),
                    "bot_username": bot_info.get("username"),
                    "bot_permissions": permissions,
                    "guild_member_count": guild_data.get("member_count", "Unknown"),
                    "bot_in_guild": True
                }
            else:
                return {"error": f"Cannot access guild: {guild_response.status_code}"}
                
    except Exception as e:
        print(f"Bot info error: {e}")
        return {"error": str(e)}

@app.post("/api/guild/{guild_id}/moderation/action")
async def perform_moderation_action(
    guild_id: str,
    action: ModerationAction,
    current_user: str = Depends(get_current_user)
):
    """Perform a moderation action on a user"""
    try:
        print(f"🔍 Received moderation action for guild {guild_id}")
        print(f"📝 Action data: {action}")
        print(f"👤 Current user: {current_user}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            print("❌ Access denied to guild")
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get user info
        user_data = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        moderator_id = user_data.get("sub")
        
        # Get bot token from environment
        bot_token = DISCORD_BOT_TOKEN
        print(f"🔍 Bot token loaded: {bool(bot_token)}")
        if bot_token:
            print(f"🔍 Bot token prefix: {bot_token[:10]}...")
        if not bot_token:
            print("❌ No bot token configured")
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
            
            # Get user info for display
            user_response = await client.get(
                f"https://discord.com/api/v10/users/{action.user_id}",
                headers=headers
            )
            user_info = user_response.json() if user_response.status_code == 200 else {"username": "Unknown User"}
            
            # Get moderator info
            moderator_response = await client.get(
                f"https://discord.com/api/v10/users/{moderator_id}",
                headers=headers
            )
            moderator_info = moderator_response.json() if moderator_response.status_code == 200 else {"username": "Unknown Moderator"}
            
            success_message = ""
            log_message = ""
            
            if action.action == "warn":
                print(f"⚠️ Processing warning for user {action.user_id}")
                # Add warning to database
                await database.execute(
                    """INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (guild_id, action.user_id, moderator_id, action.reason, datetime.utcnow())
                )
                print(f"✅ Warning saved to database")
                
                # Send DM to user
                try:
                    print(f"📤 Attempting to send DM to user {action.user_id}")
                    dm_response = await client.post(
                        f"https://discord.com/api/v10/users/@me/channels",
                        headers=headers,
                        json={"recipient_id": action.user_id}
                    )
                    print(f"📤 DM channel response: {dm_response.status_code}")
                    
                    if dm_response.status_code == 200:
                        dm_channel = dm_response.json()
                        print(f"📤 DM channel created: {dm_channel['id']}")
                        dm_message_response = await client.post(
                            f"https://discord.com/api/v10/channels/{dm_channel['id']}/messages",
                            headers=headers,
                            json={
                                "content": f"⚠️ You have been warned in the server.\n**Reason:** {action.reason}\n\nPlease review the server rules to avoid further actions."
                            }
                        )
                        print(f"📤 DM message response: {dm_message_response.status_code}")
                    else:
                        print(f"❌ Failed to create DM channel: {dm_response.text}")
                except Exception as e:
                    print(f"❌ Failed to send DM to user: {e}")
                
                success_message = f"User warned successfully. Reason: {action.reason}"
                log_message = f"⚠️ **Warning Issued**\n**User:** {user_info.get('username', 'Unknown')} (<@{action.user_id}>)\n**Moderator:** {moderator_info.get('username', 'Unknown')} (<@{moderator_id}>)\n**Reason:** {action.reason}"
                print(f"✅ Warning processed successfully")
            
            elif action.action == "timeout":
                if not action.duration:
                    raise HTTPException(status_code=400, detail="Duration required for timeout")
                
                # Calculate timeout end time
                timeout_end = datetime.utcnow() + timedelta(minutes=action.duration)
                
                # Apply timeout via Discord API
                timeout_response = await client.patch(
                    f"https://discord.com/api/v10/guilds/{guild_id}/members/{action.user_id}",
                    headers=headers,
                    json={
                        "communication_disabled_until": timeout_end.isoformat()
                    }
                )
                
                if timeout_response.status_code == 200:
                    # Add timeout to database
                    await database.execute(
                        """INSERT INTO timeouts (guild_id, user_id, moderator_id, duration, reason, timestamp)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (guild_id, action.user_id, moderator_id, action.duration, action.reason, datetime.utcnow())
                    )
                    
                    success_message = f"User timed out for {action.duration} minutes. Reason: {action.reason}"
                    log_message = f"🔇 **Timeout Applied**\n**User:** {user_info.get('username', 'Unknown')} (<@{action.user_id}>)\n**Moderator:** {moderator_info.get('username', 'Unknown')} (<@{moderator_id}>)\n**Duration:** {action.duration} minutes\n**Reason:** {action.reason}"
                else:
                    raise HTTPException(status_code=500, detail="Failed to apply timeout")
            
            elif action.action == "kick":
                # Kick user via Discord API
                kick_response = await client.delete(
                    f"https://discord.com/api/v10/guilds/{guild_id}/members/{action.user_id}",
                    headers=headers,
                    params={"reason": action.reason}
                )
                
                if kick_response.status_code == 204:
                    success_message = f"User kicked successfully. Reason: {action.reason}"
                    log_message = f"👢 **User Kicked**\n**User:** {user_info.get('username', 'Unknown')} (<@{action.user_id}>)\n**Moderator:** {moderator_info.get('username', 'Unknown')} (<@{moderator_id}>)\n**Reason:** {action.reason}"
                else:
                    raise HTTPException(status_code=500, detail="Failed to kick user")
            
            elif action.action == "ban":
                # Ban user via Discord API
                ban_response = await client.put(
                    f"https://discord.com/api/v10/guilds/{guild_id}/bans/{action.user_id}",
                    headers=headers,
                    json={"reason": action.reason}
                )
                
                if ban_response.status_code == 204:
                    success_message = f"User banned successfully. Reason: {action.reason}"
                    log_message = f"🔨 **User Banned**\n**User:** {user_info.get('username', 'Unknown')} (<@{action.user_id}>)\n**Moderator:** {moderator_info.get('username', 'Unknown')} (<@{moderator_id}>)\n**Reason:** {action.reason}"
                else:
                    raise HTTPException(status_code=500, detail="Failed to ban user")
            
            else:
                raise HTTPException(status_code=400, detail="Invalid moderation action")
            
            # Send log message to channel if specified
            if action.channel_id and log_message:
                try:
                    print(f"📢 Attempting to send log message to channel {action.channel_id}")
                    print(f"📢 Log message content: {repr(log_message)}")
                    
                    embed_data = {
                        "title": "Moderation Action",
                        "description": log_message,
                        "color": 0xff6b6b if action.action in ["kick", "ban"] else 0xffa500 if action.action == "timeout" else 0xffff00,
                        "timestamp": datetime.utcnow().isoformat(),
                        "footer": {
                            "text": "MaybeBot Moderation System"
                        }
                    }
                    
                    message_payload = {"embeds": [embed_data]}
                    print(f"📢 Message payload: {message_payload}")
                    
                    log_response = await client.post(
                        f"https://discord.com/api/v10/channels/{action.channel_id}/messages",
                        headers=headers,
                        json=message_payload
                    )
                    print(f"📢 Log message response: {log_response.status_code}")
                    if log_response.status_code != 200:
                        print(f"❌ Failed to send log message: {log_response.text}")
                    else:
                        print(f"✅ Log message sent successfully")
                except Exception as e:
                    print(f"❌ Failed to send log message to channel: {e}")
            else:
                print(f"ℹ️ No log channel specified or no log message to send")
                if not action.channel_id:
                    print("ℹ️ No channel_id provided")
                if not log_message:
                    print("ℹ️ No log_message generated")
            
            print(f"✅ Moderation action completed successfully: {success_message}")
            return {"message": success_message}
    
    except Exception as e:
        print(f"Moderation action error: {e}")
        import traceback
        print(f"Moderation action traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/moderation/history")
async def get_guild_moderation_history(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get recent moderation history for the guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get recent warnings
        warnings = await database.fetch_all(
            "SELECT user_id, moderator_id, reason, timestamp, 'warning' as action_type FROM warnings WHERE guild_id = %s ORDER BY timestamp DESC LIMIT 10",
            (guild_id,)
        )
        
        # Get recent timeouts
        timeouts = await database.fetch_all(
            "SELECT user_id, moderator_id, duration, reason, timestamp, 'timeout' as action_type FROM timeouts WHERE guild_id = %s ORDER BY timestamp DESC LIMIT 10",
            (guild_id,)
        )
        
        # Combine and sort by timestamp
        history = []
        for warning in warnings:
            history.append({
                "user_id": str(warning["user_id"]),  # Convert to string for JavaScript
                "moderator_id": str(warning["moderator_id"]),  # Convert to string for JavaScript
                "action_type": "warning",
                "reason": warning["reason"],
                "created_at": warning["timestamp"]
            })
        
        for timeout in timeouts:
            history.append({
                "user_id": str(timeout["user_id"]),  # Convert to string for JavaScript
                "moderator_id": str(timeout["moderator_id"]),  # Convert to string for JavaScript
                "action_type": "timeout",
                "reason": timeout["reason"],
                "duration": timeout["duration"],
                "created_at": timeout["timestamp"]
            })
        
        # Sort by timestamp (most recent first)
        history.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {"history": history[:10]}  # Return top 10 most recent
    
    except Exception as e:
        print(f"Get moderation history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/moderation/history/{user_id}")
async def get_moderation_history(
    guild_id: str,
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get moderation history for a user"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get warnings
        warnings = await database.fetch_all(
            "SELECT moderator_id, reason, timestamp FROM warnings WHERE guild_id = %s AND user_id = %s ORDER BY timestamp DESC",
            (guild_id, user_id)
        )
        
        # Get timeouts
        timeouts = await database.fetch_all(
            "SELECT moderator_id, duration, reason, timestamp FROM timeouts WHERE guild_id = %s AND user_id = %s ORDER BY timestamp DESC",
            (guild_id, user_id)
        )
        
        return {
            "warnings": [dict(warning) for warning in warnings],
            "timeouts": [dict(timeout) for timeout in timeouts]
        }
    
    except Exception as e:
        print(f"Get moderation history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Language endpoints
@app.get("/api/languages")
async def get_available_languages():
    """Get all available languages"""
    try:
        languages = []
        for lang_code in SUPPORTED_LANGUAGES:
            lang_data = load_language_file(lang_code)
            languages.append({
                "code": lang_code,
                "name": lang_data["_meta"]["name"],
                "flag": lang_data["_meta"]["flag"]
            })
        return {"languages": languages}
    except Exception as e:
        print(f"Get languages error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/language/{language_code}")
async def get_language_strings(language_code: str):
    """Get language strings for a specific language"""
    try:
        if language_code not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=404, detail="Language not found")
        
        lang_data = load_language_file(language_code)
        return lang_data
    except Exception as e:
        print(f"Get language strings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/language")
async def get_user_language_preference(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Get user's language preference"""
    try:
        # Get user ID from token
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if user has a saved language preference
        result = await database.fetch_one(
            "SELECT language_code FROM user_languages WHERE user_id = %s",
            (user_id,)
        )
        
        if result:
            return {"language": result["language_code"]}
        else:
            # Detect from browser if no preference saved
            accept_language = request.headers.get("accept-language", "")
            detected_language = detect_browser_language(accept_language)
            
            # Save the detected language as preference
            await database.execute(
                "INSERT INTO user_languages (user_id, language_code) VALUES (%s, %s) ON DUPLICATE KEY UPDATE language_code = %s",
                (user_id, detected_language, detected_language)
            )
            
            return {"language": detected_language}
    
    except Exception as e:
        print(f"Get user language error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/user/language")
async def set_user_language_preference(
    language_pref: LanguagePreference,
    current_user: str = Depends(get_current_user)
):
    """Set user's language preference"""
    try:
        # Validate language
        if language_pref.language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail="Unsupported language")
        
        # Get user ID from token
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Save language preference
        await database.execute(
            "INSERT INTO user_languages (user_id, language_code) VALUES (%s, %s) ON DUPLICATE KEY UPDATE language_code = %s",
            (user_id, language_pref.language, language_pref.language)
        )
        
        return {"message": "Language preference saved successfully"}
    
    except Exception as e:
        print(f"Set user language error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/detect-language")
async def detect_language_from_browser(request: Request):
    """Detect language from browser Accept-Language header"""
    try:
        accept_language = request.headers.get("accept-language", "")
        detected_language = detect_browser_language(accept_language)
        
        return {
            "detected_language": detected_language,
            "accept_language_header": accept_language
        }
    except Exception as e:
        print(f"Detect language error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Production server startup
if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.getenv("PORT", 8000))
    
    # Production configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Listen on all interfaces
        port=port,
        log_level="info",
        access_log=True,
        # Don't use reload in production
        reload=False
    )
