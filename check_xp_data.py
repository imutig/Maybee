#!/usr/bin/env python3
"""
Simple XP data checker
"""

import asyncio
import aiomysql

async def check_xp_data():
    try:
        conn = await aiomysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            db='MaybeBot',
            charset='utf8mb4'
        )
        
        cur = await conn.cursor(aiomysql.DictCursor)
        
        print('🔍 Checking XP data...')
        await cur.execute('SELECT user_id, xp, text_xp, voice_xp FROM xp_data ORDER BY xp DESC LIMIT 10')
        rows = await cur.fetchall()
        
        if not rows:
            print('❌ No XP data found')
        else:
            print(f'📊 Found {len(rows)} XP records:')
            for row in rows:
                print(f'  User {row["user_id"]}: Total={row["xp"]}, Text={row["text_xp"]}, Voice={row["voice_xp"]}')
        
        # Check if there are records with 0 text_xp and voice_xp but non-zero xp
        await cur.execute('SELECT COUNT(*) as count FROM xp_data WHERE xp > 0 AND text_xp = 0 AND voice_xp = 0')
        problematic = await cur.fetchone()
        print(f'⚠️  Records with XP but no text/voice breakdown: {problematic["count"]}')
        
        await cur.close()
        conn.close()
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_xp_data())
