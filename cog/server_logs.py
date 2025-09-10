import discord
from discord.ext import commands
from datetime import datetime, timezone
import logging
from i18n import _
from .command_logger import log_command_usage

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
                    'log_channel_delete': True,
                    'log_role_create': True,
                    'log_role_delete': True,
                    'log_role_update': True,
                    'log_channel_update': True,
                    'log_voice_state_changes': True
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
            timestamp=datetime.now(timezone.utc)
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
            timestamp=datetime.now(timezone.utc)
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
        """Log voice channel joins, leaves, and voice state changes"""
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
                    timestamp=datetime.now(timezone.utc)
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
                    timestamp=datetime.now(timezone.utc)
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
                    timestamp=datetime.now(timezone.utc)
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
        
        # Voice state changes (mute, deaf, etc.)
        elif before.channel == after.channel and before.channel is not None:
            voice_changes = []
            
            # Check for mute changes
            if before.mute != after.mute:
                if after.mute:
                    voice_changes.append(_('server_logs.voice_changes.muted', 0, member.guild.id))
                else:
                    voice_changes.append(_('server_logs.voice_changes.unmuted', 0, member.guild.id))
            
            # Check for deaf changes
            if before.deaf != after.deaf:
                if after.deaf:
                    voice_changes.append(_('server_logs.voice_changes.deafened', 0, member.guild.id))
                else:
                    voice_changes.append(_('server_logs.voice_changes.undeafened', 0, member.guild.id))
            
            # Check for self mute changes
            if before.self_mute != after.self_mute:
                if after.self_mute:
                    voice_changes.append(_('server_logs.voice_changes.self_muted', 0, member.guild.id))
                else:
                    voice_changes.append(_('server_logs.voice_changes.self_unmuted', 0, member.guild.id))
            
            # Check for self deaf changes
            if before.self_deaf != after.self_deaf:
                if after.self_deaf:
                    voice_changes.append(_('server_logs.voice_changes.self_deafened', 0, member.guild.id))
                else:
                    voice_changes.append(_('server_logs.voice_changes.self_undeafened', 0, member.guild.id))
            
            # Check for stream changes
            if before.self_stream != after.self_stream:
                if after.self_stream:
                    voice_changes.append(_('server_logs.voice_changes.started_streaming', 0, member.guild.id))
                else:
                    voice_changes.append(_('server_logs.voice_changes.stopped_streaming', 0, member.guild.id))
            
            # Check for video changes
            if before.self_video != after.self_video:
                if after.self_video:
                    voice_changes.append(_('server_logs.voice_changes.started_video', 0, member.guild.id))
                else:
                    voice_changes.append(_('server_logs.voice_changes.stopped_video', 0, member.guild.id))
            
            # Log voice state changes if any
            if voice_changes and config.get('log_voice_state_changes', True):
                embed = discord.Embed(
                    title=f"🎤 {_('server_logs.voice_state_changed', 0, member.guild.id)}",
                    description=_('server_logs.voice_state_description', 0, member.guild.id, member=member.mention, channel=after.channel.mention),
                    color=discord.Color.cyan(),
                    timestamp=datetime.now(timezone.utc)
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
                    name=_('server_logs.changes', 0, member.guild.id),
                    value="\n".join(voice_changes),
                    inline=False
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
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name=_('server_logs.author', 0, message.guild.id),
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
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name=_('server_logs.author', 0, before.guild.id),
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
                timestamp=datetime.now(timezone.utc)
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
        if before.roles != after.roles and config.get('log_role_changes', True):
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title=f"🎭 {_('config_system.server_logs.log_events.roles_changed', 0, before.guild.id)}",
                    color=discord.Color.purple(),
                    timestamp=datetime.now(timezone.utc)
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
                
                # Try to find who made the change by checking audit logs
                try:
                    async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                        if entry.target and entry.target.id == after.id:
                            # Check if the change happened recently (within last 10 seconds)
                            if (datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 10:
                                embed.add_field(
                                    name=_('server_logs.modified_by', 0, before.guild.id),
                                    value=f"{entry.user.mention}\n({entry.user.display_name})",
                                    inline=True
                                )
                                break
                except Exception as e:
                    logger.warning(f"Could not fetch audit log for role change: {e}")
                
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
            timestamp=datetime.now(timezone.utc)
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
            timestamp=datetime.now(timezone.utc)
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
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log when a role is created"""
        config = await self.get_log_config(role.guild.id)
        
        if not config or not config.get('log_role_create', True):
            return
        
        embed = discord.Embed(
            title=f"🎭 {_('server_logs.role_created', 0, role.guild.id)}",
            description=_('server_logs.role_created_description', 0, role.guild.id, role_name=role.name),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name=_('server_logs.role', 0, role.guild.id),
            value=f"{role.mention}\n({role.name})",
            inline=True
        )
        
        embed.add_field(
            name=_('server_logs.color', 0, role.guild.id),
            value=f"#{role.color.value:06x}" if role.color.value != 0 else _('server_logs.default', 0, role.guild.id),
            inline=True
        )
        
        embed.add_field(
            name=_('server_logs.position', 0, role.guild.id),
            value=f"{role.position}",
            inline=True
        )
        
        # Try to find who created the role
        try:
            async for entry in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create):
                if entry.target and entry.target.id == role.id:
                    # Check if the change happened recently (within last 10 seconds)
                    if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                        embed.add_field(
                            name=_('server_logs.created_by', 0, role.guild.id),
                            value=f"{entry.user.mention}\n({entry.user.display_name})",
                            inline=True
                        )
                        break
        except Exception as e:
            logger.warning(f"Could not fetch audit log for role creation: {e}")
        
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.send_log(role.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log when a role is deleted"""
        config = await self.get_log_config(role.guild.id)
        
        if not config or not config.get('log_role_delete', True):
            return
        
        embed = discord.Embed(
            title=f"🗑️ {_('server_logs.role_deleted', 0, role.guild.id)}",
            description=_('server_logs.role_deleted_description', 0, role.guild.id, role_name=role.name),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name=_('server_logs.role', 0, role.guild.id),
            value=f"**{role.name}**",
            inline=True
        )
        
        embed.add_field(
            name=_('server_logs.color', 0, role.guild.id),
            value=f"#{role.color.value:06x}" if role.color.value != 0 else _('server_logs.default', 0, role.guild.id),
            inline=True
        )
        
        embed.add_field(
            name=_('server_logs.position', 0, role.guild.id),
            value=f"{role.position}",
            inline=True
        )
        
        # Try to find who deleted the role
        try:
            async for entry in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_delete):
                if entry.target and entry.target.id == role.id:
                    # Check if the change happened recently (within last 10 seconds)
                    if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                        embed.add_field(
                            name=_('server_logs.deleted_by', 0, role.guild.id),
                            value=f"{entry.user.mention}\n({entry.user.display_name})",
                            inline=True
                        )
                        break
        except Exception as e:
            logger.warning(f"Could not fetch audit log for role deletion: {e}")
        
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.send_log(role.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Log when a role is updated"""
        config = await self.get_log_config(after.guild.id)
        
        if not config or not config.get('log_role_update', True):
            return
        
        changes = []
        
        # Check for name changes
        if before.name != after.name:
            changes.append(_('server_logs.role_changes.name', 0, after.guild.id, before=before.name, after=after.name))
        
        # Check for color changes
        if before.color != after.color:
            before_color = f"#{before.color.value:06x}" if before.color.value != 0 else _('server_logs.default', 0, after.guild.id)
            after_color = f"#{after.color.value:06x}" if after.color.value != 0 else _('server_logs.default', 0, after.guild.id)
            changes.append(_('server_logs.role_changes.color', 0, after.guild.id, before=before_color, after=after_color))
        
        # Check for permission changes
        if before.permissions != after.permissions:
            changes.append(_('server_logs.role_changes.permissions', 0, after.guild.id))
        
        # Check for position changes
        if before.position != after.position:
            changes.append(_('server_logs.role_changes.position', 0, after.guild.id, before=before.position, after=after.position))
        
        # Check for mentionable changes
        if before.mentionable != after.mentionable:
            changes.append(_('server_logs.role_changes.mentionable', 0, after.guild.id, before=before.mentionable, after=after.mentionable))
        
        # Check for hoist changes
        if before.hoist != after.hoist:
            changes.append(_('server_logs.role_changes.hoist', 0, after.guild.id, before=before.hoist, after=after.hoist))
        
        # Only log if there are actual changes
        if changes:
            embed = discord.Embed(
                title=f"✏️ {_('server_logs.role_updated', 0, after.guild.id)}",
                description=_('server_logs.role_updated_description', 0, after.guild.id, role=after.mention),
                color=discord.Color.yellow(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name=_('server_logs.role', 0, after.guild.id),
                value=f"{after.mention}\n({after.name})",
                inline=True
            )
            
            embed.add_field(
                name=_('server_logs.changes', 0, after.guild.id),
                value="\n".join(changes),
                inline=False
            )
            
            # Try to find who updated the role
            try:
                async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_update):
                    if entry.target and entry.target.id == after.id:
                        # Check if the change happened recently (within last 10 seconds)
                        if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                            embed.add_field(
                                name=_('server_logs.updated_by', 0, after.guild.id),
                                value=f"{entry.user.mention}\n({entry.user.display_name})",
                                inline=True
                            )
                            break
            except Exception as e:
                logger.warning(f"Could not fetch audit log for role update: {e}")
            
            embed.set_footer(text=f"Role ID: {after.id}")
            
            await self.send_log(after.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """Log when a channel is updated"""
        config = await self.get_log_config(after.guild.id)
        
        if not config or not config.get('log_channel_update', True):
            return
        
        changes = []
        
        # Check for name changes
        if before.name != after.name:
            changes.append(_('server_logs.channel_changes.name', 0, after.guild.id, before=before.name, after=after.name))
        
        # Check for topic changes (text channels)
        if hasattr(before, 'topic') and hasattr(after, 'topic'):
            if before.topic != after.topic:
                before_topic = before.topic[:50] + "..." if before.topic and len(before.topic) > 50 else before.topic or _('server_logs.none', 0, after.guild.id)
                after_topic = after.topic[:50] + "..." if after.topic and len(after.topic) > 50 else after.topic or _('server_logs.none', 0, after.guild.id)
                changes.append(_('server_logs.channel_changes.topic', 0, after.guild.id, before=before_topic, after=after_topic))
        
        # Check for category changes
        if before.category != after.category:
            before_cat = before.category.name if before.category else _('server_logs.none', 0, after.guild.id)
            after_cat = after.category.name if after.category else _('server_logs.none', 0, after.guild.id)
            changes.append(_('server_logs.channel_changes.category', 0, after.guild.id, before=before_cat, after=after_cat))
        
        # Check for permission changes
        if before.overwrites != after.overwrites:
            changes.append(_('server_logs.channel_changes.permissions', 0, after.guild.id))
        
        # Only log if there are actual changes
        if changes:
            embed = discord.Embed(
                title=f"✏️ {_('server_logs.channel_updated', 0, after.guild.id)}",
                description=_('server_logs.channel_updated_description', 0, after.guild.id, channel=after.mention),
                color=discord.Color.yellow(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name=_('server_logs.channel', 0, after.guild.id),
                value=f"{after.mention}\n({after.name})",
                inline=True
            )
            
            embed.add_field(
                name=_('server_logs.type', 0, after.guild.id),
                value=f"{after.type}".replace("_", " ").title(),
                inline=True
            )
            
            embed.add_field(
                name=_('server_logs.changes', 0, after.guild.id),
                value="\n".join(changes),
                inline=False
            )
            
            # Try to find who updated the channel
            try:
                async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_update):
                    if entry.target and entry.target.id == after.id:
                        # Check if the change happened recently (within last 10 seconds)
                        if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                            embed.add_field(
                                name=_('server_logs.updated_by', 0, after.guild.id),
                                value=f"{entry.user.mention}\n({entry.user.display_name})",
                                inline=True
                            )
                            break
            except Exception as e:
                logger.warning(f"Could not fetch audit log for channel update: {e}")
            
            embed.set_footer(text=f"Channel ID: {after.id}")
            
            await self.send_log(after.guild.id, embed)

async def setup(bot):
    await bot.add_cog(ServerLogsCog(bot))
