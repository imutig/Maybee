"""
Maybee Web Dashboard - Main FastAPI Application
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
import sys
import json
import asyncio
import traceback
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
    await create_welcome_config_table()
    await create_role_menu_tables()  # Add role menu tables
    await create_ticket_tables()  # Add ticket system tables
    await create_level_roles_table()  # Add level roles table
    await create_embed_config_table()  # Add embed config table
    yield
    # Shutdown
    if database:
        await database.close()

app = FastAPI(
    title="Maybee Dashboard",
    description="Professional web interface for Maybee configuration",
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

# Session middleware for storing user sessions
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-in-production"))

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

# Cache for guild access verification
guild_access_cache = {}
guild_access_cache_ttl = 300  # 5 minutes

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
    welcome_title: str = "👋 New member!"
    welcome_message: str = "Welcome {user} to {server}!"
    welcome_fields: Optional[List[dict]] = None
    goodbye_channel: Optional[str] = None
    goodbye_title: str = "👋 Departure"
    goodbye_message: str = "Goodbye {user}, we'll miss you!"
    goodbye_fields: Optional[List[dict]] = None
    auto_role_enabled: bool = False
    auto_role_ids: Optional[List[str]] = None

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
    reason: Optional[str] = "No reason provided"
    duration: Optional[int] = None  # For timeout duration in minutes
    channel_id: Optional[str] = None  # For sending log messages

# Ticket System Models
class TicketButton(BaseModel):
    id: Optional[int] = None
    button_label: str
    button_emoji: Optional[str] = None
    button_style: str = "primary"  # primary, secondary, success, danger
    category_id: Optional[str] = None
    ticket_name_format: str = "ticket-{username}"
    ping_roles: Optional[List[str]] = None
    initial_message: Optional[str] = None
    button_order: int = 0

class TicketPanel(BaseModel):
    id: Optional[int] = None
    panel_name: str
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    embed_title: str = "🎫 Support Tickets"
    embed_description: str = "Click a button below to create a support ticket"
    embed_color: str = "#5865F2"
    embed_thumbnail: Optional[str] = None
    embed_image: Optional[str] = None
    embed_footer: Optional[str] = None
    buttons: Optional[List[TicketButton]] = None

class TicketConfig(BaseModel):
    enabled: bool = False
    panels: Optional[List[TicketPanel]] = None
    reason: str = "No reason provided"
    duration: Optional[int] = None  # For timeout (in minutes)
    channel_id: Optional[str] = None  # Channel to send moderation messages to

# Embed System Models
class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool = False

class EmbedCreator(BaseModel):
    target_channel: str
    ping_role_id: Optional[str] = None
    ping_user_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: str = "#5865F2"
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    author_name: Optional[str] = None
    author_icon_url: Optional[str] = None
    author_url: Optional[str] = None
    footer_text: Optional[str] = None
    footer_icon_url: Optional[str] = None
    timestamp_enabled: bool = False
    fields: Optional[List[EmbedField]] = None

class EmbedConfig(BaseModel):
    id: Optional[int] = None
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    color: str = "#5865F2"
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    author_name: Optional[str] = None
    author_icon_url: Optional[str] = None
    author_url: Optional[str] = None
    footer_text: Optional[str] = None
    footer_icon_url: Optional[str] = None
    timestamp_enabled: bool = False
    fields: Optional[List[EmbedField]] = None

class DeployRequest(BaseModel):
    channel_id: str

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
    """Get guilds where the bot is present using Discord API"""
    try:
        if not DISCORD_BOT_TOKEN:
            print("❌ No Discord bot token available for API calls")
            return []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
            response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
            
            if response.status_code == 200:
                guilds = response.json()
                guild_ids = [str(guild['id']) for guild in guilds]
                print(f"✅ Bot guilds from Discord API: {len(guild_ids)} guilds")
                return guild_ids
            else:
                print(f"❌ Discord API error when fetching bot guilds: {response.status_code}")
                print(f"❌ Error details: {response.text}")
                # Fallback to database method
                try:
                    guilds_data = await database.query(
                        "SELECT DISTINCT guild_id FROM xp_data", 
                        fetchall=True
                    )
                    fallback_guilds = [str(guild['guild_id']) for guild in guilds_data] if guilds_data else []
                    print(f"🔄 Using fallback database method: {len(fallback_guilds)} guilds")
                    return fallback_guilds
                except Exception as db_error:
                    print(f"❌ Database fallback also failed: {db_error}")
                    return []
    except Exception as e:
        print(f"❌ Error getting bot guilds from Discord API: {e}")
        # Fallback to database method
        try:
            guilds_data = await database.query(
                "SELECT DISTINCT guild_id FROM xp_data", 
                fetchall=True
            )
            fallback_guilds = [str(guild['guild_id']) for guild in guilds_data] if guilds_data else []
            print(f"🔄 Using fallback database method: {len(fallback_guilds)} guilds")
            return fallback_guilds
        except Exception as db_error:
            print(f"❌ Database fallback also failed: {db_error}")
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
    
    async def fetch_val(query, params=None):
        """Fetch a single value from a query"""
        result = await database.query(query, params, fetchone=True)
        if result:
            # Return the first value of the first row
            return list(result.values())[0] if isinstance(result, dict) else result[0]
        return None
    
    # Bind helper methods to database object
    database.fetch_one = fetch_one
    database.fetch_all = fetch_all
    database.fetch_val = fetch_val
    # Note: execute_and_get_id is already available on the database object

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
        auto_role_enabled BOOLEAN DEFAULT FALSE,
        auto_role_ids JSON NULL,
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

async def create_welcome_config_table():
    """Create the welcome_config table if it doesn't exist"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS welcome_config (
        guild_id VARCHAR(20) PRIMARY KEY,
        welcome_channel VARCHAR(20) NULL,
        welcome_message VARCHAR(500) DEFAULT 'Welcome {user} to {server}!',
        welcome_fields JSON NULL,
        goodbye_channel VARCHAR(20) NULL,
        goodbye_message VARCHAR(500) DEFAULT 'Goodbye {user}, we will miss you!',
        goodbye_fields JSON NULL,
        auto_role_enabled BOOLEAN DEFAULT FALSE,
        auto_role_ids JSON NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    
    try:
        await database.execute(create_table_sql)
        print("✅ Welcome config table created/verified")
        
        # Check if new columns exist, add them if they don't
        await migrate_welcome_config_table()
        await migrate_auto_role_columns()
        
        return True
    except Exception as e:
        print(f"❌ Error creating welcome_config table: {e}")
        return False

async def create_role_menu_tables():
    """Create role menu tables if they don't exist"""
    role_menus_table = """
    CREATE TABLE IF NOT EXISTS role_menus (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id BIGINT NOT NULL,
        channel_id BIGINT NOT NULL,
        message_id BIGINT NULL,
        title VARCHAR(100) NOT NULL,
        description TEXT NULL,
        color VARCHAR(7) DEFAULT '#5865F2',
        placeholder VARCHAR(150) DEFAULT 'Select a role...',
        max_values INT DEFAULT 1,
        min_values INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_guild (guild_id),
        INDEX idx_channel (channel_id),
        INDEX idx_message (message_id)
    )
    """
    
    role_menu_options_table = """
    CREATE TABLE IF NOT EXISTS role_menu_options (
        id INT AUTO_INCREMENT PRIMARY KEY,
        menu_id INT NOT NULL,
        role_id BIGINT NOT NULL,
        label VARCHAR(80) NOT NULL,
        description VARCHAR(100) NULL,
        emoji VARCHAR(100) NULL,
        position INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_menu (menu_id),
        INDEX idx_role (role_id),
        INDEX idx_position (position),
        FOREIGN KEY (menu_id) REFERENCES role_menus(id) ON DELETE CASCADE
    )
    """
    
    try:
        await database.execute(role_menus_table)
        await database.execute(role_menu_options_table)
        print("✅ Role menu tables created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating role menu tables: {e}")
        return False

async def create_ticket_tables():
    """Create ticket system tables if they don't exist"""
    ticket_config_table = """
    CREATE TABLE IF NOT EXISTS ticket_config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id VARCHAR(20) NOT NULL UNIQUE,
        enabled BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_guild_id (guild_id)
    )
    """
    
    ticket_panels_table = """
    CREATE TABLE IF NOT EXISTS ticket_panels (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id VARCHAR(20) NOT NULL,
        panel_name VARCHAR(100) NOT NULL,
        channel_id VARCHAR(20),
        message_id VARCHAR(20),
        embed_title VARCHAR(256),
        embed_description TEXT,
        embed_color VARCHAR(7) DEFAULT '#5865F2',
        embed_thumbnail VARCHAR(512),
        embed_image VARCHAR(512),
        embed_footer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_guild_id (guild_id),
        INDEX idx_channel_message (channel_id, message_id)
    )
    """
    
    ticket_buttons_table = """
    CREATE TABLE IF NOT EXISTS ticket_buttons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        panel_id INT NOT NULL,
        button_label VARCHAR(80) NOT NULL,
        button_emoji VARCHAR(100),
        button_style ENUM('primary', 'secondary', 'success', 'danger') DEFAULT 'primary',
        category_id VARCHAR(20),
        ticket_name_format VARCHAR(100) DEFAULT 'ticket-{username}',
        ping_roles JSON,
        initial_message TEXT,
        button_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (panel_id) REFERENCES ticket_panels(id) ON DELETE CASCADE,
        INDEX idx_panel_id (panel_id)
    )
    """
    
    active_tickets_table = """
    CREATE TABLE IF NOT EXISTS active_tickets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id VARCHAR(20) NOT NULL,
        channel_id VARCHAR(20) NOT NULL UNIQUE,
        user_id VARCHAR(20) NOT NULL,
        button_id INT,
        panel_id INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP NULL,
        closed_by VARCHAR(20),
        FOREIGN KEY (button_id) REFERENCES ticket_buttons(id) ON DELETE SET NULL,
        FOREIGN KEY (panel_id) REFERENCES ticket_panels(id) ON DELETE SET NULL,
        INDEX idx_guild_id (guild_id),
        INDEX idx_user_id (user_id),
        INDEX idx_channel_id (channel_id)
    )
    """
    
    try:
        await database.execute(ticket_config_table)
        await database.execute(ticket_panels_table)
        await database.execute(ticket_buttons_table)
        await database.execute(active_tickets_table)
        print("✅ Ticket system tables created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating ticket system tables: {e}")
        return False

async def create_level_roles_table():
    """Create level_roles table if it doesn't exist"""
    level_roles_table = """
    CREATE TABLE IF NOT EXISTS level_roles (
        guild_id BIGINT NOT NULL,
        level INT NOT NULL,
        role_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (guild_id, level),
        INDEX idx_guild_level (guild_id, level),
        INDEX idx_role (role_id)
    )
    """
    
    try:
        await database.execute(level_roles_table)
        print("✅ Level roles table created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating level_roles table: {e}")
        return False

