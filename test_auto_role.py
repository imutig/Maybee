#!/usr/bin/env python3
"""
Simple test script to verify auto-role database setup
"""

import asyncio
import json
from web.main import database, init_database

async def test_auto_role_setup():
    """Test auto-role database setup"""
    print("🔧 Testing auto-role database setup...")
    
    try:
        # Initialize database
        await init_database()
        print("✅ Database initialized")
        
        # Test guild config table structure
        result = await database.fetch_one("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'guild_config'
            AND COLUMN_NAME IN ('auto_role_enabled', 'auto_role_ids')
        """)
        
        if result:
            print("✅ Auto-role columns exist in guild_config table")
        else:
            print("❌ Auto-role columns missing from guild_config table")
            return
        
        # Test welcome config table structure  
        result = await database.fetch_one("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'welcome_config'
            AND COLUMN_NAME IN ('auto_role_enabled', 'auto_role_ids')
        """)
        
        if result:
            print("✅ Auto-role columns exist in welcome_config table")
        else:
            print("❌ Auto-role columns missing from welcome_config table")
            return
            
        # Test inserting sample data
        test_guild_id = "123456789012345678"
        test_roles = ["987654321098765432", "876543210987654321"]
        
        await database.execute("""
            INSERT INTO guild_config 
            (guild_id, auto_role_enabled, auto_role_ids, updated_at)
            VALUES (%s, %s, %s, NOW()) 
            ON DUPLICATE KEY UPDATE
            auto_role_enabled = VALUES(auto_role_enabled),
            auto_role_ids = VALUES(auto_role_ids),
            updated_at = VALUES(updated_at)
        """, (test_guild_id, True, json.dumps(test_roles)))
        
        print("✅ Successfully inserted test auto-role configuration")
        
        # Test retrieving the data
        result = await database.fetch_one(
            "SELECT auto_role_enabled, auto_role_ids FROM guild_config WHERE guild_id = %s",
            (test_guild_id,)
        )
        
        if result:
            auto_role_enabled = result['auto_role_enabled']
            auto_role_ids = json.loads(result['auto_role_ids']) if result['auto_role_ids'] else []
            print(f"✅ Retrieved auto-role config: enabled={auto_role_enabled}, roles={auto_role_ids}")
        else:
            print("❌ Failed to retrieve auto-role configuration")
            return
            
        # Clean up test data
        await database.execute(
            "DELETE FROM guild_config WHERE guild_id = %s",
            (test_guild_id,)
        )
        print("✅ Cleaned up test data")
        
        print("🎉 Auto-role setup test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_auto_role_setup())
