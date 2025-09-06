import discord
from .command_logger import log_command_usage
from discord.ext import commands, tasks
from discord import app_commands
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class RoleMenuDropdown(discord.ui.Select):
    def __init__(self, bot, menu_data: Dict, options_data: List[Dict]):
        self.bot = bot
        self.menu_data = menu_data
        self.guild_id = menu_data['guild_id']
        
        # Convert database options to Discord select options
        discord_options = []
        for option in options_data:
            discord_options.append(discord.SelectOption(
                label=option['label'],
                value=str(option['role_id']),
                description=option['description'],
                emoji=option['emoji'] if option['emoji'] else None
            ))
        
        super().__init__(
            placeholder=menu_data['placeholder'],
            min_values=menu_data['min_values'],
            max_values=min(menu_data['max_values'], len(discord_options)),
            options=discord_options,
            custom_id=f"role_menu_{menu_data['id']}"  # Add custom_id for persistence
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle role selection from dropdown"""
        try:
            logger.info(f"🔄 Role menu interaction received: User {interaction.user} selected {self.values} from menu {self.menu_data['id']}")
            
            guild = interaction.guild
            member = interaction.user
            
            if not guild or not member:
                logger.error(f"❌ Invalid guild or member in role menu interaction")
                await interaction.response.send_message("❌ Could not process role selection.", ephemeral=True)
                return
            
            selected_role_ids = [int(value) for value in self.values]
            logger.info(f"📝 Selected role IDs: {selected_role_ids}")
            
            # Check bot permissions
            bot_member = guild.get_member(self.bot.user.id)
            if not bot_member:
                logger.error(f"❌ Bot member not found in guild {guild.id}")
                await interaction.response.send_message("❌ Bot member not found.", ephemeral=True)
                return
            
            # Get all roles from this menu for removal logic
            menu_options = await self.bot.db.query(
                "SELECT role_id FROM role_menu_options WHERE menu_id = %s",
                params=(self.menu_data['id'],),
                fetchall=True
            )
            
            if not menu_options:
                logger.error(f"❌ No options found for menu {self.menu_data['id']}")
                await interaction.response.send_message("❌ Menu configuration error.", ephemeral=True)
                return
                
            menu_role_ids = [option['role_id'] for option in menu_options]
            logger.info(f"📋 Menu role IDs: {menu_role_ids}")
            
            # Check if this is a single-selection menu (max_values = 1)
            is_single_selection = self.menu_data.get('max_values', 1) == 1
            
            # Role removal logic depends on selection mode
            roles_to_remove = []
            
            if is_single_selection:
                # Single selection: remove all other roles from this menu that aren't selected
                for role in member.roles:
                    if role.id in menu_role_ids and role.id not in selected_role_ids:
                        if role < bot_member.top_role:  # Check if bot can manage this role
                            roles_to_remove.append(role)
            else:
                # Multiple selection: For true multi-select behavior, we should only remove roles
                # that the user explicitly deselected. However, Discord dropdowns show current selection,
                # so any role from this menu not in the current selection should be removed.
                for role in member.roles:
                    if role.id in menu_role_ids and role.id not in selected_role_ids:
                        if role < bot_member.top_role:
                            roles_to_remove.append(role)
            
            # Add newly selected roles
            roles_to_add = []
            for role_id in selected_role_ids:
                role = guild.get_role(role_id)
                if role and role not in member.roles and role < bot_member.top_role:
                    roles_to_add.append(role)
            
            # Apply role changes
            changes_made = []
            
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="Role menu selection")
                    for role in roles_to_remove:
                        changes_made.append(f"➖ Removed {role.name}")
                except discord.Forbidden:
                    await interaction.response.send_message("❌ I don't have permission to remove some roles.", ephemeral=True)
                    return
                except Exception as e:
                    logger.error(f"Error removing roles: {e}")
            
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Role menu selection")
                    for role in roles_to_add:
                        changes_made.append(f"➕ Added {role.name}")
                except discord.Forbidden:
                    await interaction.response.send_message("❌ I don't have permission to add some roles.", ephemeral=True)
                    return
                except Exception as e:
                    logger.error(f"Error adding roles: {e}")
            
            # Send response
            if changes_made:
                response = "✅ **Role Update Successful!**\n" + "\n".join(changes_made)
            else:
                response = "ℹ️ No role changes were needed."
            
            await interaction.response.send_message(response, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error in role menu callback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await interaction.response.send_message("❌ An error occurred while processing your selection.", ephemeral=True)

class RoleMenuView(discord.ui.View):
    def __init__(self, bot, menu_data: Dict, options_data: List[Dict]):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.menu_data = menu_data
        
        # Add dropdown to view
        if options_data:
            dropdown = RoleMenuDropdown(bot, menu_data, options_data)
            self.add_item(dropdown)

class RoleMenus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_load(self):
        """Load persistent views for existing role menus"""
        try:
            # Wait for database to be connected
            if not self.bot.db.pool:
                logger.info("Waiting for database connection before loading role menu views...")
                await self.bot.db.connect()
            
            # Get all active role menus
            menus = await self.bot.db.query(
                "SELECT * FROM role_menus WHERE message_id IS NOT NULL",
                params=None,
                fetchall=True
            )
            
            if not menus:
                logger.info("No existing role menus found with message IDs")
                return
            
            logger.info(f"Found {len(menus)} role menus with message IDs, loading persistent views...")
            
            for menu in menus:
                # Get menu options
                options = await self.bot.db.query(
                    "SELECT * FROM role_menu_options WHERE menu_id = %s ORDER BY position",
                    params=(menu['id'],),
                    fetchall=True
                )
                
                if options:
                    view = RoleMenuView(self.bot, menu, options)
                    self.bot.add_view(view, message_id=menu['message_id'])
                    logger.info(f"✅ Loaded persistent view for role menu {menu['id']} ({menu['title']})")
                else:
                    logger.warning(f"⚠️  Role menu {menu['id']} has no options, skipping persistent view")
                    
            logger.info(f"✅ Loaded {len(menus)} persistent role menu views")
            
            # Start the background task to check for new role menus
            self.check_new_role_menus.start()
            
        except Exception as e:
            logger.error(f"Error loading role menu views: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
    async def cog_unload(self):
        """Stop background tasks when cog is unloaded"""
        self.check_new_role_menus.cancel()
    
    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def check_new_role_menus(self):
        """Check for role menus that need Discord messages created"""
        try:
            # Find role menus without message IDs
            menus = await self.bot.db.query(
                "SELECT * FROM role_menus WHERE message_id IS NULL",
                params=None,
                fetchall=True
            )
            
            if not menus:
                return
                
            logger.info(f"Found {len(menus)} role menus without Discord messages")
            
            for menu in menus:
                try:
                    # Get menu options
                    options = await self.bot.db.query(
                        "SELECT * FROM role_menu_options WHERE menu_id = %s ORDER BY position",
                        params=(menu['id'],),
                        fetchall=True
                    )
                    
                    if not options:
                        logger.warning(f"Role menu {menu['id']} has no options, skipping")
                        continue
                    
                    # Create the Discord message
                    message = await self.create_or_update_menu_message(menu, options)
                    
                    if message:
                        logger.info(f"✅ Created Discord message for role menu {menu['id']}")
                        
                        # Add persistent view
                        view = RoleMenuView(self.bot, menu, options)
                        self.bot.add_view(view, message_id=message.id)
                    else:
                        logger.error(f"❌ Failed to create Discord message for role menu {menu['id']}")
                        
                except Exception as e:
                    logger.error(f"Error processing role menu {menu['id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in check_new_role_menus task: {e}")
    
    @check_new_role_menus.before_loop
    async def before_check_new_role_menus(self):
        """Wait for bot to be ready before starting the task"""
        await self.bot.wait_until_ready()

    @app_commands.command(name="sync_role_menus", description="Sync role menus from database to Discord (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def sync_role_menus(self, interaction: discord.Interaction):
        """Sync role menus that exist in database but not in Discord"""
        try:
            print(f"🔄 Sync command started by {interaction.user} in guild {interaction.guild.id}")
            await interaction.response.defer()
            
            # Get role menus without message_id (created from dashboard but no Discord message)
            menus = await self.bot.db.query(
                "SELECT * FROM role_menus WHERE guild_id = %s AND message_id IS NULL",
                params=(interaction.guild.id,),
                fetchall=True
            )
            
            print(f"🔍 Found {len(menus) if menus else 0} role menus to sync")
            
            if not menus:
                await interaction.followup.send("✅ All role menus are already synced!", ephemeral=True)
                return
            
            synced_count = 0
            for menu in menus:
                print(f"🔄 Processing menu ID {menu['id']}: {menu['title']}")
                # Get menu options
                options = await self.bot.db.query(
                    "SELECT * FROM role_menu_options WHERE menu_id = %s ORDER BY position",
                    params=(menu['id'],),
                    fetchall=True
                )
                
                print(f"🔍 Found {len(options) if options else 0} options for menu {menu['id']}")
                
                if options:
                    message = await self.create_or_update_menu_message(menu, options)
                    if message:
                        synced_count += 1
                        print(f"✅ Created message {message.id} for menu {menu['id']}")
                        # Add the view to bot for persistence
                        view = RoleMenuView(self.bot, menu, options)
                        self.bot.add_view(view, message_id=message.id)
                    else:
                        print(f"❌ Failed to create message for menu {menu['id']}")
            
            print(f"✅ Sync completed: {synced_count} menus synced")
            await interaction.followup.send(
                f"✅ Synced {synced_count} role menu(s) to Discord!", 
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error syncing role menus: {e}")
            await interaction.followup.send(
                f"❌ Error syncing role menus: {str(e)}", 
                ephemeral=True
            )
    
    async def create_or_update_menu_message(self, menu_data: Dict, options_data: List[Dict]) -> Optional[discord.Message]:
        """Create or update a role menu message"""
        try:
            channel = self.bot.get_channel(menu_data['channel_id'])
            if not channel:
                logger.error(f"Channel {menu_data['channel_id']} not found for menu {menu_data['id']}")
                return None
            
            # Create embed
            color = discord.Color.blue()
            if menu_data['color']:
                try:
                    color_value = menu_data['color'].strip()
                    if color_value.startswith('#'):
                        color_value = color_value[1:]
                    color = discord.Color(int(color_value, 16))
                except:
                    color = discord.Color.blue()
            
            embed = discord.Embed(
                title=menu_data['title'],
                description=menu_data['description'] or "Select a role from the dropdown below:",
                color=color
            )
            
            # Add role information to embed
            if options_data:
                role_list = []
                for option in sorted(options_data, key=lambda x: x['position']):
                    role = channel.guild.get_role(option['role_id'])
                    if role:
                        emoji_str = f"{option['emoji']} " if option['emoji'] else ""
                        desc_str = f" - {option['description']}" if option['description'] else ""
                        role_list.append(f"{emoji_str}**{option['label']}**{desc_str}")
                
                if role_list:
                    embed.add_field(
                        name="Available Roles",
                        value="\n".join(role_list),
                        inline=False
                    )
            
            # Create view with dropdown
            view = RoleMenuView(self.bot, menu_data, options_data)
            
            # Send or update message
            if menu_data.get('message_id'):
                # Try to edit existing message
                try:
                    message = await channel.fetch_message(menu_data['message_id'])
                    await message.edit(embed=embed, view=view)
                    return message
                except discord.NotFound:
                    # Message was deleted, create new one
                    pass
                except Exception as e:
                    logger.error(f"Error editing message: {e}")
            
            # Create new message
            message = await channel.send(embed=embed, view=view)
            
            # Update database with message ID
            await self.bot.db.execute(
                "UPDATE role_menus SET message_id = %s WHERE id = %s",
                (message.id, menu_data['id'])
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating/updating menu message: {e}")
            return None

    async def force_create_menu_message(self, menu_id: int) -> bool:
        """Force create a Discord message for a specific role menu"""
        try:
            # Get menu data
            menu = await self.bot.db.query(
                "SELECT * FROM role_menus WHERE id = %s",
                params=(menu_id,),
                fetchone=True
            )
            
            if not menu:
                logger.error(f"Role menu {menu_id} not found")
                return False
            
            # Get menu options
            options = await self.bot.db.query(
                "SELECT * FROM role_menu_options WHERE menu_id = %s ORDER BY position",
                params=(menu_id,),
                fetchall=True
            )
            
            if not options:
                logger.error(f"Role menu {menu_id} has no options")
                return False
            
            # Create the message
            message = await self.create_or_update_menu_message(menu, options)
            
            if message:
                logger.info(f"✅ Forced creation of Discord message for role menu {menu_id}")
                return True
            else:
                logger.error(f"❌ Failed to force create Discord message for role menu {menu_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error in force_create_menu_message: {e}")
            return False

async def setup(bot):
    await bot.add_cog(RoleMenus(bot))
