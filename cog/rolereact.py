import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import asyncio
from i18n import _

logger = logging.getLogger(__name__)

class RoleReactView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Create New Role Reaction", style=discord.ButtonStyle.primary, emoji="➕")
    async def create_new(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📝 Create Role Reaction Message",
            description="**Step 1:** Reply to this message with the title and description for your role reaction message.\n\n**Format:**\n```\nTitle: Your Title Here\nDescription: Your description here\n```\n\n**Example:**\n```\nTitle: Get Your Roles!\nDescription: Click the reactions below to get your roles\n```",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Wait for user response
        try:
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            # Parse the message
            content = msg.content
            title_match = re.search(r'Title:\s*(.+)', content, re.IGNORECASE)
            desc_match = re.search(r'Description:\s*(.+)', content, re.IGNORECASE | re.DOTALL)
            
            if not title_match:
                await interaction.followup.send("❌ Please provide a title using the format: `Title: Your Title Here`", ephemeral=True)
                return
            
            title = title_match.group(1).strip()
            description = desc_match.group(1).strip() if desc_match else "Click the reactions below to get your roles"
            
            # Clean up description if it contains other fields
            if desc_match:
                description = description.split('\n')[0].strip()
            
            # Delete user's message
            try:
                await msg.delete()
            except:
                pass
            
            # Start role collection process
            await self.collect_roles(interaction, title, description)
            
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Timed out waiting for response.", ephemeral=True)
    
    async def collect_roles(self, interaction: discord.Interaction, title: str, description: str):
        embed = discord.Embed(
            title="🎭 Add Role Reactions",
            description=f"**Message Title:** {title}\n**Description:** {description}\n\n**Step 2:** Add reactions one by one using this format:\n```\nEmoji: 🎮\nRole: @Gaming\n```\n\nOr:\n```\nEmoji: 🎨\nRole: Artist\n```\n\n**Type 'done' when finished adding all reactions.**",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        reactions = []
        
        while True:
            try:
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel
                
                msg = await self.bot.wait_for('message', timeout=120.0, check=check)
                
                if msg.content.lower() == 'done':
                    await msg.delete()
                    break
                
                # Parse emoji and role
                content = msg.content
                emoji_match = re.search(r'Emoji:\s*(.+)', content, re.IGNORECASE)
                role_match = re.search(r'Role:\s*(.+)', content, re.IGNORECASE)
                
                if not emoji_match or not role_match:
                    await interaction.followup.send("❌ Please use the format:\n```\nEmoji: 🎮\nRole: @Gaming\n```", ephemeral=True)
                    await msg.delete()
                    continue
                
                emoji = emoji_match.group(1).strip()
                role_input = role_match.group(1).strip()
                
                # Find the role
                role = None
                
                # Try to find by mention
                role_mention_match = re.search(r'<@&(\d+)>', role_input)
                if role_mention_match:
                    role_id = int(role_mention_match.group(1))
                    role = interaction.guild.get_role(role_id)
                
                # Try to find by name
                if not role:
                    role = discord.utils.get(interaction.guild.roles, name=role_input)
                
                # Try to find by ID
                if not role and role_input.isdigit():
                    role = interaction.guild.get_role(int(role_input))
                
                if not role:
                    await interaction.followup.send(f"❌ Role '{role_input}' not found. Please check the role name or mention.", ephemeral=True)
                    await msg.delete()
                    continue
                
                reactions.append((emoji, role))
                await interaction.followup.send(f"✅ Added: {emoji} → {role.mention}", ephemeral=True)
                await msg.delete()
                
            except asyncio.TimeoutError:
                await interaction.followup.send("⏱️ Timed out. Creating message with current reactions.", ephemeral=True)
                break
        
        if not reactions:
            await interaction.followup.send("❌ No reactions added. Cancelled.", ephemeral=True)
            return
        
        # Create the role reaction message
        await self.create_role_message(interaction, title, description, reactions)
    
    async def create_role_message(self, interaction: discord.Interaction, title: str, description: str, reactions: list):
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        # Add reactions field
        reactions_text = "\n".join([f"{emoji} → {role.mention}" for emoji, role in reactions])
        embed.add_field(
            name="Available Reactions",
            value=reactions_text,
            inline=False
        )
        
        # Send the message
        message = await interaction.channel.send(embed=embed)
        
        # Add reactions to the message
        for emoji, role in reactions:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                logger.error(f"Failed to add reaction {emoji}")
        
        # Save to database
        for emoji, role in reactions:
            await self.bot.db.execute(
                "INSERT INTO role_reactions (guild_id, message_id, emoji, role_id) VALUES (%s, %s, %s, %s)",
                (self.guild_id, message.id, emoji, role.id)
            )
        
        await interaction.followup.send(f"✅ Role reaction message created with {len(reactions)} reactions!", ephemeral=True)
    
    @discord.ui.button(label="View All Configurations", style=discord.ButtonStyle.secondary, emoji="👀")
    async def view_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_all_configurations(interaction)
    
    @discord.ui.button(label="Edit Existing", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_existing_messages(interaction)
    
    async def show_existing_messages(self, interaction: discord.Interaction):
        # Get all unique messages with role reactions in this guild
        query = """
        SELECT DISTINCT message_id, COUNT(*) as reaction_count 
        FROM role_reactions 
        WHERE guild_id = %s 
        GROUP BY message_id
        """
        result = await self.bot.db.query(query, (self.guild_id,), fetchall=True)
        
        if not result:
            await interaction.response.send_message(
                "❌ No role reaction messages found. Create one first!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📝 Existing Role Reaction Messages",
            description="Select a message to edit its reactions:",
            color=discord.Color.blue()
        )
        
        message_info = []
        for message_id, count in result:
            try:
                # Try to find the message in the guild channels
                message = None
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(message_id)
                        break
                    except:
                        continue
                
                if message:
                    channel_mention = message.channel.mention
                    embed.add_field(
                        name=f"Message in {channel_mention}",
                        value=f"ID: `{message_id}`\nReactions: {count}\n[Jump to message]({message.jump_url})",
                        inline=True
                    )
                    message_info.append(message_id)
                else:
                    embed.add_field(
                        name=f"Message ID: {message_id}",
                        value=f"Reactions: {count}\n⚠️ Message not found",
                        inline=True
                    )
            except Exception as e:
                logger.error(f"Error fetching message {message_id}: {e}")
        
        view = EditMessageSelectView(self.bot, self.guild_id, message_info)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_all_configurations(self, interaction: discord.Interaction):
        query = "SELECT message_id, emoji, role_id FROM role_reactions WHERE guild_id = %s ORDER BY message_id"
        result = await self.bot.db.query(query, (self.guild_id,), fetchall=True)
        
        if not result:
            await interaction.response.send_message(
                "❌ No role reactions configured.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📊 All Role Reaction Configurations",
            description="Here are all your configured role reactions:",
            color=discord.Color.green()
        )
        
        current_message_id = None
        message_reactions = []
        
        for message_id, emoji, role_id in result:
            if current_message_id != message_id:
                if current_message_id is not None:
                    embed.add_field(
                        name=f"Message ID: {current_message_id}",
                        value="\n".join(message_reactions),
                        inline=False
                    )
                current_message_id = message_id
                message_reactions = []
            
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else f"Role ID: {role_id}"
            message_reactions.append(f"{emoji} → {role_name}")
        
        if current_message_id is not None:
            embed.add_field(
                name=f"Message ID: {current_message_id}",
                value="\n".join(message_reactions),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class EditMessageSelectView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_ids: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.message_ids = message_ids
        self.add_item(EditMessageSelect(bot, guild_id, message_ids))

class EditMessageSelect(discord.ui.Select):
    def __init__(self, bot, guild_id: int, message_ids: list):
        self.bot = bot
        self.guild_id = guild_id
        
        options = []
        for i, message_id in enumerate(message_ids[:25]):  # Discord limit
            options.append(discord.SelectOption(
                label=f"Message {i+1}",
                value=str(message_id),
                description=f"Message ID: {message_id}"
            ))
        
        super().__init__(placeholder="Select a message to edit...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        message_id = int(self.values[0])
        view = EditMessageOptionsView(self.bot, self.guild_id, message_id)
        
        embed = discord.Embed(
            title="✏️ Edit Role Reaction Message",
            description=f"Message ID: {message_id}\nChoose what you'd like to do:",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class EditMessageOptionsView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id  
        self.message_id = message_id
    
    @discord.ui.button(label="Add Reaction", style=discord.ButtonStyle.success, emoji="➕")
    async def add_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="➕ Add New Reaction",
            description="Add a new reaction to this message using this format:\n```\nEmoji: 🎮\nRole: @Gaming\n```\n\nReply with the emoji and role information.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        try:
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            # Parse emoji and role
            content = msg.content
            emoji_match = re.search(r'Emoji:\s*(.+)', content, re.IGNORECASE)
            role_match = re.search(r'Role:\s*(.+)', content, re.IGNORECASE)
            
            if not emoji_match or not role_match:
                await interaction.followup.send("❌ Please use the format:\n```\nEmoji: 🎮\nRole: @Gaming\n```", ephemeral=True)
                await msg.delete()
                return
            
            emoji = emoji_match.group(1).strip()
            role_input = role_match.group(1).strip()
            
            # Find the role
            role = None
            
            # Try to find by mention
            role_mention_match = re.search(r'<@&(\d+)>', role_input)
            if role_mention_match:
                role_id = int(role_mention_match.group(1))
                role = interaction.guild.get_role(role_id)
            
            # Try to find by name
            if not role:
                role = discord.utils.get(interaction.guild.roles, name=role_input)
            
            # Try to find by ID
            if not role and role_input.isdigit():
                role = interaction.guild.get_role(int(role_input))
            
            if not role:
                await interaction.followup.send(f"❌ Role '{role_input}' not found. Please check the role name or mention.", ephemeral=True)
                await msg.delete()
                return
            
            # Add to database
            await self.bot.db.execute(
                "INSERT INTO role_reactions (guild_id, message_id, emoji, role_id) VALUES (%s, %s, %s, %s)",
                (self.guild_id, self.message_id, emoji, role.id)
            )
            
            # Add reaction to the actual message
            try:
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(self.message_id)
                        await message.add_reaction(emoji)
                        break
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error adding reaction {emoji}: {e}")
            
            await interaction.followup.send(f"✅ Added: {emoji} → {role.mention}", ephemeral=True)
            await msg.delete()
            
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Timed out waiting for response.", ephemeral=True)
    
    @discord.ui.button(label="Remove Reaction", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_reactions_to_remove(interaction)
    
    @discord.ui.button(label="Remove All Reactions", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_all_reactions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.execute("DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s", (self.guild_id, self.message_id))
        
        # Remove all reactions from the actual message
        try:
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(self.message_id)
                    await message.clear_reactions()
                    break
                except:
                    continue
        except Exception as e:
            logger.error(f"Error clearing reactions: {e}")
        
        await interaction.response.send_message(
            "✅ All reactions removed from the message!",
            ephemeral=True
        )
    
    async def show_reactions_to_remove(self, interaction: discord.Interaction):
        query = "SELECT emoji, role_id FROM role_reactions WHERE guild_id = %s AND message_id = %s"
        result = await self.bot.db.query(query, (self.guild_id, self.message_id), fetchall=True)
        
        if not result:
            await interaction.response.send_message(
                "❌ No reactions found for this message.",
                ephemeral=True
            )
            return
        
        options = []
        for emoji, role_id in result:
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else f"Role ID: {role_id}"
            options.append(discord.SelectOption(
                label=f"{emoji} → {role_name}",
                value=f"{emoji}|{role_id}",
                emoji=emoji
            ))
        
        view = RemoveReactionView(self.bot, self.guild_id, self.message_id, options)
        await interaction.response.send_message(
            "Select the reactions you want to remove:",
            view=view,
            ephemeral=True
        )


class RemoveReactionView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_id: int, options: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id
        self.add_item(RemoveReactionSelect(bot, guild_id, message_id, options))

class RemoveReactionSelect(discord.ui.Select):
    def __init__(self, bot, guild_id: int, message_id: int, options: list):
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id
        super().__init__(placeholder="Select reactions to remove...", options=options, max_values=len(options))
    
    async def callback(self, interaction: discord.Interaction):
        removed_reactions = []
        
        for value in self.values:
            emoji, role_id = value.split("|")
            await self.bot.db.execute(
                "DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s AND emoji = %s",
                (self.guild_id, self.message_id, emoji)
            )
            
            # Remove the reaction from the actual message
            try:
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(self.message_id)
                        await message.remove_reaction(emoji, interaction.client.user)
                        break
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error removing reaction {emoji}: {e}")
            
            role = interaction.guild.get_role(int(role_id))
            role_name = role.name if role else f"Role ID: {role_id}"
            removed_reactions.append(f"{emoji} → {role_name}")
        
        await interaction.response.send_message(
            f"✅ Reactions removed: {', '.join(removed_reactions)}",
            ephemeral=True
        )
    
    async def show_existing_messages(self, interaction: discord.Interaction):
        # Get all unique messages with role reactions in this guild
        query = """
        SELECT DISTINCT message_id, COUNT(*) as reaction_count 
        FROM role_reactions 
        WHERE guild_id = %s 
        GROUP BY message_id
        """
        result = await self.bot.db.query(query, (self.guild_id,), fetchall=True)
        
        if not result:
            await interaction.response.send_message(
                _("role_reactions.no_messages", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=_("role_reactions.existing_messages.title", interaction.user.id, self.guild_id),
            description=_("role_reactions.existing_messages.description", interaction.user.id, self.guild_id),
            color=discord.Color.blue()
        )
        
        message_info = []
        for message_id, count in result:
            try:
                # Try to find the message in the guild channels
                message = None
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(message_id)
                        break
                    except:
                        continue
                
                if message:
                    channel_mention = message.channel.mention
                    embed.add_field(
                        name=f"Message in {channel_mention}",
                        value=f"ID: `{message_id}`\nReactions: {count}\n[Jump to message]({message.jump_url})",
                        inline=True
                    )
                    message_info.append(message_id)
                else:
                    embed.add_field(
                        name=f"Message ID: {message_id}",
                        value=f"Reactions: {count}\n⚠️ Message not found",
                        inline=True
                    )
            except Exception as e:
                logger.error(f"Error fetching message {message_id}: {e}")
        
        view = EditMessageSelectView(self.bot, self.guild_id, message_info)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_all_configurations(self, interaction: discord.Interaction):
        query = "SELECT message_id, emoji, role_id FROM role_reactions WHERE guild_id = %s ORDER BY message_id"
        result = await self.bot.db.query(query, (self.guild_id,), fetchall=True)
        
        if not result:
            await interaction.response.send_message(
                _("role_reactions.no_configs", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=_("role_reactions.all_configs.title", interaction.user.id, self.guild_id),
            description=_("role_reactions.all_configs.description", interaction.user.id, self.guild_id),
            color=discord.Color.green()
        )
        
        current_message_id = None
        message_reactions = []
        
        for message_id, emoji, role_id in result:
            if current_message_id != message_id:
                if current_message_id is not None:
                    embed.add_field(
                        name=f"Message ID: {current_message_id}",
                        value="\n".join(message_reactions),
                        inline=False
                    )
                current_message_id = message_id
                message_reactions = []
            
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else f"Role ID: {role_id}"
            message_reactions.append(f"{emoji} → {role_name}")
        
        if current_message_id is not None:
            embed.add_field(
                name=f"Message ID: {current_message_id}",
                value="\n".join(message_reactions),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EditMessageSelectView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_ids: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.message_ids = message_ids
        self.add_item(EditMessageSelect(bot, guild_id, message_ids))

class EditMessageSelect(discord.ui.Select):
    def __init__(self, bot, guild_id: int, message_ids: list):
        self.bot = bot
        self.guild_id = guild_id
        
        options = []
        for i, message_id in enumerate(message_ids[:25]):  # Discord limit
            options.append(discord.SelectOption(
                label=f"Message {i+1}",
                value=str(message_id),
                description=f"Message ID: {message_id}"
            ))
        
        super().__init__(placeholder="Select a message to edit...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        message_id = int(self.values[0])
        view = EditMessageOptionsView(self.bot, self.guild_id, message_id)
        
        embed = discord.Embed(
            title=_("role_reactions.edit_message.title", interaction.user.id, self.guild_id),
            description=_("role_reactions.edit_message.description", interaction.user.id, self.guild_id, message_id=message_id),
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class EditMessageOptionsView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id  
        self.message_id = message_id
    
    @discord.ui.button(label="Add Reaction", style=discord.ButtonStyle.success, emoji="➕")
    async def add_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="➕ Add New Reaction",
            description="Add a new reaction to this message using this format:\n```\nEmoji: 🎮\nRole: @Gaming\n```\n\nReply with the emoji and role information.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        try:
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            # Parse emoji and role
            content = msg.content
            emoji_match = re.search(r'Emoji:\s*(.+)', content, re.IGNORECASE)
            role_match = re.search(r'Role:\s*(.+)', content, re.IGNORECASE)
            
            if not emoji_match or not role_match:
                await interaction.followup.send("❌ Please use the format:\n```\nEmoji: 🎮\nRole: @Gaming\n```", ephemeral=True)
                await msg.delete()
                return
            
            emoji = emoji_match.group(1).strip()
            role_input = role_match.group(1).strip()
            
            # Find the role
            role = None
            
            # Try to find by mention
            role_mention_match = re.search(r'<@&(\d+)>', role_input)
            if role_mention_match:
                role_id = int(role_mention_match.group(1))
                role = interaction.guild.get_role(role_id)
            
            # Try to find by name
            if not role:
                role = discord.utils.get(interaction.guild.roles, name=role_input)
            
            # Try to find by ID
            if not role and role_input.isdigit():
                role = interaction.guild.get_role(int(role_input))
            
            if not role:
                await interaction.followup.send(f"❌ Role '{role_input}' not found. Please check the role name or mention.", ephemeral=True)
                await msg.delete()
                return
            
            # Add to database
            await self.bot.db.execute(
                "INSERT INTO role_reactions (guild_id, message_id, emoji, role_id) VALUES (%s, %s, %s, %s)",
                (self.guild_id, self.message_id, emoji, role.id)
            )
            
            # Add reaction to the actual message
            try:
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(self.message_id)
                        await message.add_reaction(emoji)
                        break
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error adding reaction {emoji}: {e}")
            
            await interaction.followup.send(f"✅ Added: {emoji} → {role.mention}", ephemeral=True)
            await msg.delete()
            
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Timed out waiting for response.", ephemeral=True)
    
    @discord.ui.button(label="Remove Reaction", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_reactions_to_remove(interaction)
    
    @discord.ui.button(label="Remove All Reactions", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_all_reactions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.execute("DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s", (self.guild_id, self.message_id))
        
        # Remove all reactions from the actual message
        try:
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(self.message_id)
                    await message.clear_reactions()
                    break
                except:
                    continue
        except Exception as e:
            logger.error(f"Error clearing reactions: {e}")
        
        await interaction.response.send_message(
            _("role_reactions.all_reactions_removed", interaction.user.id, self.guild_id),
            ephemeral=True
        )
    
    async def show_reactions_to_remove(self, interaction: discord.Interaction):
        query = "SELECT emoji, role_id FROM role_reactions WHERE guild_id = %s AND message_id = %s"
        result = await self.bot.db.query(query, (self.guild_id, self.message_id), fetchall=True)
        
        if not result:
            await interaction.response.send_message(
                "❌ No reactions found for this message.",
                ephemeral=True
            )
            return
        
        options = []
        for emoji, role_id in result:
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else f"Role ID: {role_id}"
            options.append(discord.SelectOption(
                label=f"{emoji} → {role_name}",
                value=f"{emoji}|{role_id}",
                emoji=emoji
            ))
        
        view = RemoveReactionView(self.bot, self.guild_id, self.message_id, options)
        await interaction.response.send_message(
            _("role_reactions.select_reaction_to_remove", interaction.user.id, self.guild_id),
            view=view,
            ephemeral=True
        )

class RemoveReactionView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_id: int, options: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id
        self.add_item(RemoveReactionSelect(bot, guild_id, message_id, options))

class RemoveReactionSelect(discord.ui.Select):
    def __init__(self, bot, guild_id: int, message_id: int, options: list):
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id
        super().__init__(placeholder="Select reactions to remove...", options=options, max_values=len(options))
    
    async def callback(self, interaction: discord.Interaction):
        removed_reactions = []
        
        for value in self.values:
            emoji, role_id = value.split("|")
            await self.bot.db.execute(
                "DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s AND emoji = %s",
                (self.guild_id, self.message_id, emoji)
            )
            
            # Remove the reaction from the actual message
            try:
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(self.message_id)
                        await message.remove_reaction(emoji, interaction.client.user)
                        break
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error removing reaction {emoji}: {e}")
            
            role = interaction.guild.get_role(int(role_id))
            role_name = role.name if role else f"Role ID: {role_id}"
            removed_reactions.append(f"{emoji} → {role_name}")
        
        await interaction.response.send_message(
            _("role_reactions.reactions_removed", interaction.user.id, self.guild_id, reactions=", ".join(removed_reactions)),
            ephemeral=True
        )


class RoleReact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Structure en mémoire : {guild_id: {message_id: {emoji: role_id}}}
        self.bot.role_reactions = {}
        logger.info("Initialisation de RoleReact Cog")

    async def load_role_reactions(self):
        logger.info("[DB] Chargement des réactions de rôles depuis la base de données...")
        query = "SELECT guild_id, message_id, emoji, role_id FROM role_reactions"
        rows = await self.bot.db.query(query, fetchall=True)
        self.bot.role_reactions = {}
        if rows:
            for guild_id, message_id, emoji, role_id in rows:
                if guild_id not in self.bot.role_reactions:
                    self.bot.role_reactions[guild_id] = {}
                if message_id not in self.bot.role_reactions[guild_id]:
                    self.bot.role_reactions[guild_id][message_id] = {}
                self.bot.role_reactions[guild_id][message_id][emoji] = role_id
        logger.info(f"[DB] {len(rows) if rows else 0} configurations chargées.")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_role_reactions()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        role_map = self.bot.role_reactions.get(payload.guild_id, {}).get(payload.message_id)
        if role_map and str(payload.emoji) in role_map:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            member = guild.get_member(payload.user_id)
            if not member:
                return

            role_id = role_map[str(payload.emoji)]
            role = guild.get_role(role_id)
            if not role:
                return

            try:
                await member.add_roles(role)
                logger.info(f"Rôle {role.name} ajouté à {member.display_name}")

                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    msg = await channel.send(
                        _("role_reactions.messages.role_added", member.id, guild.id, user=member.mention, role=role.name)
                    )
                    await msg.delete(delay=5)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout du rôle: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        role_map = self.bot.role_reactions.get(payload.guild_id, {}).get(payload.message_id)
        if role_map and str(payload.emoji) in role_map:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            member = guild.get_member(payload.user_id)
            if not member:
                return

            role_id = role_map[str(payload.emoji)]
            role = guild.get_role(role_id)
            if not role:
                return

            try:
                await member.remove_roles(role)
                logger.info(f"Rôle {role.name} retiré de {member.display_name}")

                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    msg = await channel.send(
                        _("role_reactions.messages.role_removed", member.id, guild.id, user=member.mention, role=role.name)
                    )
                    await msg.delete(delay=5)
            except Exception as e:
                logger.error(f"Erreur lors du retrait du rôle: {e}")

    @app_commands.command(name="rolereact", description="role_reactions.command.description")
    @app_commands.checks.has_permissions(administrator=True)
    async def rolereact(self, interaction: discord.Interaction):
        logger.info("Commande rolereact appelée")
        
        embed = discord.Embed(
            title=_("role_reactions.main_menu.title", interaction.user.id, interaction.guild_id),
            description=_("role_reactions.main_menu.description", interaction.user.id, interaction.guild_id),
            color=discord.Color.blue()
        )
        
        # Get current statistics
        query = "SELECT COUNT(*) FROM role_reactions WHERE guild_id = %s"
        result = await self.bot.db.query(query, (interaction.guild_id,), fetchall=True)
        count = result[0][0] if result else 0
        
        embed.add_field(
            name=_("role_reactions.main_menu.current_stats", interaction.user.id, interaction.guild_id),
            value=_("role_reactions.main_menu.stats_value", interaction.user.id, interaction.guild_id, count=count),
            inline=False
        )
        
        view = RoleReactView(self.bot, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleReact(bot))
    logger.info("Cog RoleReact chargé avec succès")