async def create_embed_config_table():
    """Create the embed_config table for storing custom embed configurations"""
    embed_config_table = """
    CREATE TABLE IF NOT EXISTS embed_config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id BIGINT NOT NULL,
        name VARCHAR(100) NOT NULL,
        title VARCHAR(256),
        description TEXT,
        color VARCHAR(7) DEFAULT '#5865F2',
        thumbnail_url VARCHAR(512),
        image_url VARCHAR(512),
        author_name VARCHAR(256),
        author_icon_url VARCHAR(512),
        author_url VARCHAR(512),
        footer_text VARCHAR(2048),
        footer_icon_url VARCHAR(512),
        timestamp_enabled BOOLEAN DEFAULT FALSE,
        fields JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_guild_id (guild_id),
        INDEX idx_name (guild_id, name)
    )
    """
    
    try:
        await database.execute(embed_config_table)
        print("✅ Embed config table created/verified")
        return True
    except Exception as e:
        print(f"❌ Error creating embed_config table: {e}")
        return False

async def migrate_welcome_config_table():
    """Add missing columns to existing welcome_config table"""
    try:
        # Check if welcome_fields column exists
        check_query = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'welcome_config' 
        AND COLUMN_NAME = 'welcome_fields'
        """
        
        result = await database.fetch_one(check_query)
        
        if not result:
            print("🔧 Adding welcome_fields column to welcome_config table...")
            await database.execute("""
                ALTER TABLE welcome_config 
                ADD COLUMN welcome_fields JSON NULL AFTER welcome_message
            """)
            print("✅ Added welcome_fields column")
        
        # Check if goodbye_fields column exists
        check_query2 = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'welcome_config' 
        AND COLUMN_NAME = 'goodbye_fields'
        """
        
        result2 = await database.fetch_one(check_query2)
        
        if not result2:
            print("🔧 Adding goodbye_fields column to welcome_config table...")
            await database.execute("""
                ALTER TABLE welcome_config 
                ADD COLUMN goodbye_fields JSON NULL AFTER goodbye_message
            """)
            print("✅ Added goodbye_fields column")
            
    except Exception as e:
        print(f"⚠️ Migration error (this may be normal if columns already exist): {e}")

