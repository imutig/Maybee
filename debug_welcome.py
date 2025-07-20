#!/usr/bin/env python3
"""
Welcome Configuration Debug Script
This script helps debug welcome message configuration issues.
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def debug_welcome_config():
    """Debug welcome configuration for OuiOui server"""
    
    # OuiOui server ID
    guild_id = 1392463988679508030
    
    # Initialize database
    db = Database(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        db=os.getenv('DB_NAME', 'maybee')
    )
    
    try:
        await db.connect()
        print("✅ Database connected successfully")
        
        # Check welcome_config table
        print("\n🔍 Checking welcome_config table:")
        welcome_config = await db.query(
            "SELECT * FROM welcome_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if welcome_config:
            print(f"  ✅ Welcome config found:")
            print(f"    Guild ID: {welcome_config.get('guild_id')}")
            print(f"    Welcome enabled: {welcome_config.get('welcome_enabled', 'Not set')}")
            print(f"    Welcome channel: {welcome_config.get('welcome_channel', 'Not set')}")
            print(f"    Welcome message: {welcome_config.get('welcome_message', 'Not set')}")
            print(f"    Goodbye enabled: {welcome_config.get('goodbye_enabled', 'Not set')}")
            print(f"    Goodbye channel: {welcome_config.get('goodbye_channel', 'Not set')}")
            print(f"    Goodbye message: {welcome_config.get('goodbye_message', 'Not set')}")
        else:
            print("  ❌ No welcome config found in welcome_config table")
            
        # Check guild_config table
        print("\n🔍 Checking guild_config table:")
        guild_config = await db.query(
            "SELECT * FROM guild_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if guild_config:
            print(f"  ✅ Guild config found:")
            print(f"    Guild ID: {guild_config.get('guild_id')}")
            print(f"    Welcome enabled: {guild_config.get('welcome_enabled', 'Not set')}")
            print(f"    Welcome channel: {guild_config.get('welcome_channel', 'Not set')}")
            print(f"    Welcome message: {guild_config.get('welcome_message', 'Not set')}")
        else:
            print("  ❌ No guild config found in guild_config table")
            
        # Check table structure
        print("\n🔍 Checking table structures:")
        
        # welcome_config structure
        welcome_structure = await db.query("DESCRIBE welcome_config", fetchall=True)
        print("  welcome_config columns:")
        for col in welcome_structure:
            print(f"    - {col['Field']}: {col['Type']}")
            
        # guild_config structure
        guild_structure = await db.query("DESCRIBE guild_config", fetchall=True)
        print("  guild_config columns:")
        for col in guild_structure:
            print(f"    - {col['Field']}: {col['Type']}")
            
        # Recommendations
        print("\n💡 Recommendations:")
        if not welcome_config and not guild_config:
            print("  1. No configuration found. Create a welcome config using the web dashboard.")
            print("  2. Make sure to set a welcome channel and enable welcome messages.")
        elif guild_config and not guild_config.get('welcome_enabled'):
            print("  1. Welcome messages are disabled in guild_config.")
            print("  2. Enable welcome messages and set a welcome channel.")
        elif welcome_config and not welcome_config.get('welcome_enabled'):
            print("  1. Welcome messages are disabled in welcome_config.")
            print("  2. Enable welcome messages and set a welcome channel.")
        elif (welcome_config and not welcome_config.get('welcome_channel')) or (guild_config and not guild_config.get('welcome_channel')):
            print("  1. Welcome channel is not configured.")
            print("  2. Set a welcome channel for welcome messages to work.")
        else:
            print("  1. Configuration looks good.")
            print("  2. Check bot permissions in the welcome channel.")
            print("  3. Ensure the bot can send messages and embeds in the welcome channel.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()
        print("\n✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(debug_welcome_config())
