#!/usr/bin/env python3
"""
Test script to verify Discord bot token and permissions
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_discord_token():
    """Test Discord bot token and permissions"""
    print("🔍 Testing Discord Bot Token and Permissions")
    print("=" * 50)
    
    # Get token
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ No DISCORD_TOKEN found in environment variables")
        return False
    
    print(f"✅ Token found (length: {len(token)})")
    print(f"🔍 Token starts with: {token[:10]}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {token}"}
            
            # Test 1: Get bot user info
            print("\n📋 Test 1: Getting bot user info...")
            response = await client.get("https://discord.com/api/users/@me", headers=headers)
            
            if response.status_code == 200:
                bot_data = response.json()
                print(f"✅ Bot info retrieved successfully")
                print(f"   - Bot ID: {bot_data['id']}")
                print(f"   - Bot Username: {bot_data['username']}")
                print(f"   - Bot Discriminator: {bot_data.get('discriminator', 'N/A')}")
            else:
                print(f"❌ Failed to get bot info: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
            
            # Test 2: Get bot guilds
            print("\n📋 Test 2: Getting bot guilds...")
            guilds_response = await client.get("https://discord.com/api/users/@me/guilds", headers=headers)
            
            if guilds_response.status_code == 200:
                guilds = guilds_response.json()
                print(f"✅ Bot guilds retrieved successfully")
                print(f"   - Total guilds: {len(guilds)}")
                
                for i, guild in enumerate(guilds[:5], 1):  # Show first 5 guilds
                    print(f"   {i}. {guild['name']} (ID: {guild['id']})")
                    print(f"      - Owner: {guild.get('owner', False)}")
                    print(f"      - Permissions: {guild.get('permissions', 'N/A')}")
                
                if len(guilds) > 5:
                    print(f"   ... and {len(guilds) - 5} more guilds")
                    
                return True
            else:
                print(f"❌ Failed to get bot guilds: {guilds_response.status_code}")
                print(f"   Error: {guilds_response.text}")
                return False
                
    except httpx.ReadTimeout:
        print("❌ Timeout error when connecting to Discord API")
        return False
    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_specific_guild(guild_id: str):
    """Test access to a specific guild"""
    print(f"\n🔍 Testing access to guild {guild_id}...")
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ No DISCORD_TOKEN found")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bot {token}"}
            
            # Test guild info
            response = await client.get(f"https://discord.com/api/guilds/{guild_id}", headers=headers)
            
            if response.status_code == 200:
                guild_data = response.json()
                print(f"✅ Guild access successful")
                print(f"   - Guild Name: {guild_data['name']}")
                print(f"   - Member Count: {guild_data.get('approximate_member_count', 'N/A')}")
                print(f"   - Bot Permissions: {guild_data.get('permissions', 'N/A')}")
                return True
            else:
                print(f"❌ Guild access failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing guild access: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Discord Bot Token Test Suite")
    print("=" * 50)
    
    # Test basic token functionality
    success = await test_discord_token()
    
    if success:
        print("\n✅ All basic tests passed!")
        
        # Test specific guild if provided
        guild_id = input("\n🔍 Enter a guild ID to test (or press Enter to skip): ").strip()
        if guild_id:
            await test_specific_guild(guild_id)
    else:
        print("\n❌ Basic tests failed. Please check your token and permissions.")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
