import discord
from discord.ext import commands
from discord import app_commands, Embed
from i18n import _

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def get_welcome_config(self, guild_id):
        """Get welcome configuration for a guild"""
        # Try welcome_config table first
        result = await self.db.query(
            "SELECT * FROM welcome_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if result:
            print(f"🔍 DEBUG: Raw welcome_config result: {dict(result) if result else None}")
            # Check if title columns exist, if not add default values
            config_dict = dict(result)
            if 'welcome_title' not in config_dict:
                config_dict['welcome_title'] = '👋 New member!'
            if 'goodbye_title' not in config_dict:  
                config_dict['goodbye_title'] = '👋 Departure'
            return config_dict
            
        # If no welcome_config, check guild_config table for dashboard consistency
        guild_result = await self.db.query(
            "SELECT welcome_channel, welcome_message, welcome_enabled FROM guild_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if guild_result and guild_result.get("welcome_enabled"):
            # Convert guild_config format to welcome_config format
            return {
                "welcome_channel": guild_result.get("welcome_channel"),
                "welcome_message": guild_result.get("welcome_message"),
                "goodbye_channel": None,
                "goodbye_message": None
            }
        
        return {}

    async def save_welcome_config(self, guild_id, **kwargs):
        """Save welcome configuration for a guild"""
        # Check if config exists
        existing = await self.get_welcome_config(guild_id)
        
        if existing:
            # Update existing config
            set_clauses = []
            params = []
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = %s")
                params.append(value)
            
            if set_clauses:
                params.append(guild_id)
                query = f"UPDATE welcome_config SET {', '.join(set_clauses)} WHERE guild_id = %s"
                await self.db.query(query, params)
        else:
            # Insert new config
            columns = ['guild_id'] + list(kwargs.keys())
            values = [guild_id] + list(kwargs.values())
            placeholders = ', '.join(['%s'] * len(values))
            
            query = f"INSERT INTO welcome_config ({', '.join(columns)}) VALUES ({placeholders})"
            await self.db.query(query, values)

    def format_message(self, template: str, member: discord.Member):
        """Format welcome/goodbye message with member and guild information"""
        print(f"🔧 DEBUG: Formatting template: '{template}'")
        print(f"🔧 DEBUG: Member: {member.display_name} ({member.mention})")
        
        result = template\
            .replace("{memberName}", member.display_name)\
            .replace("{memberMention}", member.mention)\
            .replace("{serverName}", member.guild.name)\
            .replace("{memberUsername}", member.name)\
            .replace("{memberTag}", str(member))\
            .replace("{memberCount}", str(member.guild.member_count))\
            .replace("{user}", member.mention)\
            .replace("{server}", member.guild.name)\
            .replace("{username}", member.name)\
            .replace("{displayname}", member.display_name)\
            .replace("{userMention}", member.mention)
        
        print(f"🔧 DEBUG: Formatted result: '{result}'")
        return result

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = member.guild.id
        print(f"🎉 DEBUG: Member joined - {member.display_name} in guild {guild_id}")
        
        config = await self.get_welcome_config(guild_id)
        print(f"🔍 DEBUG: Welcome config for guild {guild_id}: {config}")
        
        # Handle auto-role assignment first
        await self.handle_auto_roles(member, config)
        
        # Then handle welcome message
        await self.send_welcome_message(member, config)

    async def handle_auto_roles(self, member, config):
        """Handle automatic role assignment for new members"""
        try:
            auto_role_enabled = config.get("auto_role_enabled", False)
            auto_role_ids = config.get("auto_role_ids")
            
            print(f"🔧 DEBUG: Auto-role enabled: {auto_role_enabled}")
            print(f"🔧 DEBUG: Auto-role IDs: {auto_role_ids}")
            
            if not auto_role_enabled or not auto_role_ids:
                print(f"⚠️ DEBUG: Auto-role disabled or no roles configured")
                return
            
            # Parse role IDs if they're stored as JSON string
            if isinstance(auto_role_ids, str):
                import json
                try:
                    auto_role_ids = json.loads(auto_role_ids)
                except json.JSONDecodeError:
                    print(f"❌ DEBUG: Failed to parse auto_role_ids JSON: {auto_role_ids}")
                    return
            
            if not isinstance(auto_role_ids, list):
                print(f"❌ DEBUG: auto_role_ids is not a list: {type(auto_role_ids)}")
                return
            
            # Assign roles to the new member
            roles_assigned = []
            roles_failed = []
            
            for role_id in auto_role_ids:
                try:
                    role = member.guild.get_role(int(role_id))
                    if role:
                        # Check if bot has permission to assign this role
                        if role.position < member.guild.me.top_role.position:
                            await member.add_roles(role, reason="Auto-role assignment on member join")
                            roles_assigned.append(role.name)
                            print(f"✅ DEBUG: Assigned role {role.name} to {member.display_name}")
                        else:
                            roles_failed.append(f"{role.name} (insufficient permissions)")
                            print(f"❌ DEBUG: Cannot assign role {role.name} - insufficient permissions")
                    else:
                        roles_failed.append(f"Role ID {role_id} (not found)")
                        print(f"❌ DEBUG: Role with ID {role_id} not found")
                except Exception as e:
                    roles_failed.append(f"Role ID {role_id} (error: {str(e)})")
                    print(f"❌ DEBUG: Error assigning role {role_id}: {e}")
            
            if roles_assigned:
                print(f"🎉 DEBUG: Successfully assigned {len(roles_assigned)} roles to {member.display_name}: {', '.join(roles_assigned)}")
            
            if roles_failed:
                print(f"⚠️ DEBUG: Failed to assign {len(roles_failed)} roles to {member.display_name}: {', '.join(roles_failed)}")
                
        except Exception as e:
            print(f"❌ DEBUG: Error in auto-role assignment for {member.display_name}: {e}")

    async def send_welcome_message(self, member, config):
        """Send welcome message to the configured channel"""
        channel_id = config.get("welcome_channel")
        print(f"📢 DEBUG: Welcome channel ID: {channel_id}")
        
    async def send_welcome_message(self, member, config):
        """Send welcome message to the configured channel"""
        channel_id = config.get("welcome_channel")
        print(f"📢 DEBUG: Welcome channel ID: {channel_id}")
        
        guild_id = member.guild.id
        
        # Use configured message or default translation
        message = config.get("welcome_message")
        if not message:
            message = _("welcome_system.default_welcome_message", member.id, guild_id)
        print(f"💬 DEBUG: Welcome message: {message}")

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            print(f"🏠 DEBUG: Welcome channel object: {channel}")
            if channel:
                # Use custom title or default
                welcome_title = config.get("welcome_title", "👋 New member!")
                print(f"🏷️ DEBUG: Raw welcome title: '{welcome_title}'")
                
                # Format the title with placeholders
                formatted_title = self.format_message(welcome_title, member)
                print(f"🏷️ DEBUG: Formatted welcome title: '{formatted_title}'")
                
                # Format the message with placeholders
                formatted_message = self.format_message(message, member)
                print(f"💬 DEBUG: Formatted welcome message: '{formatted_message}'")
                
                print(f"🔍 DEBUG: Full config: {config}")
                embed = Embed(
                    title=formatted_title,
                    description=formatted_message,
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                
                # Add custom fields if configured
                welcome_fields = config.get("welcome_fields")
                if welcome_fields:
                    try:
                        import json
                        if isinstance(welcome_fields, str):
                            fields_data = json.loads(welcome_fields)
                        else:
                            fields_data = welcome_fields
                            
                        for field in fields_data:
                            if isinstance(field, dict) and "name" in field and "value" in field:
                                embed.add_field(
                                    name=self.format_message(field["name"], member),
                                    value=self.format_message(field["value"], member),
                                    inline=field.get("inline", False)
                                )
                    except Exception as e:
                        print(f"⚠️ DEBUG: Error processing welcome fields: {e}")
                
                try:
                    await channel.send(embed=embed)
                    print(f"✅ DEBUG: Welcome message sent successfully to {channel.name}")
                except Exception as e:
                    print(f"❌ DEBUG: Failed to send welcome message: {e}")
            else:
                print(f"❌ DEBUG: Could not find welcome channel with ID {channel_id}")
        else:
            print(f"⚠️ DEBUG: No welcome channel configured for guild {guild_id}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = member.guild.id
        config = await self.get_welcome_config(guild_id)
        
        channel_id = config.get("goodbye_channel")
        # Use configured message or default translation
        message = config.get("goodbye_message")
        if not message:
            message = _("welcome_system.default_goodbye_message", member.id, guild_id)

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                # Use custom title or default
                goodbye_title = config.get("goodbye_title", "👋 Departure")
                print(f"🏷️ DEBUG: Raw goodbye title: '{goodbye_title}'")
                
                # Format the title with placeholders
                formatted_title = self.format_message(goodbye_title, member)
                print(f"🏷️ DEBUG: Formatted goodbye title: '{formatted_title}'")
                
                # Format the message with placeholders
                formatted_message = self.format_message(message, member)
                print(f"💬 DEBUG: Formatted goodbye message: '{formatted_message}'")
                
                embed = Embed(
                    title=formatted_title,
                    description=formatted_message,
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                
                # Add custom fields if configured
                goodbye_fields = config.get("goodbye_fields")
                if goodbye_fields:
                    try:
                        import json
                        if isinstance(goodbye_fields, str):
                            fields_data = json.loads(goodbye_fields)
                        else:
                            fields_data = goodbye_fields
                            
                        for field in fields_data:
                            if isinstance(field, dict) and "name" in field and "value" in field:
                                embed.add_field(
                                    name=self.format_message(field["name"], member),
                                    value=self.format_message(field["value"], member),
                                    inline=field.get("inline", False)
                                )
                    except Exception as e:
                        print(f"⚠️ DEBUG: Error processing goodbye fields: {e}")
                
                await channel.send(embed=embed)

    # Configuration commands removed - use unified /config command instead
    # @app_commands.command(name="configwelcome", description="Configurer le message de bienvenue")
    # @app_commands.describe(channel="Salon de bienvenue", message="Message avec {memberMention}, {memberName}, {serverName}")
    # async def configwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    #     guild_id = interaction.guild.id
    #     await self.save_welcome_config(guild_id, welcome_channel=channel.id, welcome_message=message)
    #     await interaction.response.send_message("✅ Message de bienvenue configuré.", ephemeral=True)

    # @app_commands.command(name="configgoodbye", description="Configurer le message d'au revoir")
    # @app_commands.describe(channel="Salon d'au revoir", message="Message avec {memberName}, {serverName}")
    # async def configgoodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    #     guild_id = interaction.guild.id
    #     await self.save_welcome_config(guild_id, goodbye_channel=channel.id, goodbye_message=message)
    #     await interaction.response.send_message("✅ Message d'au revoir configuré.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
