import discord
from discord.ext import commands
from datetime import datetime
import logging
from i18n import _

logger = logging.getLogger(__name__)

class ServerLogsCog(commands.Cog):
    """Server logging functionality for monitoring server events"""
    
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = {}  # Cache for message content before deletion
        
    async def get_log_config(self, guild_id: int):
        """Get server logging configuration for a guild"""
        result = await self.bot.db.query(
            "SELECT * FROM server_logs_config WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        # If no server_logs_config, check guild_config table for dashboard consistency
        if not result:
            guild_config = await self.bot.db.query(
                "SELECT * FROM guild_config WHERE guild_id = %s",
                (guild_id,),
                fetchone=True
            )
            if guild_config and guild_config.get('logs_enabled') and guild_config.get('logs_channel'):
                # Convert guild_config to server_logs_config format
                return {
                    'guild_id': guild_id,
                    'log_channel_id': guild_config['logs_channel'],
                    'log_member_join': True,
                    'log_member_leave': True,
                    'log_voice_join': True,
                    'log_voice_leave': True,
                    'log_message_delete': True,
                    'log_message_edit': True,
                    'log_role_changes': True,
                    'log_nickname_changes': True,
                    'log_channel_create': True,
                    'log_channel_delete': True
                }
        
        return result
    
    async def get_guild_language(self, guild_id: int):
        """Get guild language preference"""
        if hasattr(self.bot, 'i18n') and self.bot.i18n:
            return self.bot.i18n.get_guild_language(guild_id)
        return 'en'
    
    async def send_log(self, guild_id: int, embed: discord.Embed):
        """Send a log message to the configured log channel"""
        config = await self.get_log_config(guild_id)
        
        if not config or not config['log_channel_id']:
            return
        
        channel = self.bot.get_channel(config['log_channel_id'])
        if not channel:
            return
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"No permission to send logs to channel {channel.id} in guild {guild_id}")
        except Exception as e:
            logger.error(f"Error sending log message: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when a member joins the server"""
        config = await self.get_log_config(member.guild.id)
        
        if not config or not config['log_member_join']:
            return
        
        # Get guild language for translations
        lang = await self.get_guild_language(member.guild.id)
        
        embed = discord.Embed(
            title=f"👋 {_('config_system.server_logs.log_events.member_joined', 0, member.guild.id)}",
            description=f"{member.mention} has joined the server",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.member", 0, member.guild.id),
            value=f"**{member.display_name}** ({member.name})\nID: {member.id}",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.account_created", 0, member.guild.id),
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.total_members", 0, member.guild.id),
            value=f"{member.guild.member_count}",
            inline=True
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(member.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when a member leaves the server"""
        config = await self.get_log_config(member.guild.id)
        
        if not config or not config['log_member_leave']:
            return
        
        embed = discord.Embed(
            title=f"👋 {_('config_system.server_logs.log_events.member_left', 0, member.guild.id)}",
            description=f"**{member.display_name}** has left the server",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.member", 0, member.guild.id),
            value=f"**{member.display_name}** ({member.name})\nID: {member.id}",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.joined", 0, member.guild.id),
            value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else _("config_system.server_logs.embed_fields.unknown", 0, member.guild.id),
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.total_members", 0, member.guild.id),
            value=f"{member.guild.member_count}",
            inline=True
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(member.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log voice channel joins and leaves"""
        config = await self.get_log_config(member.guild.id)
        
        if not config:
            return
        
        # Member joined a voice channel
        if before.channel is None and after.channel is not None:
            if config['log_voice_join']:
                embed = discord.Embed(
                    title=f"🔊 {_('config_system.server_logs.log_events.voice_joined', 0, member.guild.id)}",
                    description=f"{member.mention} joined {after.channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.member", 0, member.guild.id),
                    value=f"**{member.display_name}** ({member.name})",
                    inline=True
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.channel", 0, member.guild.id),
                    value=f"{after.channel.mention}\n({after.channel.name})",
                    inline=True
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.members_in_channel", 0, member.guild.id),
                    value=f"{len(after.channel.members)}",
                    inline=True
                )
                
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"User ID: {member.id}")
                
                await self.send_log(member.guild.id, embed)
        
        # Member left a voice channel
        elif before.channel is not None and after.channel is None:
            if config['log_voice_leave']:
                embed = discord.Embed(
                    title=f"🔇 {_('config_system.server_logs.log_events.voice_left', 0, member.guild.id)}",
                    description=f"{member.mention} left {before.channel.mention}",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.member", 0, member.guild.id),
                    value=f"**{member.display_name}** ({member.name})",
                    inline=True
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.channel", 0, member.guild.id),
                    value=f"{before.channel.mention}\n({before.channel.name})",
                    inline=True
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.members_in_channel", 0, member.guild.id),
                    value=f"{len(before.channel.members)}",
                    inline=True
                )
                
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"User ID: {member.id}")
                
                await self.send_log(member.guild.id, embed)
        
        # Member switched voice channels
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            if config['log_voice_join']:  # Use join log setting for switching
                embed = discord.Embed(
                    title=f"🔄 {_('config_system.server_logs.log_events.voice_switched', 0, member.guild.id)}",
                    description=f"{member.mention} switched from {before.channel.mention} to {after.channel.mention}",
                    color=discord.Color.purple(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.member", 0, member.guild.id),
                    value=f"**{member.display_name}** ({member.name})",
                    inline=True
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.from_to", 0, member.guild.id),
                    value=f"{before.channel.mention}\n↓\n{after.channel.mention}",
                    inline=True
                )
                
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"User ID: {member.id}")
                
                await self.send_log(member.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Cache messages for deletion logging"""
        if message.author.bot or not message.guild:
            return
            
        # Store message content for potential deletion logging
        self.message_cache[message.id] = {
            'content': message.content,
            'author': message.author,
            'channel': message.channel,
            'created_at': message.created_at,
            'attachments': [att.url for att in message.attachments],
            'embeds': len(message.embeds)
        }
        
        # Keep cache size manageable (store last 1000 messages)
        if len(self.message_cache) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.message_cache.keys())[:100]
            for key in oldest_keys:
                del self.message_cache[key]
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when a message is deleted"""
        if message.author.bot or not message.guild:
            return
            
        config = await self.get_log_config(message.guild.id)
        
        if not config or not config['log_message_delete']:
            return
        
        # Get cached message content
        cached_msg = self.message_cache.get(message.id)
        
        embed = discord.Embed(
            title=f"🗑️ {_('config_system.server_logs.log_events.message_deleted', 0, message.guild.id)}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Author",
            value=f"{message.author.mention}\n({message.author.name})",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.channel", 0, message.guild.id),
            value=f"{message.channel.mention}\n({message.channel.name})",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.message_id", 0, message.guild.id),
            value=f"{message.id}",
            inline=True
        )
        
        # Show message content if available
        if cached_msg and cached_msg['content']:
            content = cached_msg['content']
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.content", 0, message.guild.id),
                value=f"```{content}```",
                inline=False
            )
        elif message.content:
            content = message.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.content", 0, message.guild.id),
                value=f"```{content}```",
                inline=False
            )
        else:
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.content", 0, message.guild.id),
                value=_("config_system.server_logs.embed_fields.no_content", 0, message.guild.id),
                inline=False
            )
        
        # Show attachments if any
        if cached_msg and cached_msg['attachments']:
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.attachments", 0, message.guild.id),
                value=_("config_system.server_logs.embed_fields.attachment_count", 0, message.guild.id).format(count=len(cached_msg['attachments'])),
                inline=True
            )
        elif message.attachments:
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.attachments", 0, message.guild.id),
                value=_("config_system.server_logs.embed_fields.attachment_count", 0, message.guild.id).format(count=len(message.attachments)),
                inline=True
            )
        
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"Author ID: {message.author.id}")
        
        await self.send_log(message.guild.id, embed)
        
        # Clean up cache
        if message.id in self.message_cache:
            del self.message_cache[message.id]
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log when a message is edited"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
            
        config = await self.get_log_config(before.guild.id)
        
        if not config or not config['log_message_edit']:
            return
        
        embed = discord.Embed(
            title=f"✏️ {_('config_system.server_logs.log_events.message_edited', 0, before.guild.id)}",
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Author",
            value=f"{before.author.mention}\n({before.author.name})",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.channel", 0, before.guild.id),
            value=f"{before.channel.mention}\n({before.channel.name})",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.message_id", 0, before.guild.id),
            value=f"{before.id}",
            inline=True
        )
        
        # Show before content
        if before.content:
            content = before.content
            if len(content) > 512:
                content = content[:509] + "..."
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.before", 0, before.guild.id),
                value=f"```{content}```",
                inline=False
            )
        
        # Show after content
        if after.content:
            content = after.content
            if len(content) > 512:
                content = content[:509] + "..."
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.after", 0, before.guild.id),
                value=f"```{content}```",
                inline=False
            )
        
        # Add jump link
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.jump_to_message", 0, before.guild.id),
            value=f"[{_('config_system.server_logs.embed_fields.click_here', 0, before.guild.id)}]({after.jump_url})",
            inline=True
        )
        
        embed.set_thumbnail(url=before.author.display_avatar.url)
        embed.set_footer(text=f"Author ID: {before.author.id}")
        
        await self.send_log(before.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log nickname and role changes"""
        config = await self.get_log_config(before.guild.id)
        
        if not config:
            return
        
        # Nickname change
        if before.nick != after.nick and config['log_nickname_changes']:
            embed = discord.Embed(
                title=f"📝 {_('config_system.server_logs.log_events.nickname_changed', 0, before.guild.id)}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.member", 0, before.guild.id),
                value=f"{after.mention}\n({after.name})",
                inline=True
            )
            
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.before", 0, before.guild.id),
                value=f"{before.nick if before.nick else before.name}",
                inline=True
            )
            
            embed.add_field(
                name=_("config_system.server_logs.embed_fields.after", 0, before.guild.id),
                value=f"{after.nick if after.nick else after.name}",
                inline=True
            )
            
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.send_log(before.guild.id, embed)
        
        # Role changes
        if before.roles != after.roles and config['log_role_changes']:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title=f"🎭 {_('config_system.server_logs.log_events.roles_changed', 0, before.guild.id)}",
                    color=discord.Color.purple(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name=_("config_system.server_logs.embed_fields.member", 0, before.guild.id),
                    value=f"{after.mention}\n({after.display_name})",
                    inline=True
                )
                
                if added_roles:
                    roles_text = ", ".join([role.mention for role in added_roles])
                    embed.add_field(
                        name=_("config_system.server_logs.embed_fields.added_roles", 0, before.guild.id),
                        value=roles_text,
                        inline=False
                    )
                
                if removed_roles:
                    roles_text = ", ".join([role.mention for role in removed_roles])
                    embed.add_field(
                        name=_("config_system.server_logs.embed_fields.removed_roles", 0, before.guild.id),
                        value=roles_text,
                        inline=False
                    )
                
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.send_log(before.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log when a channel is created"""
        config = await self.get_log_config(channel.guild.id)
        
        if not config or not config['log_channel_create']:
            return
        
        embed = discord.Embed(
            title=f"📢 {_('config_system.server_logs.log_events.channel_created', 0, channel.guild.id)}",
            description=f"Channel {channel.mention} was created",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.channel", 0, channel.guild.id),
            value=f"{channel.mention}\n({channel.name})",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.type", 0, channel.guild.id),
            value=f"{channel.type}".replace("_", " ").title(),
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.category", 0, channel.guild.id),
            value=f"{channel.category.name}" if channel.category else _("config_system.server_logs.embed_fields.unknown", 0, channel.guild.id),
            inline=True
        )
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.send_log(channel.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log when a channel is deleted"""
        config = await self.get_log_config(channel.guild.id)
        
        if not config or not config['log_channel_delete']:
            return
        
        embed = discord.Embed(
            title=f"🗑️ {_('config_system.server_logs.log_events.channel_deleted', 0, channel.guild.id)}",
            description=f"Channel **{channel.name}** was deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.channel", 0, channel.guild.id),
            value=f"#{channel.name}",
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.type", 0, channel.guild.id),
            value=f"{channel.type}".replace("_", " ").title(),
            inline=True
        )
        
        embed.add_field(
            name=_("config_system.server_logs.embed_fields.category", 0, channel.guild.id),
            value=f"{channel.category.name}" if channel.category else _("config_system.server_logs.embed_fields.unknown", 0, channel.guild.id),
            inline=True
        )
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.send_log(channel.guild.id, embed)

async def setup(bot):
    await bot.add_cog(ServerLogsCog(bot))
