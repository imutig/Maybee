"""
Temporary script to add missing database columns.
Run this once to add welcome_title and goodbye_title columns.
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def main():
    """Run database migration"""
    try:
        # Import after adding path
        from main import bot
        
        # Wait for bot to be ready
        await bot.wait_until_ready()
        
        # Get database connection from any cog that has it
        welcome_cog = bot.get_cog('Welcome')
        if not welcome_cog:
            print("❌ Welcome cog not found")
            return
            
        db = welcome_cog.db
        
        print("🔄 Starting database migration...")
        
        # Try to add welcome_title column
        try:
            await db.execute("""
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
        
        # Try to add goodbye_title column
        try:
            await db.execute("""
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
        try:
            result = await db.query("SELECT welcome_title, goodbye_title FROM welcome_config LIMIT 1", fetchone=True)
            print(f"✅ Test query successful: {result}")
        except Exception as e:
            print(f"❌ Test query failed: {e}")
        
        print("✅ Migration completed!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