async def migrate_auto_role_columns():
    """Add auto-role columns to welcome_config and guild_config tables"""
    try:
        # Check if auto_role_enabled column exists in welcome_config
        check_query = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'welcome_config' 
        AND COLUMN_NAME = 'auto_role_enabled'
        """
        
        result = await database.fetch_one(check_query)
        
        if not result:
            print("🔧 Adding auto_role_enabled column to welcome_config table...")
            await database.execute("""
                ALTER TABLE welcome_config 
                ADD COLUMN auto_role_enabled BOOLEAN DEFAULT FALSE AFTER goodbye_fields
            """)
            print("✅ Added auto_role_enabled column")
        
        # Check if auto_role_ids column exists in welcome_config
        check_query2 = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'welcome_config' 
        AND COLUMN_NAME = 'auto_role_ids'
        """
        
        result2 = await database.fetch_one(check_query2)
        
        if not result2:
            print("🔧 Adding auto_role_ids column to welcome_config table...")
            await database.execute("""
                ALTER TABLE welcome_config 
                ADD COLUMN auto_role_ids JSON NULL AFTER auto_role_enabled
            """)
            print("✅ Added auto_role_ids column")
            
        # Check if auto_role_enabled column exists in guild_config
        check_query3 = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'guild_config' 
        AND COLUMN_NAME = 'auto_role_enabled'
        """
        
        result3 = await database.fetch_one(check_query3)
        
        if not result3:
            print("🔧 Adding auto_role_enabled column to guild_config table...")
            await database.execute("""
                ALTER TABLE guild_config 
                ADD COLUMN auto_role_enabled BOOLEAN DEFAULT FALSE AFTER welcome_message
            """)
            print("✅ Added auto_role_enabled column to guild_config")
        
        # Check if auto_role_ids column exists in guild_config
        check_query4 = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'guild_config' 
        AND COLUMN_NAME = 'auto_role_ids'
        """
        
        result4 = await database.fetch_one(check_query4)
        
        if not result4:
            print("🔧 Adding auto_role_ids column to guild_config table...")
            await database.execute("""
                ALTER TABLE guild_config 
                ADD COLUMN auto_role_ids JSON NULL AFTER auto_role_enabled
            """)
            print("✅ Added auto_role_ids column to guild_config")
            
    except Exception as e:
        print(f"⚠️ Auto-role migration error (this may be normal if columns already exist): {e}")

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    # Detect language from query parameter, cookie, or browser
    lang = request.query_params.get('lang')
    if not lang:
        lang = request.cookies.get('language')
    if not lang:
        accept_language = request.headers.get('accept-language', '')
        lang = detect_browser_language(accept_language)
    
    # Ensure language is supported
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # Load language data
    lang_data = load_language_file(lang)
    
    # Create response with language data
    response = templates.TemplateResponse("index.html", {
        "request": request,
        "lang_data": lang_data,
        "current_lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES
    })
    
    # Set language cookie if it was changed via query parameter
    if request.query_params.get('lang'):
        response.set_cookie("language", lang, max_age=365*24*60*60)  # 1 year
    
    return response

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
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new_values
               ON DUPLICATE KEY UPDATE
               xp_enabled = new_values.xp_enabled,
               xp_multiplier = new_values.xp_multiplier,
               level_up_message = new_values.level_up_message,
               level_up_channel = new_values.level_up_channel,
               moderation_enabled = new_values.moderation_enabled,
               welcome_enabled = new_values.welcome_enabled,
               welcome_channel = new_values.welcome_channel,
               welcome_message = new_values.welcome_message,
               logs_enabled = new_values.logs_enabled,
               logs_channel = new_values.logs_channel,
               updated_at = new_values.updated_at""",
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
        xp_member_count = await database.fetch_one(
            "SELECT COUNT(*) as count FROM xp_data WHERE guild_id = %s",
            (guild_id,)
        )
        xp_members = xp_member_count["count"] if xp_member_count else 0
        
        # Try to get total server members from Discord API (fallback to XP members)
        try:
            bot_token = DISCORD_BOT_TOKEN.strip() if DISCORD_BOT_TOKEN else None
            if bot_token:
                headers = {"Authorization": f"Bot {bot_token}"}
                async with httpx.AsyncClient(timeout=8.0) as client:
                    # Get actual members list to count real members (more accurate than guild.member_count)
                    response = await client.get(f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000", headers=headers)
                    if response.status_code == 200:
                        members = response.json()
                        # Filter out bots to get real member count
                        real_members = [m for m in members if not m.get("user", {}).get("bot", False)]
                        stats["total_members"] = len(real_members)
                    else:
                        stats["total_members"] = xp_members
            else:
                stats["total_members"] = xp_members
        except Exception:
            stats["total_members"] = xp_members
        
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
        try:
            recent_activity = await database.fetch_one(
                "SELECT COUNT(*) as count FROM xp_history WHERE guild_id = %s AND timestamp >= %s",
                (guild_id, week_ago)
            )
            if recent_activity and recent_activity["count"] is not None:
                stats["recent_activity"] = recent_activity["count"]
            else:
                # Fallback: check recent updates in xp_data table
                fallback_activity = await database.fetch_one(
                    "SELECT COUNT(*) as count FROM xp_data WHERE guild_id = %s AND updated_at >= %s",
                    (guild_id, week_ago)
                )
                stats["recent_activity"] = fallback_activity["count"] if fallback_activity else 0
        except Exception:
            stats["recent_activity"] = 0
        
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
                original_id = user_dict["user_id"]
                user_dict["user_id"] = str(user_dict["user_id"])  # Convert to string for JavaScript
                print(f"🔍 User ID conversion: {original_id} -> {user_dict['user_id']} (type: {type(user_dict['user_id'])})")
                stats["top_users"].append(user_dict)
        
        print(f"🔍 Final top_users before JSON response: {stats['top_users']}")
        import json
        from fastapi import Response
        return Response(content=json.dumps(stats, default=str, ensure_ascii=False), media_type="application/json")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/bulk")
async def get_guild_bulk_data(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get multiple guild data in one request to reduce API calls"""
    try:
        # Verify user has access to this guild (cached)
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        print(f"🔄 Loading bulk data for guild {guild_id}")
        
        # Load all data in parallel
        async def get_config():
            try:
                config_data = await database.fetch_one("SELECT * FROM guild_config WHERE guild_id = %s", (guild_id,))
                xp_config_data = await database.fetch_one("SELECT * FROM xp_config WHERE guild_id = %s", (guild_id,))
                default_config = {
                    "guild_id": guild_id,
                    "xp_enabled": True,
                    "xp_multiplier": 1.0,
                    "level_up_message": True,
                    "level_up_channel": None,
                    "xp_channel": None
                }
                if config_data:
                    default_config.update(dict(config_data))
                if xp_config_data:
                    default_config["xp_channel"] = str(xp_config_data[1]) if xp_config_data[1] else None
                return default_config
            except Exception as e:
                print(f"Bulk config error: {e}")
                return {"guild_id": guild_id, "xp_enabled": True}
        
        async def get_channels():
            try:
                bot_token = DISCORD_BOT_TOKEN.strip()
                headers = {"Authorization": f"Bot {bot_token}"}
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers)
                    if response.status_code == 200:
                        channels = response.json()
                        text_channels = [{"id": ch["id"], "name": ch["name"]} for ch in channels if ch["type"] == 0]
                        return text_channels
                return []
            except Exception as e:
                print(f"Bulk channels error: {e}")
                return []
        
        async def get_stats():
            try:
                print(f"🔍 Getting stats for guild_id: {guild_id}")
                
                # Get XP-active members count (users who have earned XP)
                xp_members = await database.fetch_val("SELECT COUNT(DISTINCT user_id) FROM xp_data WHERE guild_id = %s", (guild_id,))
                print(f"📊 XP-active members query result: {xp_members}")
                
                # Try to get total server members from Discord API (fallback to XP members if API fails)
                try:
                    bot_token = DISCORD_BOT_TOKEN.strip()
                    headers = {"Authorization": f"Bot {bot_token}"}
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        # Get actual members list to count real members (more accurate than guild.member_count)
                        response = await client.get(f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000", headers=headers)
                        if response.status_code == 200:
                            members = response.json()
                            # Filter out bots to get real member count
                            real_members = [m for m in members if not m.get("user", {}).get("bot", False)]
                            total_members = len(real_members)
                            print(f"📊 Total server members from Discord members API: {total_members} (fetched {len(members)} total, {len(real_members)} non-bot)")
                        else:
                            total_members = xp_members
                            print(f"📊 Discord members API failed, using XP members: {total_members}")
                except Exception as api_error:
                    total_members = xp_members
                    print(f"📊 Discord API failed, using XP members: {total_members} - Error: {api_error}")
                
                total_xp = await database.fetch_val("SELECT COALESCE(SUM(xp), 0) FROM xp_data WHERE guild_id = %s", (guild_id,))
                print(f"📊 Total XP query result: {total_xp}")
                
                avg_level = await database.fetch_val("SELECT COALESCE(AVG(level), 0) FROM xp_data WHERE guild_id = %s", (guild_id,))
                print(f"📊 Average level query result: {avg_level}")
                
                # Check for recent activity in xp_history table first, fallback to xp_data updates
                week_ago = datetime.utcnow() - timedelta(days=7)
                try:
                    recent_activity = await database.fetch_val(
                        "SELECT COUNT(*) FROM xp_history WHERE guild_id = %s AND timestamp >= %s", 
                        (guild_id, week_ago)
                    )
                    if recent_activity is None:
                        # Fallback: check recent updates in xp_data table
                        recent_activity = await database.fetch_val(
                            "SELECT COUNT(*) FROM xp_data WHERE guild_id = %s AND updated_at >= %s", 
                            (guild_id, week_ago)
                        )
                        print(f"📊 Recent activity (from xp_data updates): {recent_activity}")
                    else:
                        print(f"📊 Recent activity (from xp_history): {recent_activity}")
                except Exception as activity_error:
                    recent_activity = 0
                    print(f"📊 Recent activity query failed: {activity_error}")
                
                top_users = await database.fetch_all("SELECT user_id, xp, level FROM xp_data WHERE guild_id = %s ORDER BY xp DESC LIMIT 5", (guild_id,))
                print(f"📊 Top users query result: {top_users}")
                
                # Convert top_users to ensure user_id is string for JavaScript compatibility
                top_users_list = []
                for user in (top_users or []):
                    user_dict = dict(user)
                    user_dict["user_id"] = str(user_dict["user_id"])  # Force conversion to string
                    top_users_list.append(user_dict)
                print(f"📊 Top users converted to strings: {top_users_list}")
                
                # Debug info
                total_rows = await database.fetch_val("SELECT COUNT(*) FROM xp_data")
                print(f"📊 Total rows in xp_data table: {total_rows}")
                guild_rows = await database.fetch_val("SELECT COUNT(*) FROM xp_data WHERE guild_id = %s", (guild_id,))
                print(f"📊 XP data rows for guild {guild_id}: {guild_rows}")
                
                return {
                    "total_members": total_members or 0,
                    "total_xp": total_xp or 0,
                    "average_level": round(avg_level, 1) if avg_level else 0,
                    "recent_activity": recent_activity or 0,
                    "top_users": top_users_list
                }
            except Exception as e:
                print(f"Bulk stats error: {e}")
                return {"total_members": 0, "total_xp": 0, "average_level": 0, "recent_activity": 0, "top_users": []}
        
        async def get_level_roles():
            try:
                level_roles = await database.fetch_all(
                    "SELECT guild_id, level, role_id FROM level_roles WHERE guild_id = %s ORDER BY level ASC",
                    (guild_id,)
                )
                # Convert role_id to string for JavaScript compatibility
                result = []
                for lr in (level_roles or []):
                    lr_dict = dict(lr)
                    lr_dict["role_id"] = str(lr_dict["role_id"])
                    result.append(lr_dict)
                return result
            except Exception as e:
                print(f"Bulk level roles error: {e}")
                return []
        
        # Execute all requests in parallel
        config_task = get_config()
        channels_task = get_channels()
        stats_task = get_stats()
        level_roles_task = get_level_roles()
        
        config, channels, stats, level_roles = await asyncio.gather(config_task, channels_task, stats_task, level_roles_task, return_exceptions=True)
        
        # Handle any exceptions
        if isinstance(config, Exception):
            config = {"guild_id": guild_id, "xp_enabled": True}
        if isinstance(channels, Exception):
            channels = []
        if isinstance(stats, Exception):
            stats = {"total_members": 0, "total_xp": 0, "average_level": 0, "recent_activity": 0, "top_users": []}
        if isinstance(level_roles, Exception):
            level_roles = []
        
        print(f"✅ Bulk data loaded: {len(channels)} channels, {stats['total_members']} members, {len(level_roles)} level roles")
        
        return {
            "config": config,
            "channels": channels,
            "stats": stats,
            "level_roles": level_roles
        }
        
    except Exception as e:
        print(f"Bulk data error: {e}")
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

@app.get("/api/guild/{guild_id}/categories")
async def get_guild_categories(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get guild categories for ticket configuration"""
    try:
        print(f"Fetching categories for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get bot token
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            print("❌ No bot token available")
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        # Clean the token
        bot_token = bot_token.strip()
        if '=' in bot_token and 'DISCORD_TOKEN=' in bot_token:
            bot_token = bot_token.split('=', 1)[1]
        
        # Try to get Discord guild channels via bot token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://discord.com/api/guilds/{guild_id}/channels",
                headers={"Authorization": f"Bot {bot_token}"}
            )
            
            print(f"Discord API response status: {response.status_code}")
            if response.status_code == 200:
                channels = response.json()
                print(f"Total channels found: {len(channels)}")
                # Filter to category channels only (type 4)
                categories = [
                    {"id": ch["id"], "name": ch["name"]} 
                    for ch in channels 
                    if ch["type"] == 4  # Category channel
                ]
                print(f"Categories found: {len(categories)}")
                return categories
            else:
                print(f"Discord API error: {response.text}")
                # Fallback to mock categories if API fails
                return [
                    {"id": "1234567890123456795", "name": "Support"},
                    {"id": "1234567890123456796", "name": "Tickets"},
                    {"id": "1234567890123456797", "name": "Admin"}
                ]
                
    except Exception as e:
        print(f"Error fetching categories: {e}")
        # Return mock categories as fallback
        return [
            {"id": "1234567890123456795", "name": "Support"},
            {"id": "1234567890123456796", "name": "Tickets"},
            {"id": "1234567890123456797", "name": "Admin"}
        ]

@app.get("/api/guild/{guild_id}/roles")
async def get_guild_roles(guild_id: str, current_user: str = Depends(get_current_user)):
    """Get guild roles for configuration"""
    try:
        print(f"Fetching roles for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get bot token
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            print("❌ No bot token available")
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        # Clean the token
        bot_token = bot_token.strip()
        if '=' in bot_token and 'DISCORD_TOKEN=' in bot_token:
            bot_token = bot_token.split('=', 1)[1]
        
        # Try to get Discord guild roles via bot token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://discord.com/api/guilds/{guild_id}/roles",
                headers={"Authorization": f"Bot {bot_token}"}
            )
            
            print(f"Discord API response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Discord API error: {response.text}")
            
            if response.status_code == 200:
                roles = response.json()
                print(f"Total roles found: {len(roles)}")
                
                # Filter and format roles (exclude @everyone, sort by position)
                filtered_roles = [
                    {
                        "id": role["id"], 
                        "name": role["name"],
                        "color": role["color"],
                        "position": role["position"],
                        "managed": role["managed"]
                    } 
                    for role in roles 
                    if role["name"] != "@everyone"
                ]
                
                # Sort by position (higher position = higher in hierarchy)
                filtered_roles.sort(key=lambda x: x["position"], reverse=True)
                
                print(f"Filtered roles found: {len(filtered_roles)}")
                return {"roles": filtered_roles}
            else:
                # Fallback to mock roles if API fails
                print("Using fallback mock roles due to API error")
                return {
                    "roles": [
                        {"id": "1234567890123456801", "name": "Admin", "color": 16711680, "position": 10, "managed": False},
                        {"id": "1234567890123456802", "name": "Moderator", "color": 3447003, "position": 9, "managed": False},
                        {"id": "1234567890123456803", "name": "Member", "color": 0, "position": 1, "managed": False},
                        {"id": "1234567890123456804", "name": "New Member", "color": 65280, "position": 0, "managed": False}
                    ]
                }
                
    except Exception as e:
        print(f"Error fetching roles: {e}")
        # Return mock roles as fallback
        return {
            "roles": [
                {"id": "1234567890123456801", "name": "Admin", "color": 16711680, "position": 10, "managed": False},
                {"id": "1234567890123456802", "name": "Moderator", "color": 3447003, "position": 9, "managed": False},
                {"id": "1234567890123456803", "name": "Member", "color": 0, "position": 1, "managed": False},
                {"id": "1234567890123456804", "name": "New Member", "color": 65280, "position": 0, "managed": False}
            ]
        }

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
                   VALUES (%s, %s) AS new_values
                   ON DUPLICATE KEY UPDATE xp_channel = new_values.xp_channel""",
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
               VALUES (%s, %s, %s, %s, %s, TRUE, FALSE, NULL, 'Welcome {user} to {server}!', FALSE, NULL, %s) AS new_values
               ON DUPLICATE KEY UPDATE
               xp_enabled = new_values.xp_enabled,
               xp_multiplier = new_values.xp_multiplier,
               level_up_message = new_values.level_up_message,
               level_up_channel = new_values.level_up_channel,
               updated_at = new_values.updated_at""",
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

@app.post("/api/guild/{guild_id}/xp/reset")
async def reset_server_xp(
    guild_id: str, 
    current_user: str = Depends(get_current_user)
):
    """Reset all XP data for a server"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get count before deletion for feedback
        count_result = await database.fetch_one(
            'SELECT COUNT(*) as count FROM xp_data WHERE guild_id = %s', 
            (guild_id,)
        )
        count = count_result['count'] if count_result else 0
        
        # Delete all XP-related data for the guild
        await database.execute('DELETE FROM xp_data WHERE guild_id = %s', (guild_id,))
        await database.execute('DELETE FROM xp_history WHERE guild_id = %s', (guild_id,))
        await database.execute('DELETE FROM level_roles WHERE guild_id = %s', (guild_id,))
        await database.execute('DELETE FROM xp_multipliers WHERE guild_id = %s', (guild_id,))
        
        return {
            "success": True,
            "message": f"Successfully reset XP data for guild {guild_id}",
            "deleted_records": count
        }
        
    except Exception as e:
        print(f"Reset XP error: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"Reset XP traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Level Roles API Endpoints
@app.get("/api/guild/{guild_id}/level-roles")
async def get_level_roles(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get all level roles for a guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get level roles from database
        level_roles = await database.fetch_all(
            "SELECT guild_id, level, role_id FROM level_roles WHERE guild_id = %s ORDER BY level ASC",
            (guild_id,)
        )
        
        return {"level_roles": level_roles}
        
    except Exception as e:
        print(f"Get level roles error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/level-roles")
async def create_level_role(
    guild_id: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Create a new level role"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        level = int(request.get("level"))
        role_id = int(request.get("role_id"))
        
        if level < 1:
            raise HTTPException(status_code=400, detail="Level must be 1 or higher")
        
        # Insert or update level role
        await database.execute(
            """INSERT INTO level_roles (guild_id, level, role_id)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE role_id = VALUES(role_id)""",
            (guild_id, level, role_id)
        )
        
        return {"success": True, "message": "Level role created successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid level or role_id format")
    except Exception as e:
        print(f"Create level role error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/level-roles/{level}")
async def update_level_role(
    guild_id: str,
    level: int,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Update an existing level role"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        new_level = int(request.get("level"))
        role_id = int(request.get("role_id"))
        
        if new_level < 1:
            raise HTTPException(status_code=400, detail="Level must be 1 or higher")
        
        # Check if level role exists
        existing = await database.fetch_one(
            "SELECT level FROM level_roles WHERE guild_id = %s AND level = %s",
            (guild_id, level)
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail="Level role not found")
        
        # Delete old entry and create new one if level changed
        if new_level != level:
            await database.execute(
                "DELETE FROM level_roles WHERE guild_id = %s AND level = %s",
                (guild_id, level)
            )
            await database.execute(
                """INSERT INTO level_roles (guild_id, level, role_id)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE role_id = VALUES(role_id)""",
                (guild_id, new_level, role_id)
            )
        else:
            # Just update the role_id
            await database.execute(
                "UPDATE level_roles SET role_id = %s WHERE guild_id = %s AND level = %s",
                (role_id, guild_id, level)
            )
        
        return {"success": True, "message": "Level role updated successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid level or role_id format")
    except Exception as e:
        print(f"Update level role error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/guild/{guild_id}/level-roles/{level}")
async def delete_level_role(
    guild_id: str,
    level: int,
    current_user: str = Depends(get_current_user)
):
    """Delete a level role"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Check if level role exists
        existing = await database.fetch_one(
            "SELECT level FROM level_roles WHERE guild_id = %s AND level = %s",
            (guild_id, level)
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail="Level role not found")
        
        # Delete level role
        await database.execute(
            "DELETE FROM level_roles WHERE guild_id = %s AND level = %s",
            (guild_id, level)
        )
        
        return {"success": True, "message": "Level role deleted successfully"}
        
    except Exception as e:
        print(f"Delete level role error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/level-roles/sync")
async def sync_level_roles(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Sync level roles for all users (retroactive assignment with highest role only)"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get all level roles for this guild
        level_roles = await database.fetch_all(
            "SELECT level, role_id FROM level_roles WHERE guild_id = %s ORDER BY level DESC",
            (guild_id,)
        )
        
        if not level_roles:
            return {"success": True, "message": "No level roles configured", "updated_users": 0}
        
        # Get all users with XP in this guild
        users = await database.fetch_all(
            "SELECT user_id, level FROM xp_data WHERE guild_id = %s AND level > 0",
            (guild_id,)
        )
        
        if not users:
            return {"success": True, "message": "No users with XP found", "updated_users": 0}
        
        # For now, return information about what would be synced
        # The actual sync should be done using the Discord bot command /synclevelroles
        user_updates = {}
        for user_row in users:
            user_id = user_row["user_id"]
            user_level = user_row["level"]
            
            # Find the highest level role this user should have
            highest_role_level = 0
            highest_role_id = None
            
            for role_row in level_roles:
                role_level = role_row["level"]
                role_id = role_row["role_id"]
                
                if user_level >= role_level and role_level > highest_role_level:
                    highest_role_level = role_level
                    highest_role_id = role_id
            
            if highest_role_id:
                user_updates[str(user_id)] = {
                    "current_level": user_level,
                    "highest_role_level": highest_role_level,
                    "highest_role_id": highest_role_id
                }
        
        return {
            "success": True,
            "message": f"Sync analysis completed. Use Discord command '/synclevelroles confirm:CONFIRM' to perform the actual sync.",
            "analysis": {
                "total_users": len(users),
                "users_to_update": len(user_updates),
                "level_roles_configured": len(level_roles)
            },
            "note": "To perform the actual role sync, use the Discord slash command '/synclevelroles confirm:CONFIRM' in your server."
        }
        
    except Exception as e:
        print(f"Sync level roles analysis error: {e}")
        import traceback
        print(f"Sync traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Role Menu Endpoints
@app.get("/api/guild/{guild_id}/role-menus")
async def get_role_menus(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get all role menus for a guild"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get all role menus for the guild (without guild_channels table)
        menus = await database.fetch_all(
            """SELECT rm.*, 
                      COUNT(rmo.id) as options_count
               FROM role_menus rm 
               LEFT JOIN role_menu_options rmo ON rm.id = rmo.menu_id
               WHERE rm.guild_id = %s 
               GROUP BY rm.id 
               ORDER BY rm.created_at DESC""",
            (guild_id,)
        )
        
        # Get channel names from Discord API
        channels_map = {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://discord.com/api/guilds/{guild_id}/channels",
                    headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
                )
                if response.status_code == 200:
                    channels = response.json()
                    channels_map = {ch["id"]: ch["name"] for ch in channels}
        except Exception as e:
            print(f"Error fetching channel names: {e}")
        
        # Add channel names to menus
        result_menus = []
        for menu in menus:
            menu_dict = dict(menu)
            menu_dict['channel_name'] = channels_map.get(str(menu_dict['channel_id']), 'Unknown Channel')
            result_menus.append(menu_dict)
        
        return {"menus": result_menus}
        
    except Exception as e:
        print(f"Get role menus error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/role-menus/{menu_id}")
async def get_role_menu(
    guild_id: str,
    menu_id: int,
    current_user: str = Depends(get_current_user)
):
    """Get a specific role menu with its options"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get menu
        menu = await database.fetch_one(
            "SELECT * FROM role_menus WHERE id = %s AND guild_id = %s",
            (menu_id, guild_id)
        )
        
        if not menu:
            raise HTTPException(status_code=404, detail="Role menu not found")
        
        # Get options
        options = await database.fetch_all(
            "SELECT * FROM role_menu_options WHERE menu_id = %s ORDER BY position",
            (menu_id,)
        )
        
        menu_dict = dict(menu)
        menu_dict['options'] = options
        
        return {"menu": menu_dict}
        
    except Exception as e:
        print(f"Get role menu error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/role-menus")
async def create_role_menu(
    guild_id: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Create a new role menu"""
    try:
        print(f"🔍 DEBUG: Creating role menu for guild {guild_id}")
        print(f"🔍 DEBUG: Request data: {request}")
        
        if not await verify_guild_access(guild_id, current_user):
            print(f"❌ DEBUG: Guild access denied for guild {guild_id}")
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        print(f"✅ DEBUG: Guild access verified for guild {guild_id}")
        
        menu_data = request.get("menu", {})
        options_data = request.get("options", [])
        
        print(f"🔍 DEBUG: Menu data: {menu_data}")
        print(f"🔍 DEBUG: Options data: {options_data}")
        
        # Validate required fields
        if not menu_data.get("title") or not menu_data.get("channel_id"):
            raise HTTPException(status_code=400, detail="Title and channel are required")
        
        if not options_data:
            raise HTTPException(status_code=400, detail="At least one role option is required")
        
        # Create menu (note: MySQL doesn't support RETURNING, so we'll get the ID after insert)
        await database.execute(
            """INSERT INTO role_menus 
               (guild_id, channel_id, title, description, color, placeholder, max_values, min_values)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                guild_id,
                menu_data["channel_id"],
                menu_data["title"],
                menu_data.get("description"),
                menu_data.get("color", "#5865F2"),
                menu_data.get("placeholder", "Select a role..."),
                menu_data.get("max_values", 1),  # Use value from form
                menu_data.get("min_values", 0)   # Use value from form
            )
        )
        
        # Get the menu ID that was just inserted
        menu_result = await database.query(
            "SELECT id FROM role_menus WHERE guild_id = %s ORDER BY id DESC LIMIT 1",
            (guild_id,),
            fetchone=True
        )
        menu_id = menu_result['id']
        
        # Create options
        for option in options_data:
            await database.execute(
                """INSERT INTO role_menu_options 
                   (menu_id, role_id, label, description, emoji, position)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    menu_id,
                    option["role_id"],
                    option["label"],
                    option.get("description"),
                    option.get("emoji"),
                    option.get("position", 0)
                )
            )
        
        # Trigger bot to create/update the message
        await notify_bot_role_menu_update(guild_id, menu_id)
        
        return {"success": True, "menu_id": menu_id}
        
    except Exception as e:
        print(f"Create role menu error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/role-menus/{menu_id}")
async def update_role_menu(
    guild_id: str,
    menu_id: int,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Update an existing role menu"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        menu_data = request.get("menu", {})
        options_data = request.get("options", [])
        
        # Validate menu exists
        existing_menu = await database.fetch_one(
            "SELECT * FROM role_menus WHERE id = %s AND guild_id = %s",
            (menu_id, guild_id)
        )
        
        if not existing_menu:
            raise HTTPException(status_code=404, detail="Role menu not found")
        
        # Update menu
        await database.execute(
            """UPDATE role_menus 
               SET title = %s, description = %s, color = %s, placeholder = %s, 
                   channel_id = %s, min_values = %s, max_values = %s, updated_at = %s
               WHERE id = %s""",
            (
                menu_data.get("title", existing_menu["title"]),
                menu_data.get("description", existing_menu["description"]),
                menu_data.get("color", existing_menu["color"]),
                menu_data.get("placeholder", existing_menu["placeholder"]),
                menu_data.get("channel_id", existing_menu["channel_id"]),
                menu_data.get("min_values", existing_menu.get("min_values", 0)),
                menu_data.get("max_values", existing_menu.get("max_values", 1)),
                datetime.utcnow(),
                menu_id
            )
        )
        
        # Delete existing options
        await database.execute(
            "DELETE FROM role_menu_options WHERE menu_id = %s",
            (menu_id,)
        )
        
        # Create new options
        for option in options_data:
            await database.execute(
                """INSERT INTO role_menu_options 
                   (menu_id, role_id, label, description, emoji, position)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    menu_id,
                    option["role_id"],
                    option["label"],
                    option.get("description"),
                    option.get("emoji"),
                    option.get("position", 0)
                )
            )
        
        # Trigger bot to update the message
        await notify_bot_role_menu_update(guild_id, menu_id)
        
        return {"success": True}
        
    except Exception as e:
        print(f"Update role menu error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/guild/{guild_id}/role-menus/{menu_id}")
async def delete_role_menu(
    guild_id: str,
    menu_id: int,
    current_user: str = Depends(get_current_user)
):
    """Delete a role menu"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get menu to check message_id for deletion
        menu = await database.fetch_one(
            "SELECT * FROM role_menus WHERE id = %s AND guild_id = %s",
            (menu_id, guild_id)
        )
        
        if not menu:
            raise HTTPException(status_code=404, detail="Role menu not found")
        
        # Delete menu (options will be deleted automatically due to CASCADE)
        await database.execute(
            "DELETE FROM role_menus WHERE id = %s",
            (menu_id,)
        )
        
        # Trigger bot to delete the message
        if menu["message_id"]:
            await notify_bot_role_menu_delete(guild_id, menu["channel_id"], menu["message_id"])
        
        return {"success": True}
        
    except Exception as e:
        print(f"Delete role menu error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/roles")
async def get_guild_roles(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get roles for a guild"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Try to get roles from Discord API
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
            response = await client.get(
                f"https://discord.com/api/v10/guilds/{guild_id}/roles",
                headers=headers
            )
            
            if response.status_code == 200:
                roles = response.json()
                # Convert role IDs to strings for JavaScript compatibility
                for role in roles:
                    role["id"] = str(role["id"])
                # Sort roles by position (higher position = higher in hierarchy)
                roles.sort(key=lambda r: r.get('position', 0), reverse=True)
                return {"roles": roles}
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch roles from Discord")
                
    except Exception as e:
        print(f"Get guild roles error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def notify_bot_role_menu_update(guild_id: str, menu_id: int):
    """Role menu created - bot will automatically detect and create Discord message"""
    try:
        print(f"✅ Role menu {menu_id} created for guild {guild_id}")
        print(f"🤖 Bot will automatically create Discord message within 30 seconds")
        
        # Try to trigger immediate creation by updating the menu to have a NULL message_id
        # This will make the bot's check_new_role_menus task pick it up immediately
        try:
            await database.execute(
                "UPDATE role_menus SET message_id = NULL WHERE id = %s",
                (menu_id,)
            )
            print(f"🔄 Triggered immediate message creation for role menu {menu_id}")
        except Exception as db_error:
            print(f"⚠️ Could not trigger immediate creation: {db_error}")
        
        return True
        
    except Exception as e:
        print(f"Error in notify_bot_role_menu_update: {e}")
        return False

@app.post("/api/guild/{guild_id}/role-menus/{menu_id}/send")
async def send_role_menu_message(
    guild_id: str,
    menu_id: int,
    current_user: str = Depends(get_current_user)
):
    """Send role menu message to Discord channel"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get menu data
        menu = await database.fetch_one(
            "SELECT * FROM role_menus WHERE id = %s AND guild_id = %s",
            (menu_id, guild_id)
        )
        
        if not menu:
            raise HTTPException(status_code=404, detail="Role menu not found")
        
        # Get options
        options = await database.fetch_all(
            "SELECT * FROM role_menu_options WHERE menu_id = %s ORDER BY position",
            (menu_id,)
        )
        
        if not options:
            raise HTTPException(status_code=400, detail="Role menu has no options")
        
        # Create the Discord message directly using Discord API
        import httpx
        import json
        
        # Build the select menu options
        select_options = []
        for option in options:
            select_option = {
                "label": option["label"],
                "value": str(option["role_id"]),
                "description": option.get("description"),
            }
            if option.get("emoji"):
                select_option["emoji"] = {"name": option["emoji"]}
            select_options.append(select_option)
        
        # Create the embed
        embed = {
            "title": menu["title"],
            "description": menu.get("description", ""),
            "color": int(menu.get("color", "#5865F2").replace("#", ""), 16),
            "footer": {"text": "Role Menu"}
        }
        
        # Create the select menu component
        select_menu = {
            "type": 1,  # Action Row
            "components": [{
                "type": 3,  # Select Menu
                "custom_id": f"role_menu_{menu_id}",
                "placeholder": menu.get("placeholder", "Select a role..."),
                "min_values": menu.get("min_values", 0),
                "max_values": menu.get("max_values", 1),
                "options": select_options
            }]
        }
        
        # Send the message to Discord
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "embeds": [embed],
                "components": [select_menu]
            }
            
            response = await client.post(
                f"https://discord.com/api/v10/channels/{menu['channel_id']}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                message_data = response.json()
                message_id = message_data["id"]
                
                # Update the database with the message ID
                await database.execute(
                    "UPDATE role_menus SET message_id = %s WHERE id = %s",
                    (message_id, menu_id)
                )
                
                print(f"✅ Created Discord message {message_id} for role menu {menu_id}")
                return {"success": True, "message": f"Role menu message sent to Discord channel successfully! Message ID: {message_id}"}
            else:
                error_msg = f"Discord API error: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
        
    except Exception as e:
        print(f"Send role menu message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/role-menus/{menu_id}/status")
async def get_role_menu_status(
    guild_id: str,
    menu_id: int,
    current_user: str = Depends(get_current_user)
):
    """Check the status of a role menu"""
    try:
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get menu data
        menu = await database.fetch_one(
            "SELECT * FROM role_menus WHERE id = %s AND guild_id = %s",
            (menu_id, guild_id)
        )
        
        if not menu:
            raise HTTPException(status_code=404, detail="Role menu not found")
        
        # Get options count
        options_count = await database.fetch_one(
            "SELECT COUNT(*) as count FROM role_menu_options WHERE menu_id = %s",
            (menu_id,)
        )
        
        status = {
            "id": menu["id"],
            "title": menu["title"],
            "channel_id": menu["channel_id"],
            "message_id": menu["message_id"],
            "has_discord_message": menu["message_id"] is not None,
            "options_count": options_count["count"] if options_count else 0,
            "created_at": menu["created_at"].isoformat() if menu["created_at"] else None
        }
        
        return status
        
    except Exception as e:
        print(f"Get role menu status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def notify_bot_role_menu_delete(guild_id: str, channel_id: int, message_id: int):
    """Notify bot to delete role menu message"""
    try:
        # Try to delete the message directly through Discord API
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
            response = await client.delete(
                f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
                headers=headers
            )
            print(f"🗑️ Deleted role menu message {message_id} in channel {channel_id}")
            
    except Exception as e:
        print(f"Error deleting role menu message: {e}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    # Detect language from query parameter, cookie, or browser
    lang = request.query_params.get('lang')
    if not lang:
        lang = request.cookies.get('language')
    if not lang:
        accept_language = request.headers.get('accept-language', '')
        lang = detect_browser_language(accept_language)
    
    # Ensure language is supported
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # Load language data
    lang_data = load_language_file(lang)
    
    # Create response with language data
    import time
    response = templates.TemplateResponse("dashboard.html", {
        "request": request,
        "lang_data": lang_data,
        "current_lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "timestamp": int(time.time())  # Add timestamp for cache busting
    })
    
    # Set language cookie if it was changed via query parameter
    if request.query_params.get('lang'):
        response.set_cookie("language", lang, max_age=365*24*60*60)  # 1 year
    
    return response

@app.get("/language-test", response_class=HTMLResponse)
async def language_test_page(request: Request):
    """Language test page - for testing language functionality"""
    return templates.TemplateResponse("language-test.html", {"request": request})

@app.get("/terms-of-service", response_class=HTMLResponse)
async def terms_of_service(request: Request):
    """Terms of Service page"""
    from datetime import datetime
    current_date = datetime.now().strftime("%d/%m/%Y")
    return templates.TemplateResponse("terms-of-service.html", {
        "request": request,
        "current_date": current_date
    })

@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Privacy Policy page"""
    from datetime import datetime
    current_date = datetime.now().strftime("%d/%m/%Y")
    return templates.TemplateResponse("privacy-policy.html", {
        "request": request,
        "current_date": current_date
    })

# Add caching for guild access verification
guild_access_cache = {}
guild_access_cache_ttl = 300  # 5 minutes cache

async def verify_guild_access(guild_id: str, current_user: str) -> bool:
    """Verify user has access to a guild through Discord API or bot presence with caching"""
    try:
        # Create cache key
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        cache_key = f"{user_id}:{guild_id}"
        
        # Check cache first
        current_time = datetime.now().timestamp()
        if cache_key in guild_access_cache:
            cached_result, cache_time = guild_access_cache[cache_key]
            if current_time - cache_time < guild_access_cache_ttl:
                print(f"✅ Using cached guild access for {guild_id}")
                return cached_result
        
        print(f"🔍 Verifying guild access for guild {guild_id}")
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
        
        # Cache the result
        guild_access_cache[cache_key] = (result, current_time)
        
        return result
    except Exception as e:
        print(f"❌ Exception in verify_guild_access: {e}")
        return False

# Welcome System API Endpoints
@app.post("/api/admin/migrate-titles")
async def migrate_welcome_titles():
    """Temporary endpoint to add welcome_title and goodbye_title columns"""
    try:
        # Add welcome_title column
        try:
            await database.execute("""
                ALTER TABLE welcome_config 
                ADD COLUMN welcome_title VARCHAR(256) DEFAULT '👋 New member!' 
                AFTER welcome_channel
            """)
            print("✅ Added welcome_title column")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️ welcome_title column already exists")
            else:
                print(f"❌ Error adding welcome_title: {e}")
        
        # Add goodbye_title column
        try:
            await database.execute("""
                ALTER TABLE welcome_config 
                ADD COLUMN goodbye_title VARCHAR(256) DEFAULT '👋 Departure' 
                AFTER goodbye_channel
            """)
            print("✅ Added goodbye_title column")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️ goodbye_title column already exists")
            else:
                print(f"❌ Error adding goodbye_title: {e}")
        
        # Test the columns
        result = await database.fetch_one("SELECT welcome_title, goodbye_title FROM welcome_config LIMIT 1")
        print(f"✅ Test query successful: {result}")
        
        return {"success": True, "message": "Migration completed"}
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return {"success": False, "error": str(e)}

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
                "welcome_enabled": bool(welcome_config.get("welcome_channel")),
                "welcome_channel": str(welcome_config["welcome_channel"]) if welcome_config["welcome_channel"] else None,
                "welcome_title": welcome_config.get("welcome_title", "👋 New member!"),
                "welcome_message": welcome_config["welcome_message"] or "Welcome {user} to {server}!",
                "welcome_fields": json.loads(welcome_config["welcome_fields"]) if welcome_config.get("welcome_fields") else None,
                "goodbye_enabled": bool(welcome_config.get("goodbye_channel")),
                "goodbye_channel": str(welcome_config["goodbye_channel"]) if welcome_config["goodbye_channel"] else None,
                "goodbye_title": welcome_config.get("goodbye_title", "👋 Departure"),
                "goodbye_message": welcome_config["goodbye_message"] or "Goodbye {user}, we'll miss you!",
                "goodbye_fields": json.loads(welcome_config["goodbye_fields"]) if welcome_config.get("goodbye_fields") else None,
                "auto_role_enabled": welcome_config.get("auto_role_enabled", False),
                "auto_role_ids": json.loads(welcome_config["auto_role_ids"]) if welcome_config.get("auto_role_ids") else []
            }
        elif guild_config and (guild_config.get("welcome_enabled") or guild_config.get("auto_role_enabled")):
            # If no welcome_config but guild_config has welcome or auto-role settings, use those
            return {
                "welcome_enabled": guild_config.get("welcome_enabled", False),
                "welcome_channel": str(guild_config["welcome_channel"]) if guild_config.get("welcome_channel") else None,
                "welcome_title": "👋 New member!",
                "welcome_message": guild_config.get("welcome_message", "Welcome {user} to {server}!"),
                "welcome_fields": None,
                "goodbye_enabled": False,
                "goodbye_channel": None,
                "goodbye_title": "👋 Departure",
                "goodbye_message": "Goodbye {user}, we'll miss you!",
                "goodbye_fields": None,
                "auto_role_enabled": guild_config.get("auto_role_enabled", False),
                "auto_role_ids": json.loads(guild_config["auto_role_ids"]) if guild_config.get("auto_role_ids") else []
            }
        else:
            return {
                "welcome_enabled": False,
                "welcome_channel": None,
                "welcome_title": "👋 New member!",
                "welcome_message": "Welcome {user} to {server}!",
                "welcome_fields": None,
                "goodbye_enabled": False,
                "goodbye_channel": None,
                "goodbye_title": "👋 Departure",
                "goodbye_message": "Goodbye {user}, we'll miss you!",
                "goodbye_fields": None,
                "auto_role_enabled": False,
                "auto_role_ids": []
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
        print(f"Config data: welcome_enabled={config.welcome_enabled} goodbye_enabled={config.goodbye_enabled} welcome_channel='{config.welcome_channel}' welcome_title='{config.welcome_title}' welcome_message='{config.welcome_message}' goodbye_channel='{config.goodbye_channel}' goodbye_title='{config.goodbye_title}' goodbye_message='{config.goodbye_message}' auto_role_enabled={config.auto_role_enabled} auto_role_ids={config.auto_role_ids}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        if config.welcome_enabled or config.goodbye_enabled or config.auto_role_enabled:
            # Vérifier d'abord si les colonnes existent
            try:
                # Essayer d'abord avec toutes les colonnes
                await database.execute(
                    """INSERT INTO welcome_config 
                       (guild_id, welcome_channel, welcome_title, welcome_message, welcome_fields, goodbye_channel, goodbye_title, goodbye_message, goodbye_fields, auto_role_enabled, auto_role_ids, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new_values
                       ON DUPLICATE KEY UPDATE
                       welcome_channel = new_values.welcome_channel,
                       welcome_title = new_values.welcome_title,
                       welcome_message = new_values.welcome_message,
                       welcome_fields = new_values.welcome_fields,
                       goodbye_channel = new_values.goodbye_channel,
                       goodbye_title = new_values.goodbye_title,
                       goodbye_message = new_values.goodbye_message,
                       goodbye_fields = new_values.goodbye_fields,
                       auto_role_enabled = new_values.auto_role_enabled,
                       auto_role_ids = new_values.auto_role_ids,
                       updated_at = new_values.updated_at""",
                    (guild_id, 
                     int(config.welcome_channel) if config.welcome_channel else None,
                     config.welcome_title,
                     config.welcome_message,
                     json.dumps(config.welcome_fields) if config.welcome_fields else None,
                     int(config.goodbye_channel) if config.goodbye_channel else None,
                     config.goodbye_title,
                     config.goodbye_message,
                     json.dumps(config.goodbye_fields) if config.goodbye_fields else None,
                     config.auto_role_enabled,
                     json.dumps(config.auto_role_ids) if config.auto_role_ids else None,
                     datetime.utcnow())
                )
            except Exception as e:
                if "Unknown column" in str(e):
                    print(f"⚠️ Colonnes manquantes détectées, utilisation de la version simplifiée: {e}")
                    # Fallback vers la version simplifiée sans les nouvelles colonnes
                    await database.execute(
                        """INSERT INTO welcome_config 
                           (guild_id, welcome_channel, welcome_message, goodbye_channel, goodbye_message, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s) AS new_values
                           ON DUPLICATE KEY UPDATE
                           welcome_channel = new_values.welcome_channel,
                           welcome_message = new_values.welcome_message,
                           goodbye_channel = new_values.goodbye_channel,
                           goodbye_message = new_values.goodbye_message,
                           updated_at = new_values.updated_at""",
                        (guild_id, 
                         int(config.welcome_channel) if config.welcome_channel else None,
                         config.welcome_message,
                         int(config.goodbye_channel) if config.goodbye_channel else None,
                         config.goodbye_message,
                         datetime.utcnow())
                    )
                    print("⚠️ Configuration sauvegardée sans les nouvelles fonctionnalités (titre, champs, auto-rôle)")
                else:
                    raise e
        else:
            # Only delete welcome config if ALL features are disabled (including auto-role)
            await database.execute(
                "DELETE FROM welcome_config WHERE guild_id = %s",
                (guild_id,)
            )
        
        # Update general config
        await database.execute(
            """INSERT INTO guild_config 
               (guild_id, welcome_enabled, welcome_channel, welcome_message, auto_role_enabled, auto_role_ids, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s) AS new_values
               ON DUPLICATE KEY UPDATE
               welcome_enabled = new_values.welcome_enabled,
               welcome_channel = new_values.welcome_channel,
               welcome_message = new_values.welcome_message,
               auto_role_enabled = new_values.auto_role_enabled,
               auto_role_ids = new_values.auto_role_ids,
               updated_at = new_values.updated_at""",
            (guild_id, config.welcome_enabled, 
             int(config.welcome_channel) if config.welcome_channel else None,
             config.welcome_message, 
             config.auto_role_enabled,
             json.dumps(config.auto_role_ids) if config.auto_role_ids else None,
             datetime.utcnow())
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
            member_count = "Unknown"
            if guild_response.status_code == 200:
                guild_data = guild_response.json()
                guild_name = guild_data.get("name", "Unknown Server")
                member_count = str(guild_data.get("member_count", "Unknown"))
                print(f"🔍 Guild name: {guild_name}")
                print(f"🔍 Member count: {member_count}")
            
            # Get user info for avatar and username
            user_response = await client.get(
                f"https://discord.com/api/v10/users/{user_id}",
                headers=headers
            )
            
            user_avatar_url = None
            username = "TestUser"
            display_name = "TestUser"
            if user_response.status_code == 200:
                user_data = user_response.json()
                username = user_data.get("username", "TestUser")
                display_name = user_data.get("global_name") or user_data.get("display_name") or username
                avatar_hash = user_data.get("avatar")
                if avatar_hash:
                    user_avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=256"
                print(f"🔍 Username: {username}")
                print(f"🔍 Display name: {display_name}")
                print(f"🔍 User avatar URL: {user_avatar_url}")
            
            # Format the welcome message with multiple placeholder support
            formatted_message = welcome_message\
                .replace("{user}", f"<@{user_id}>")\
                .replace("{server}", guild_name)\
                .replace("{memberMention}", f"<@{user_id}>")\
                .replace("{serverName}", guild_name)\
                .replace("{userMention}", f"<@{user_id}>")\
                .replace("{memberName}", f"<@{user_id}>")\
                .replace("{username}", username)\
                .replace("{displayname}", display_name)\
                .replace("{memberCount}", member_count)
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
                        "text": "This is a test message from Maybee Dashboard"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            # Add custom fields if configured
            welcome_fields = welcome_config.get("welcome_fields") if welcome_config else None
            if welcome_fields:
                try:
                    if isinstance(welcome_fields, str):
                        fields_data = json.loads(welcome_fields)
                    else:
                        fields_data = welcome_fields
                    
                    if isinstance(fields_data, list):
                        embed_fields = []
                        for field in fields_data:
                            if isinstance(field, dict) and "name" in field and "value" in field:
                                # Format field name and value with placeholders
                                field_name = field["name"]\
                                    .replace("{user}", f"<@{user_id}>")\
                                    .replace("{server}", guild_name)\
                                    .replace("{username}", username)\
                                    .replace("{displayname}", display_name)\
                                    .replace("{memberCount}", member_count)
                                    
                                field_value = field["value"]\
                                    .replace("{user}", f"<@{user_id}>")\
                                    .replace("{server}", guild_name)\
                                    .replace("{username}", username)\
                                    .replace("{displayname}", display_name)\
                                    .replace("{memberCount}", member_count)
                                
                                embed_fields.append({
                                    "name": field_name,
                                    "value": field_value,
                                    "inline": field.get("inline", False)
                                })
                        
                        if embed_fields:
                            embed_data["embeds"][0]["fields"] = embed_fields
                            print(f"🔍 Added {len(embed_fields)} custom fields to embed")
                
                except Exception as e:
                    print(f"⚠️ Error processing welcome fields for test: {e}")
            
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

# Ticket System API Endpoints
@app.get("/api/guild/{guild_id}/tickets")
async def get_ticket_config(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get ticket system configuration for a guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get ticket config
        ticket_config = await database.fetch_one(
            "SELECT * FROM ticket_config WHERE guild_id = %s",
            (guild_id,)
        )
        
        # Get ticket panels
        panels = await database.fetch_all(
            "SELECT * FROM ticket_panels WHERE guild_id = %s ORDER BY id",
            (guild_id,)
        )
        
        panels_with_buttons = []
        for panel in panels:
            # Get buttons for each panel
            buttons = await database.fetch_all(
                "SELECT * FROM ticket_buttons WHERE panel_id = %s ORDER BY button_order, id",
                (panel["id"],)
            )
            
            # Convert buttons to dict format
            buttons_list = []
            for button in buttons:
                buttons_list.append({
                    "id": button["id"],
                    "button_label": button["button_label"],
                    "button_emoji": button["button_emoji"],
                    "button_style": button["button_style"],
                    "category_id": button["category_id"],
                    "ticket_name_format": button["ticket_name_format"],
                    "ping_roles": json.loads(button["ping_roles"]) if button["ping_roles"] else [],
                    "initial_message": button["initial_message"],
                    "button_order": button["button_order"]
                })
            
            panels_with_buttons.append({
                "id": panel["id"],
                "panel_name": panel["panel_name"],
                "channel_id": panel["channel_id"],
                "message_id": panel["message_id"],
                "embed_title": panel["embed_title"],
                "embed_description": panel["embed_description"],
                "embed_color": panel["embed_color"],
                "embed_thumbnail": panel["embed_thumbnail"],
                "embed_image": panel["embed_image"],
                "embed_footer": panel["embed_footer"],
                "buttons": buttons_list
            })
        
        return {
            "enabled": ticket_config["enabled"] if ticket_config else False,
            "panels": panels_with_buttons
        }
        
    except Exception as e:
        print(f"Ticket config get error: {e}")
        # Return default config instead of error
        return {
            "enabled": False,
            "panels": []
        }

@app.put("/api/guild/{guild_id}/tickets")
async def update_ticket_config(
    guild_id: str,
    config: TicketConfig,
    current_user: str = Depends(get_current_user)
):
    """Update ticket system configuration for a guild"""
    try:
        print(f"Received ticket config update for guild {guild_id}")
        print(f"Config data: enabled={config.enabled}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Update or create ticket config
        await database.execute(
            """INSERT INTO ticket_config (guild_id, enabled, updated_at) 
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE 
               enabled = VALUES(enabled),
               updated_at = VALUES(updated_at)""",
            (guild_id, config.enabled, datetime.utcnow())
        )
        
        return {"message": "Ticket configuration updated successfully"}
        
    except Exception as e:
        print(f"Ticket config update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/tickets/panels")
async def get_ticket_panels(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get all ticket panels for a guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get ticket panels with buttons
        panels = await database.fetch_all(
            "SELECT * FROM ticket_panels WHERE guild_id = %s ORDER BY id",
            (guild_id,)
        )
        
        panels_with_buttons = []
        for panel in panels:
            buttons = await database.fetch_all(
                "SELECT * FROM ticket_buttons WHERE panel_id = %s ORDER BY button_order, id",
                (panel["id"],)
            )
            
            buttons_list = []
            for button in buttons:
                buttons_list.append({
                    "id": button["id"],
                    "button_label": button["button_label"],
                    "button_emoji": button["button_emoji"],
                    "button_style": button["button_style"],
                    "category_id": button["category_id"],
                    "ticket_name_format": button["ticket_name_format"],
                    "ping_roles": json.loads(button["ping_roles"]) if button["ping_roles"] else [],
                    "initial_message": button["initial_message"],
                    "button_order": button["button_order"]
                })
            
            panels_with_buttons.append({
                "id": panel["id"],
                "panel_name": panel["panel_name"],
                "channel_id": panel["channel_id"],
                "message_id": panel["message_id"],
                "embed_title": panel["embed_title"],
                "embed_description": panel["embed_description"],
                "embed_color": panel["embed_color"],
                "embed_thumbnail": panel["embed_thumbnail"],
                "embed_image": panel["embed_image"],
                "embed_footer": panel["embed_footer"],
                "buttons": buttons_list
            })
        
        return {"panels": panels_with_buttons}
        
    except Exception as e:
        print(f"Get ticket panels error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/tickets/panels")
async def create_ticket_panel(
    guild_id: str,
    panel: TicketPanel,
    current_user: str = Depends(get_current_user)
):
    """Create a new ticket panel"""
    try:
        print(f"Creating ticket panel for guild {guild_id}: {panel.panel_name}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Create panel
        panel_id = await database.execute_and_get_id(
            """INSERT INTO ticket_panels 
               (guild_id, panel_name, embed_title, embed_description, embed_color, 
                embed_thumbnail, embed_image, embed_footer, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (guild_id, panel.panel_name, panel.embed_title, panel.embed_description,
             panel.embed_color, panel.embed_thumbnail, panel.embed_image, 
             panel.embed_footer, datetime.utcnow(), datetime.utcnow())
        )
        
        # Create buttons if provided
        if panel.buttons:
            for button in panel.buttons:
                await database.execute(
                    """INSERT INTO ticket_buttons 
                       (panel_id, button_label, button_emoji, button_style, category_id,
                        ticket_name_format, ping_roles, initial_message, button_order)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (panel_id, button.button_label, button.button_emoji, button.button_style,
                     button.category_id, button.ticket_name_format, 
                     json.dumps(button.ping_roles) if button.ping_roles else None,
                     button.initial_message, button.button_order)
                )
        
        return {"message": "Ticket panel created successfully", "panel_id": panel_id}
        
    except Exception as e:
        print(f"Create ticket panel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guild/{guild_id}/tickets/panels/{panel_id}")
async def update_ticket_panel(
    guild_id: str,
    panel_id: int,
    panel: TicketPanel,
    current_user: str = Depends(get_current_user)
):
    """Update an existing ticket panel"""
    try:
        print(f"Updating ticket panel {panel_id} for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Verify panel belongs to guild
        existing_panel = await database.fetch_one(
            "SELECT * FROM ticket_panels WHERE id = %s AND guild_id = %s",
            (panel_id, guild_id)
        )
        
        if not existing_panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        # Update panel
        await database.execute(
            """UPDATE ticket_panels SET 
               panel_name = %s, embed_title = %s, embed_description = %s,
               embed_color = %s, embed_thumbnail = %s, embed_image = %s,
               embed_footer = %s, updated_at = %s
               WHERE id = %s AND guild_id = %s""",
            (panel.panel_name, panel.embed_title, panel.embed_description,
             panel.embed_color, panel.embed_thumbnail, panel.embed_image,
             panel.embed_footer, datetime.utcnow(), panel_id, guild_id)
        )
        
        # Delete existing buttons
        await database.execute(
            "DELETE FROM ticket_buttons WHERE panel_id = %s",
            (panel_id,)
        )
        
        # Create new buttons
        if panel.buttons:
            for button in panel.buttons:
                await database.execute(
                    """INSERT INTO ticket_buttons 
                       (panel_id, button_label, button_emoji, button_style, category_id,
                        ticket_name_format, ping_roles, initial_message, button_order)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (panel_id, button.button_label, button.button_emoji, button.button_style,
                     button.category_id, button.ticket_name_format,
                     json.dumps(button.ping_roles) if button.ping_roles else None,
                     button.initial_message, button.button_order)
                )
        
        return {"message": "Ticket panel updated successfully"}
        
    except Exception as e:
        print(f"Update ticket panel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/guild/{guild_id}/tickets/panels/{panel_id}")
async def delete_ticket_panel(
    guild_id: str,
    panel_id: int,
    current_user: str = Depends(get_current_user)
):
    """Delete a ticket panel"""
    try:
        print(f"Deleting ticket panel {panel_id} for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Verify panel belongs to guild
        existing_panel = await database.fetch_one(
            "SELECT * FROM ticket_panels WHERE id = %s AND guild_id = %s",
            (panel_id, guild_id)
        )
        
        if not existing_panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        # Delete panel (buttons will be deleted by CASCADE)
        await database.execute(
            "DELETE FROM ticket_panels WHERE id = %s AND guild_id = %s",
            (panel_id, guild_id)
        )
        
        return {"message": "Ticket panel deleted successfully"}
        
    except Exception as e:
        print(f"Delete ticket panel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_discord_button_style(style_name: str) -> int:
    """Convert button style name to Discord button style integer"""
    style_map = {
        "primary": 1,    # Blue
        "secondary": 2,  # Grey  
        "success": 3,    # Green
        "danger": 4      # Red
    }
    return style_map.get(style_name.lower(), 2)  # Default to secondary

@app.post("/api/guild/{guild_id}/tickets/panels/{panel_id}/deploy")
async def deploy_ticket_panel(
    guild_id: str,
    panel_id: int,
    deploy_request: DeployRequest,
    current_user: str = Depends(get_current_user)
):
    """Deploy a ticket panel to a Discord channel"""
    try:
        print(f"Deploying ticket panel {panel_id} to channel {deploy_request.channel_id} for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get panel data
        panel = await database.fetch_one(
            "SELECT * FROM ticket_panels WHERE id = %s AND guild_id = %s",
            (panel_id, guild_id)
        )
        
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        # Get panel buttons
        buttons = await database.fetch_all(
            "SELECT * FROM ticket_buttons WHERE panel_id = %s ORDER BY button_order, id",
            (panel_id,)
        )
        
        # Create Discord embed
        embed = {
            "title": panel["embed_title"] or "Support Tickets",
            "description": panel["embed_description"] or "Click a button below to create a ticket",
            "color": int(panel["embed_color"].replace("#", ""), 16) if panel["embed_color"] else 0x5865F2
        }
        
        # Add footer if present
        if panel["embed_footer"]:
            embed["footer"] = {"text": panel["embed_footer"]}
        
        # Add thumbnail if present
        if panel["embed_thumbnail"]:
            embed["thumbnail"] = {"url": panel["embed_thumbnail"]}
        
        # Add image if present
        if panel["embed_image"]:
            embed["image"] = {"url": panel["embed_image"]}
        
        # Create Discord buttons/components
        components = []
        if buttons:
            action_row = {
                "type": 1,  # Action Row
                "components": []
            }
            
            for button in buttons:
                # Validate and fix button data
                button_label = button["button_label"]
                if not button_label or not button_label.strip():
                    print(f"Warning: Button {button['id']} has empty label, using default")
                    button_label = "Create Ticket"  # Default label
                else:
                    button_label = button_label.strip()
                
                discord_button = {
                    "type": 2,  # Button
                    "style": get_discord_button_style(button["button_style"]),
                    "label": button_label,
                    "custom_id": f"ticket_button_{button['id']}"
                }
                
                # Add emoji if present
                if button["button_emoji"]:
                    # Handle both unicode and custom emojis
                    if button["button_emoji"].startswith("<"):
                        # Custom emoji format: <:name:id>
                        emoji_parts = button["button_emoji"].strip("<>").split(":")
                        if len(emoji_parts) >= 3:
                            discord_button["emoji"] = {
                                "name": emoji_parts[1],
                                "id": emoji_parts[2],
                                "animated": button["button_emoji"].startswith("<a:")
                            }
                    else:
                        # Unicode emoji
                        discord_button["emoji"] = {"name": button["button_emoji"]}
                
                action_row["components"].append(discord_button)
            
            # Only add action row if it has components
            if action_row["components"]:
                components.append(action_row)
        
        # Debug: Print the components being sent
        print(f"Debug: Sending components to Discord: {components}")
        
        # Send message to Discord channel
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        # Clean the token
        bot_token = bot_token.strip()
        if '=' in bot_token and 'DISCORD_TOKEN=' in bot_token:
            bot_token = bot_token.split('=', 1)[1]
        
        message_payload = {
            "embeds": [embed]
        }
        
        if components:
            message_payload["components"] = components
        
        # Debug: Print the full payload
        print(f"Debug: Full message payload: {message_payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://discord.com/api/channels/{deploy_request.channel_id}/messages",
                headers={
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json"
                },
                json=message_payload
            )
            
            if response.status_code not in [200, 201]:
                print(f"Discord API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"Failed to send message to Discord: {response.text}")
            
            message_data = response.json()
            message_id = message_data["id"]
            
            # Update panel with channel_id and message_id
            await database.execute(
                "UPDATE ticket_panels SET channel_id = %s, message_id = %s, updated_at = %s WHERE id = %s",
                (deploy_request.channel_id, message_id, datetime.utcnow(), panel_id)
            )
        
        return {"message": "Ticket panel deployed successfully"}
        
    except Exception as e:
        print(f"Deploy ticket panel error: {e}")
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
                            "id": str(member["user"]["id"]),  # Convert to string for JavaScript compatibility
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
                            "text": "Maybee Moderation System"
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
        print(f"🔍 Getting moderation history for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get recent warnings
        warnings = await database.fetch_all(
            "SELECT user_id, moderator_id, reason, timestamp, 'warning' as action_type FROM warnings WHERE guild_id = %s ORDER BY timestamp DESC LIMIT 10",
            (guild_id,)
        )
        print(f"📝 Found {len(warnings) if warnings else 0} warnings in database")
        
        # Get recent timeouts
        timeouts = await database.fetch_all(
            "SELECT user_id, moderator_id, duration, reason, timestamp, 'timeout' as action_type FROM timeouts WHERE guild_id = %s ORDER BY timestamp DESC LIMIT 10",
            (guild_id,)
        )
        print(f"📝 Found {len(timeouts) if timeouts else 0} timeouts in database")
        
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
        
        print(f"📝 Returning {len(history)} total moderation actions")
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

# ===== EMBED CREATOR ENDPOINTS =====

@app.post("/api/guild/{guild_id}/embed/send")
async def send_embed_message(
    guild_id: str,
    embed_data: EmbedCreator,
    current_user: str = Depends(get_current_user)
):
    """Send a custom embed message to a Discord channel"""
    try:
        print(f"📝 Sending embed message for guild {guild_id}")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get bot token
        bot_token = DISCORD_BOT_TOKEN
        if not bot_token:
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        # Clean the token
        bot_token = bot_token.strip()
        if '=' in bot_token and 'DISCORD_TOKEN=' in bot_token:
            bot_token = bot_token.split('=', 1)[1]
        
        # Build Discord embed
        embed = {}
        
        if embed_data.title:
            embed["title"] = embed_data.title
        
        if embed_data.description:
            embed["description"] = embed_data.description
        
        if embed_data.color:
            # Convert hex color to decimal
            color_hex = embed_data.color.lstrip('#')
            embed["color"] = int(color_hex, 16)
        
        if embed_data.thumbnail_url:
            embed["thumbnail"] = {"url": embed_data.thumbnail_url}
        
        if embed_data.image_url:
            embed["image"] = {"url": embed_data.image_url}
        
        # Author section
        if embed_data.author_name:
            author = {"name": embed_data.author_name}
            if embed_data.author_icon_url:
                author["icon_url"] = embed_data.author_icon_url
            if embed_data.author_url:
                author["url"] = embed_data.author_url
            embed["author"] = author
        
        # Footer section
        footer_parts = []
        if embed_data.footer_text:
            footer = {"text": embed_data.footer_text}
            if embed_data.footer_icon_url:
                footer["icon_url"] = embed_data.footer_icon_url
            embed["footer"] = footer
        
        # Timestamp
        if embed_data.timestamp_enabled:
            embed["timestamp"] = datetime.utcnow().isoformat()
        
        # Fields
        if embed_data.fields:
            embed_fields = []
            for field in embed_data.fields:
                if field.name and field.value:  # Only add fields with both name and value
                    embed_fields.append({
                        "name": field.name[:1024],  # Discord limit
                        "value": field.value[:1024],  # Discord limit
                        "inline": field.inline
                    })
            
            if embed_fields:
                embed["fields"] = embed_fields[:25]  # Discord limit of 25 fields
        
        # Prepare message content
        message_content = ""
        ping_parts = []
        
        # Add role ping
        if embed_data.ping_role_id:
            ping_parts.append(f"<@&{embed_data.ping_role_id}>")
        
        # Add user ping
        if embed_data.ping_user_id:
            ping_parts.append(f"<@{embed_data.ping_user_id}>")
        
        if ping_parts:
            message_content = " ".join(ping_parts)
        
        # Prepare message payload
        message_payload = {
            "embeds": [embed]
        }
        
        if message_content:
            message_payload["content"] = message_content
        
        print(f"🔍 Embed payload: {embed}")
        
        # Send message to Discord
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://discord.com/api/channels/{embed_data.target_channel}/messages",
                headers={
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json"
                },
                json=message_payload
            )
            
            print(f"🔍 Discord API response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Embed message sent successfully: {response_data.get('id')}")
                return {
                    "success": True,
                    "message": "Embed sent successfully!",
                    "message_id": response_data.get("id")
                }
            else:
                error_data = response.json() if response.content else {}
                print(f"❌ Discord API error: {response.status_code} - {error_data}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to send embed: {error_data.get('message', 'Unknown error')}"
                )
    
    except Exception as e:
        print(f"❌ Send embed error: {e}")
        import traceback
        print(f"❌ Send embed traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guild/{guild_id}/embed/saved")
async def get_saved_embeds(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get saved embed configurations for a guild"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Get saved embeds from database
        saved_embeds = await database.fetch_all(
            "SELECT * FROM embed_config WHERE guild_id = %s ORDER BY created_at DESC",
            (guild_id,)
        )
        
        result = []
        for embed in saved_embeds:
            embed_data = {
                "id": embed["id"],
                "name": embed["name"],
                "title": embed["title"],
                "description": embed["description"],
                "color": embed["color"],
                "thumbnail_url": embed["thumbnail_url"],
                "image_url": embed["image_url"],
                "author_name": embed["author_name"],
                "author_icon_url": embed["author_icon_url"],
                "author_url": embed["author_url"],
                "footer_text": embed["footer_text"],
                "footer_icon_url": embed["footer_icon_url"],
                "timestamp_enabled": embed["timestamp_enabled"],
                "fields": json.loads(embed["fields"]) if embed["fields"] else None,
                "created_at": embed["created_at"],
                "updated_at": embed["updated_at"]
            }
            result.append(embed_data)
        
        return result
    
    except Exception as e:
        print(f"Get saved embeds error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guild/{guild_id}/embed/save")
async def save_embed_config(
    guild_id: str,
    embed_config: EmbedConfig,
    current_user: str = Depends(get_current_user)
):
    """Save an embed configuration for future use"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Save embed configuration
        await database.execute(
            """INSERT INTO embed_config 
               (guild_id, name, title, description, color, thumbnail_url, image_url, 
                author_name, author_icon_url, author_url, footer_text, footer_icon_url, 
                timestamp_enabled, fields, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (guild_id, embed_config.name, embed_config.title, embed_config.description,
             embed_config.color, embed_config.thumbnail_url, embed_config.image_url,
             embed_config.author_name, embed_config.author_icon_url, embed_config.author_url,
             embed_config.footer_text, embed_config.footer_icon_url, embed_config.timestamp_enabled,
             json.dumps([field.dict() for field in embed_config.fields]) if embed_config.fields else None,
             datetime.utcnow(), datetime.utcnow())
        )
        
        return {"message": "Embed configuration saved successfully"}
    
    except Exception as e:
        print(f"Save embed config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/guild/{guild_id}/embed/saved/{embed_id}")
async def delete_saved_embed(
    guild_id: str,
    embed_id: int,
    current_user: str = Depends(get_current_user)
):
    """Delete a saved embed configuration"""
    try:
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Delete embed configuration
        await database.execute(
            "DELETE FROM embed_config WHERE id = %s AND guild_id = %s",
            (embed_id, guild_id)
        )
        
        return {"message": "Embed configuration deleted successfully"}
    
    except Exception as e:
        print(f"Delete embed config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Ticket Logs API Endpoints
@app.get("/api/ticket-logs/search-users")
async def search_users(
    query: str,
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Search for users in the current guild from Google Drive logs"""
    try:
        if not guild_id:
            raise HTTPException(status_code=400, detail="No guild selected")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Import GoogleDriveStorage
        import sys
        sys.path.append('..')
        from cloud_storage import GoogleDriveStorage
        
        # Initialize Google Drive storage
        storage = GoogleDriveStorage()
        await storage.initialize()
        
        # Get all ticket logs from Google Drive
        all_logs = await storage.list_all_ticket_logs(guild_id)
        
        # Filter users based on query
        matching_users = []
        seen_users = set()
        
        for log_data in all_logs:
            user_id = log_data.get('user_id')
            username = log_data.get('username', '')
            discriminator = log_data.get('discriminator', '')
            
            # Skip invalid user IDs
            if not user_id or user_id == 'Inconnu' or user_id in seen_users:
                continue
            
            # Check if user matches query
            if (query.lower() in username.lower() or 
                query.lower() in discriminator.lower() or 
                query in str(user_id)):
                
                matching_users.append({
                    'id': user_id,
                    'username': username,
                    'discriminator': discriminator,
                    'avatar_url': log_data.get('avatar_url')
                })
                seen_users.add(user_id)
                
                # Limit to 10 results
                if len(matching_users) >= 10:
                    break
        
        return {"users": matching_users}
        
    except Exception as e:
        print(f"Search users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticket-logs/search-suggestions")
async def get_search_suggestions(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get search suggestions for users with recent tickets from Google Drive"""
    try:
        if not guild_id:
            raise HTTPException(status_code=400, detail="No guild selected")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Import GoogleDriveStorage
        import sys
        sys.path.append('..')
        from cloud_storage import GoogleDriveStorage
        
        # Initialize Google Drive storage
        storage = GoogleDriveStorage()
        await storage.initialize()
        
        # Get all ticket logs from Google Drive
        all_logs = await storage.list_all_ticket_logs(guild_id)
        
        # Process logs to create suggestions
        user_stats = {}
        for log_data in all_logs:
            user_id = log_data.get('user_id')
            # Skip invalid user IDs
            if not user_id or user_id == 'Inconnu':
                continue
                
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'id': user_id,
                    'username': log_data.get('username', 'Unknown'),
                    'discriminator': log_data.get('discriminator', '0000'),
                    'avatar_url': log_data.get('avatar_url'),
                    'ticket_count': 0,
                    'last_ticket_date': None
                }
            
            user_stats[user_id]['ticket_count'] += 1
            
            # Update last ticket date
            created_at = log_data.get('created_at')
            if created_at:
                if not user_stats[user_id]['last_ticket_date'] or created_at > user_stats[user_id]['last_ticket_date']:
                    user_stats[user_id]['last_ticket_date'] = created_at
        
        # Convert to list and sort by last ticket date
        suggestions = list(user_stats.values())
        suggestions.sort(key=lambda x: x['last_ticket_date'] or '', reverse=True)
        
        # Limit to 10 suggestions
        suggestions = suggestions[:10]
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        print(f"Search suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticket-logs/user-tickets/{user_id}")
async def get_user_tickets(
    user_id: str,
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get all tickets for a specific user from Google Drive logs"""
    try:
        if not guild_id:
            raise HTTPException(status_code=400, detail="No guild selected")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Import GoogleDriveStorage
        import sys
        sys.path.append('..')
        from cloud_storage import GoogleDriveStorage
        
        # Initialize Google Drive storage
        storage = GoogleDriveStorage()
        await storage.initialize()
        
        # Validate user_id
        if user_id == 'Inconnu' or not user_id.isdigit():
            raise HTTPException(status_code=400, detail="Invalid user ID")
        
        # Get ticket logs for this specific user from Google Drive
        user_logs = await storage.list_user_ticket_logs(guild_id, int(user_id))
        
        # Process logs to create user info and tickets list
        user_tickets = []
        user_info = None
        
        for log_data in user_logs:
            if not user_info:
                # Utiliser les mêmes données que dans get_search_suggestions
                user_info = {
                    'id': user_id,
                    'username': log_data.get('username', 'Unknown'),
                    'discriminator': log_data.get('discriminator', '0000'),
                    'display_name': log_data.get('display_name', log_data.get('username', 'Unknown')),
                    'avatar_url': log_data.get('avatar_url')
                }
            
            user_tickets.append({
                'ticket_id': log_data.get('ticket_id'),
                'file_id': log_data.get('file_id'),
                'status': log_data.get('status', 'closed'),
                'created_at': log_data.get('created_at'),
                'closed_at': log_data.get('closed_at'),
                'message_count': log_data.get('message_count', 0),
                'event_count': log_data.get('event_count', 0),
                'username': log_data.get('username', 'Unknown'),
                'discriminator': log_data.get('discriminator', '0000'),
                'display_name': log_data.get('display_name', log_data.get('username', 'Unknown')),
                'avatar_url': log_data.get('avatar_url')
            })
        
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Sort tickets by creation date (newest first)
        user_tickets.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        return {
            "user": user_info,
            "tickets": user_tickets
        }
        
    except Exception as e:
        print(f"Get user tickets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticket-logs/ticket-details/{file_id}")
async def get_ticket_details(
    file_id: str,
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get detailed ticket information from Google Drive"""
    try:
        if not guild_id:
            raise HTTPException(status_code=400, detail="No guild selected")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Import GoogleDriveStorage
        import sys
        sys.path.append('..')
        from cloud_storage import GoogleDriveStorage
        
        # Initialize Google Drive storage
        storage = GoogleDriveStorage()
        await storage.initialize()
        
        # Download ticket logs from Google Drive
        ticket_data = await storage.download_ticket_logs(file_id)
        
        if not ticket_data:
            raise HTTPException(status_code=404, detail="Ticket logs not found")
        
        return ticket_data
        
    except Exception as e:
        print(f"Get ticket details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticket-logs/debug")
async def debug_ticket_logs(
    guild_id: str,
    current_user: str = Depends(get_current_user)
):
    """Debug endpoint to check ticket logs data from Google Drive"""
    try:
        if not guild_id:
            raise HTTPException(status_code=400, detail="No guild selected")
        
        # Verify user has access
        if not await verify_guild_access(guild_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to this guild")
        
        # Import GoogleDriveStorage
        import sys
        sys.path.append('..')
        from cloud_storage import GoogleDriveStorage
        
        # Initialize Google Drive storage
        storage = GoogleDriveStorage()
        await storage.initialize()
        
        # Get all ticket logs from Google Drive
        all_logs = await storage.list_all_ticket_logs(guild_id)
        
        # Count unique users and tickets
        unique_users = set()
        unique_tickets = set()
        
        for log_data in all_logs:
            if log_data.get('user_id'):
                unique_users.add(log_data['user_id'])
            if log_data.get('ticket_id'):
                unique_tickets.add(log_data['ticket_id'])
        
        # Get sample data (first 5 logs)
        sample_logs = all_logs[:5] if all_logs else []
        
        return {
            "guild_id": guild_id,
            "total_logs": len(all_logs),
            "unique_users": len(unique_users),
            "unique_tickets": len(unique_tickets),
            "sample_logs": sample_logs,
            "google_drive_connected": True,
            "debug_info": {
                "sample_user_ids": [log.get('user_id') for log in sample_logs[:3]],
                "sample_usernames": [log.get('username') for log in sample_logs[:3]],
                "sample_ticket_ids": [log.get('ticket_id') for log in sample_logs[:3]]
            }
        }
        
    except Exception as e:
        print(f"Debug ticket logs error: {e}")
        return {
            "guild_id": guild_id,
            "error": str(e),
            "google_drive_connected": False
        }

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
