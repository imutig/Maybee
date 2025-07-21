#!/usr/bin/env python3
"""
Cleanup script to remove invalid test data from ticket system tables.
This will remove any entries with literal field names instead of actual values.
"""

import asyncio
import aiomysql
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def cleanup_ticket_data():
    """Clean up invalid ticket data from the database"""
    
    # Database connection config (same as main bot)
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': 3306,
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'db': os.getenv('DB_NAME'),
        'charset': 'utf8mb4'
    }
    
    try:
        # Connect to database
        connection = await aiomysql.connect(**db_config)
        cursor = await connection.cursor()
        
        print("🔌 Connected to database")
        
        # Check current ticket data
        await cursor.execute("SELECT id, category_id, ping_roles FROM ticket_buttons")
        buttons = await cursor.fetchall()
        
        print(f"📊 Found {len(buttons)} ticket buttons")
        
        invalid_buttons = []
        for button_id, category_id, ping_roles in buttons:
            is_invalid = False
            
            # Check if category_id is a literal string instead of a number
            if category_id and not str(category_id).isdigit():
                print(f"❌ Invalid category_id: {category_id}")
                is_invalid = True
            
            # Check if ping_roles is a literal string instead of JSON
            if ping_roles and ping_roles in ['ping_roles', '["ping_roles"]']:
                print(f"❌ Invalid ping_roles: {ping_roles}")
                is_invalid = True
                
            if is_invalid:
                invalid_buttons.append(button_id)
        
        if invalid_buttons:
            print(f"🗑️  Found {len(invalid_buttons)} invalid buttons to clean up")
            
            # Delete invalid buttons
            for button_id in invalid_buttons:
                await cursor.execute("DELETE FROM ticket_buttons WHERE id = %s", (button_id,))
                print(f"🗑️  Deleted invalid button ID: {button_id}")
            
            # Check for orphaned panels (panels with no buttons)
            await cursor.execute("""
                SELECT tp.id, tp.panel_name 
                FROM ticket_panels tp 
                LEFT JOIN ticket_buttons tb ON tp.id = tb.panel_id 
                WHERE tb.panel_id IS NULL
            """)
            orphaned_panels = await cursor.fetchall()
            
            if orphaned_panels:
                print(f"🗑️  Found {len(orphaned_panels)} orphaned panels to clean up")
                for panel_id, panel_name in orphaned_panels:
                    await cursor.execute("DELETE FROM ticket_panels WHERE id = %s", (panel_id,))
                    print(f"🗑️  Deleted orphaned panel: {panel_name} (ID: {panel_id})")
            
            # Commit changes
            await connection.commit()
            print("✅ Database cleanup completed successfully")
            
        else:
            print("✅ No invalid data found - database is clean")
        
        # Show remaining valid data
        await cursor.execute("""
            SELECT tp.panel_name, tb.button_label, tb.category_id 
            FROM ticket_panels tp 
            JOIN ticket_buttons tb ON tp.id = tb.panel_id
        """)
        valid_data = await cursor.fetchall()
        
        if valid_data:
            print(f"📋 Remaining valid ticket configurations:")
            for panel_name, button_label, category_id in valid_data:
                print(f"   - Panel: {panel_name}, Button: {button_label}, Category: {category_id}")
        else:
            print("📋 No ticket configurations remain - ready for fresh setup")
        
        await cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_ticket_data())
