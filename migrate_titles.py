#!/usr/bin/env python3
"""
Migration script to add welcome_title and goodbye_title columns
"""
import asyncio
import sys
import os
sys.path.append('.')

from db import Database
from dotenv import load_dotenv

async def migrate_database():
    """Add title columns to welcome_config table"""
    try:
        print("🔄 Starting database migration...")
        load_dotenv()
        
        # Initialize database connection
        db = Database(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_NAME'),
            debug=True
        )
        
        await db.connect()
        
        # Check current table structure
        try:
            columns = await db.query("SHOW COLUMNS FROM welcome_config")
            column_names = [col['Field'] for col in columns]
            print(f"📋 Current columns: {column_names}")
            
            # Add welcome_title column if missing
            if 'welcome_title' not in column_names:
                print("➕ Adding welcome_title column...")
                await db.execute("""
                    ALTER TABLE welcome_config 
                    ADD COLUMN welcome_title VARCHAR(256) DEFAULT '👋 New member!' 
                    AFTER welcome_channel
                """)
                print("✅ welcome_title column added")
            else:
                print("ℹ️ welcome_title column already exists")
            
            # Add goodbye_title column if missing
            if 'goodbye_title' not in column_names:
                print("➕ Adding goodbye_title column...")
                await db.execute("""
                    ALTER TABLE welcome_config 
                    ADD COLUMN goodbye_title VARCHAR(256) DEFAULT '👋 Departure' 
                    AFTER goodbye_channel
                """)
                print("✅ goodbye_title column added")
            else:
                print("ℹ️ goodbye_title column already exists")
            
            # Show updated table structure
            columns = await db.query("SHOW COLUMNS FROM welcome_config")
            column_names = [col['Field'] for col in columns]
            print(f"📋 Updated columns: {column_names}")
            
            # Test the new columns
            test_result = await db.query("SELECT guild_id, welcome_title, goodbye_title FROM welcome_config LIMIT 3")
            print(f"🧪 Test query result: {test_result}")
            
        except Exception as e:
            print(f"❌ Migration error: {e}")
            import traceback
            traceback.print_exc()
        
        await db.close()
        print("✅ Migration completed")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_database())
