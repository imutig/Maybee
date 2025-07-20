#!/usr/bin/env python3
"""
Reset XP for a specific guild
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database
from services import BotConfig

async def reset_server_xp(guild_id: str):
    """Reset all XP data for a specific guild"""
    
    # Load configuration the same way the bot does
    try:
        config = BotConfig.from_env()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return
    
    # Connect to database using bot config
    db = Database(
        host=config.db_host,
        port=3306,
        user=config.db_user,
        password=config.db_password,
        db=config.db_name
    )
    
    try:
        await db.connect()
        print(f"🔌 Connected to database")
        
        print(f'🔄 Resetting XP for guild {guild_id}...')
        
        # Get count before deletion
        count_result = await db.query('SELECT COUNT(*) as count FROM xp_data WHERE guild_id = %s', (guild_id,), fetchone=True)
        count = count_result['count'] if count_result else 0
        print(f'📊 Found {count} XP records to delete')
        
        # Delete all XP data for the guild
        await db.execute('DELETE FROM xp_data WHERE guild_id = %s', (guild_id,))
        print(f'🗑️ Deleted XP data records')
        
        await db.execute('DELETE FROM xp_history WHERE guild_id = %s', (guild_id,))
        print(f'🗑️ Deleted XP history records')
        
        print(f'✅ Successfully reset XP for guild {guild_id}')
        print(f'📈 All users will start fresh with 0 XP')
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.close()
        print(f"🔌 Database connection closed")

if __name__ == "__main__":
    guild_id = "1392463988679508030"  # Your server ID
    asyncio.run(reset_server_xp(guild_id))
