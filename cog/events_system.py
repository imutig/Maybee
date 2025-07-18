"""
Advanced Dynamic Events System for MaybeBot
Automatically creates engaging events and challenges for server members
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum
import random

from services import handle_errors, rate_limit
from monitoring import logger

class EventType(Enum):
    XP_BOOST = "xp_boost"
    CHALLENGE = "challenge"
    MILESTONE = "milestone"
    SEASONAL = "seasonal"
    COMMUNITY = "community"

class EventStatus(Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class Event:
    id: str
    name: str
    description: str
    event_type: EventType
    status: EventStatus
    start_time: datetime
    end_time: datetime
    guild_id: int
    creator_id: Optional[int]
    conditions: Dict[str, Any]
    rewards: Dict[str, Any]
    participants: List[int]
    progress: Dict[int, Dict[str, Any]]  # user_id -> progress data
    metadata: Dict[str, Any]

class EventsSystem(commands.Cog):
    """Advanced events system with automatic event generation and management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_events: Dict[str, Event] = {}
        self.event_templates = self._load_event_templates()
        self.check_events.start()
        self.auto_generate_events.start()
        
    def cog_unload(self):
        self.check_events.cancel()
        self.auto_generate_events.cancel()

    def _load_event_templates(self) -> Dict[str, Dict]:
        """Load event templates for automatic generation"""
        return {
            "weekend_boost": {
                "name": "Weekend XP Boost",
                "description": "Double XP for all activities this weekend!",
                "type": EventType.XP_BOOST,
                "duration_hours": 48,
                "conditions": {"multiplier": 2.0, "activities": ["text", "voice"]},
                "auto_trigger": {"day_of_week": [5, 6], "probability": 0.7}
            },
            "message_marathon": {
                "name": "Message Marathon",
                "description": "Send {target} messages in {duration} hours to earn rewards!",
                "type": EventType.CHALLENGE,
                "duration_hours": 24,
                "conditions": {"target_messages": 50, "min_participants": 5},
                "rewards": {"xp_bonus": 500, "special_role": "Marathon Champion"},
                "auto_trigger": {"activity_threshold": 0.6, "probability": 0.3}
            },
            "voice_party": {
                "name": "Voice Chat Party",
                "description": "Spend {target} minutes in voice chat to unlock group rewards!",
                "type": EventType.COMMUNITY,
                "duration_hours": 6,
                "conditions": {"target_minutes": 120, "min_participants": 3},
                "rewards": {"group_xp_bonus": 1000, "unlock_channel": True}
            },
            "milestone_celebration": {
                "name": "Server Milestone Celebration",
                "description": "Celebrating {milestone} members! Special rewards for everyone!",
                "type": EventType.MILESTONE,
                "duration_hours": 72,
                "conditions": {"member_milestones": [100, 250, 500, 1000, 2500]},
                "rewards": {"server_wide_xp": 200, "special_announcement": True}
            }
        }

    @tasks.loop(minutes=5)
    async def check_events(self):
        """Check and update active events"""
        try:
            current_time = datetime.utcnow()
            
            for event_id, event in list(self.active_events.items()):
                if event.status == EventStatus.SCHEDULED and current_time >= event.start_time:
                    await self._start_event(event)
                elif event.status == EventStatus.ACTIVE and current_time >= event.end_time:
                    await self._end_event(event)
                elif event.status == EventStatus.ACTIVE:
                    await self._update_event_progress(event)
                    
        except Exception as e:
            logger.error(f"Error checking events: {e}")

    @tasks.loop(hours=1)
    async def auto_generate_events(self):
        """Automatically generate events based on server activity and conditions"""
        try:
            for guild in self.bot.guilds:
                await self._check_auto_event_triggers(guild)
        except Exception as e:
            logger.error(f"Error in auto event generation: {e}")

    async def _check_auto_event_triggers(self, guild: discord.Guild):
        """Check if conditions are met for auto-generating events"""
        try:
            # Get server activity metrics
            activity_level = await self._calculate_activity_level(guild)
            current_time = datetime.utcnow()
            
            for template_id, template in self.event_templates.items():
                if "auto_trigger" not in template:
                    continue
                    
                trigger = template["auto_trigger"]
                should_trigger = False
                
                # Check day-based triggers
                if "day_of_week" in trigger:
                    if current_time.weekday() in trigger["day_of_week"]:
                        should_trigger = random.random() < trigger.get("probability", 0.5)
                
                # Check activity-based triggers
                if "activity_threshold" in trigger:
                    if activity_level >= trigger["activity_threshold"]:
                        should_trigger = random.random() < trigger.get("probability", 0.3)
                
                # Check milestone triggers
                if "member_milestones" in template["conditions"]:
                    member_count = guild.member_count
                    milestones = template["conditions"]["member_milestones"]
                    for milestone in milestones:
                        if abs(member_count - milestone) <= 5:  # Within 5 members of milestone
                            should_trigger = True
                            break
                
                if should_trigger and not self._has_active_event_type(guild.id, template["type"]):
                    await self._create_auto_event(guild, template_id, template)
                    
        except Exception as e:
            logger.error(f"Error checking auto triggers for guild {guild.id}: {e}")

    async def _calculate_activity_level(self, guild: discord.Guild) -> float:
        """Calculate server activity level (0.0 to 1.0)"""
        try:
            # Get recent message activity
            day_ago = datetime.utcnow() - timedelta(days=1)
            
            message_count = await self.bot.db.fetch_one(
                """SELECT COUNT(*) as count FROM xp_history 
                   WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'text'""",
                guild.id, day_ago
            )
            
            voice_activity = await self.bot.db.fetch_one(
                """SELECT COUNT(*) as count FROM xp_history 
                   WHERE guild_id = %s AND timestamp >= %s AND xp_type = 'voice'""",
                guild.id, day_ago
            )
            
            # Normalize based on member count
            messages = message_count[0] if message_count else 0
            voice_mins = voice_activity[0] if voice_activity else 0
            
            # Calculate activity score (messages per member + voice activity)
            member_count = max(guild.member_count, 1)
            activity_score = (messages / member_count) + (voice_mins / member_count * 0.1)
            
            # Normalize to 0-1 scale
            return min(activity_score / 10.0, 1.0)
            
        except Exception:
            return 0.0

    def _has_active_event_type(self, guild_id: int, event_type: EventType) -> bool:
        """Check if guild has an active event of the specified type"""
        for event in self.active_events.values():
            if (event.guild_id == guild_id and 
                event.event_type == event_type and 
                event.status in [EventStatus.SCHEDULED, EventStatus.ACTIVE]):
                return True
        return False

    async def _create_auto_event(self, guild: discord.Guild, template_id: str, template: Dict):
        """Create an automatic event from template"""
        try:
            event_id = f"auto_{template_id}_{guild.id}_{int(datetime.utcnow().timestamp())}"
            
            # Calculate start and end times
            start_time = datetime.utcnow() + timedelta(minutes=random.randint(10, 60))
            end_time = start_time + timedelta(hours=template["duration_hours"])
            
            # Customize description based on conditions
            description = template["description"]
            if "{target}" in description and "target_messages" in template["conditions"]:
                description = description.replace("{target}", str(template["conditions"]["target_messages"]))
            if "{duration}" in description:
                description = description.replace("{duration}", str(template["duration_hours"]))
            if "{milestone}" in description and guild.member_count:
                # Find closest milestone
                milestones = template["conditions"].get("member_milestones", [])
                closest_milestone = min(milestones, key=lambda x: abs(x - guild.member_count))
                description = description.replace("{milestone}", str(closest_milestone))
            
            event = Event(
                id=event_id,
                name=template["name"],
                description=description,
                event_type=template["type"],
                status=EventStatus.SCHEDULED,
                start_time=start_time,
                end_time=end_time,
                guild_id=guild.id,
                creator_id=None,  # Auto-generated
                conditions=template["conditions"],
                rewards=template.get("rewards", {}),
                participants=[],
                progress={},
                metadata={"template": template_id, "auto_generated": True}
            )
            
            self.active_events[event_id] = event
            await self._save_event_to_db(event)
            
            logger.info(f"Auto-generated event '{template['name']}' for guild {guild.id}")
            
        except Exception as e:
            logger.error(f"Error creating auto event: {e}")

    async def _start_event(self, event: Event):
        """Start an event"""
        try:
            event.status = EventStatus.ACTIVE
            await self._save_event_to_db(event)
            
            # Announce event start
            guild = self.bot.get_guild(event.guild_id)
            if guild:
                await self._announce_event(guild, event, "started")
                
            logger.info(f"Started event '{event.name}' in guild {event.guild_id}")
            
        except Exception as e:
            logger.error(f"Error starting event {event.id}: {e}")

    async def _end_event(self, event: Event):
        """End an event and distribute rewards"""
        try:
            event.status = EventStatus.COMPLETED
            await self._save_event_to_db(event)
            
            # Calculate and distribute rewards
            await self._distribute_rewards(event)
            
            # Announce event completion
            guild = self.bot.get_guild(event.guild_id)
            if guild:
                await self._announce_event(guild, event, "completed")
            
            # Clean up from active events
            if event.id in self.active_events:
                del self.active_events[event.id]
                
            logger.info(f"Completed event '{event.name}' in guild {event.guild_id}")
            
        except Exception as e:
            logger.error(f"Error ending event {event.id}: {e}")

    async def _announce_event(self, guild: discord.Guild, event: Event, action: str):
        """Announce event status to the server"""
        try:
            # Find announcement channel (general, announcements, etc.)
            announcement_channel = None
            for channel in guild.text_channels:
                if channel.name.lower() in ['general', 'announcements', 'events']:
                    announcement_channel = channel
                    break
            
            if not announcement_channel:
                announcement_channel = guild.system_channel or guild.text_channels[0]
            
            if not announcement_channel:
                return
            
            embed = discord.Embed(
                title=f"🎉 Event {action.title()}!",
                description=event.description,
                color=discord.Color.gold() if action == "started" else discord.Color.green()
            )
            
            embed.add_field(
                name="Event Name",
                value=event.name,
                inline=True
            )
            
            if action == "started":
                embed.add_field(
                    name="Duration",
                    value=f"Until <t:{int(event.end_time.timestamp())}:R>",
                    inline=True
                )
                embed.add_field(
                    name="How to Participate",
                    value="Just be active in the server!",
                    inline=False
                )
            else:  # completed
                embed.add_field(
                    name="Participants",
                    value=str(len(event.participants)),
                    inline=True
                )
                
                if event.rewards:
                    rewards_text = "\n".join([f"• {k}: {v}" for k, v in event.rewards.items()])
                    embed.add_field(
                        name="Rewards Distributed",
                        value=rewards_text,
                        inline=False
                    )
            
            embed.set_footer(text="Use /events to see all active events")
            
            await announcement_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error announcing event: {e}")

    # Slash Commands for Events Management

    @app_commands.command(name="events", description="View active and upcoming events")
    @handle_errors
    @rate_limit(cooldown=30)
    async def list_events(self, interaction: discord.Interaction):
        """List all events for this server"""
        try:
            guild_events = [e for e in self.active_events.values() if e.guild_id == interaction.guild.id]
            
            if not guild_events:
                embed = discord.Embed(
                    title="🎪 Server Events",
                    description="No active events right now. Check back later!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="🎪 Server Events",
                color=discord.Color.gold()
            )
            
            for event in guild_events:
                status_emoji = "🟢" if event.status == EventStatus.ACTIVE else "🟡"
                time_info = f"<t:{int(event.start_time.timestamp())}:R>" if event.status == EventStatus.SCHEDULED else f"Ends <t:{int(event.end_time.timestamp())}:R>"
                
                embed.add_field(
                    name=f"{status_emoji} {event.name}",
                    value=f"{event.description}\n{time_info}\n**Participants:** {len(event.participants)}",
                    inline=False
                )
            
            embed.set_footer(text="Events are automatically generated based on server activity!")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            raise

    @app_commands.command(name="create_event", description="Create a custom server event")
    @app_commands.describe(
        name="Event name",
        description="Event description", 
        duration="Duration in hours",
        event_type="Type of event"
    )
    @app_commands.choices(event_type=[
        app_commands.Choice(name="XP Boost", value="xp_boost"),
        app_commands.Choice(name="Challenge", value="challenge"),
        app_commands.Choice(name="Community Event", value="community")
    ])
    @handle_errors
    @rate_limit(cooldown=300)  # 5 minute cooldown for creating events
    async def create_event(self, interaction: discord.Interaction, 
                          name: str, description: str, duration: int, event_type: str):
        """Create a custom event (admin only)"""
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Only administrators can create custom events!",
                    ephemeral=True
                )
                return
            
            if duration < 1 or duration > 168:  # Max 1 week
                await interaction.response.send_message(
                    "❌ Duration must be between 1 and 168 hours!",
                    ephemeral=True
                )
                return
            
            # Create custom event
            event_id = f"custom_{interaction.guild.id}_{int(datetime.utcnow().timestamp())}"
            start_time = datetime.utcnow() + timedelta(minutes=5)  # Start in 5 minutes
            end_time = start_time + timedelta(hours=duration)
            
            event = Event(
                id=event_id,
                name=name,
                description=description,
                event_type=EventType(event_type),
                status=EventStatus.SCHEDULED,
                start_time=start_time,
                end_time=end_time,
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
                conditions={},
                rewards={},
                participants=[],
                progress={},
                metadata={"custom": True, "creator": interaction.user.id}
            )
            
            self.active_events[event_id] = event
            await self._save_event_to_db(event)
            
            embed = discord.Embed(
                title="✅ Event Created!",
                description=f"**{name}** will start in 5 minutes and run for {duration} hours.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Custom event '{name}' created by {interaction.user.id} in guild {interaction.guild.id}")
            
        except Exception as e:
            logger.error(f"Error creating custom event: {e}")
            raise

    async def _save_event_to_db(self, event: Event):
        """Save event to database"""
        try:
            await self.bot.db.execute(
                """INSERT INTO events (id, name, description, event_type, status, start_time, end_time, 
                   guild_id, creator_id, conditions, rewards, participants, progress, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   status = VALUES(status), participants = VALUES(participants), 
                   progress = VALUES(progress), metadata = VALUES(metadata)""",
                event.id, event.name, event.description, event.event_type.value, 
                event.status.value, event.start_time, event.end_time, event.guild_id,
                event.creator_id, json.dumps(event.conditions), json.dumps(event.rewards),
                json.dumps(event.participants), json.dumps(event.progress), 
                json.dumps(event.metadata)
            )
        except Exception as e:
            logger.error(f"Error saving event to database: {e}")

    async def _distribute_rewards(self, event: Event):
        """Distribute rewards to event participants"""
        try:
            if not event.rewards or not event.participants:
                return
            
            for user_id in event.participants:
                # Distribute XP rewards
                if "xp_bonus" in event.rewards:
                    await self._give_xp_reward(event.guild_id, user_id, event.rewards["xp_bonus"])
                
                # Server-wide rewards
                if "server_wide_xp" in event.rewards:
                    await self._give_xp_reward(event.guild_id, user_id, event.rewards["server_wide_xp"])
                
                # Group rewards (distributed if enough participants)
                if "group_xp_bonus" in event.rewards and len(event.participants) >= event.conditions.get("min_participants", 1):
                    group_bonus = event.rewards["group_xp_bonus"] // len(event.participants)
                    await self._give_xp_reward(event.guild_id, user_id, group_bonus)
            
            logger.info(f"Distributed rewards for event {event.id} to {len(event.participants)} participants")
            
        except Exception as e:
            logger.error(f"Error distributing rewards for event {event.id}: {e}")

    async def _give_xp_reward(self, guild_id: int, user_id: int, xp_amount: int):
        """Give XP reward to a user"""
        try:
            # Add to existing XP
            await self.bot.db.execute(
                """INSERT INTO xp_data (user_id, guild_id, xp, level, text_xp, voice_xp)
                   VALUES (%s, %s, %s, 1, %s, 0)
                   ON DUPLICATE KEY UPDATE xp = xp + %s, text_xp = text_xp + %s""",
                user_id, guild_id, xp_amount, xp_amount, xp_amount, xp_amount
            )
            
            # Log the reward
            await self.bot.db.execute(
                """INSERT INTO xp_history (user_id, guild_id, xp_gained, xp_type, timestamp)
                   VALUES (%s, %s, %s, 'event_reward', %s)""",
                user_id, guild_id, xp_amount, datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error giving XP reward: {e}")

    async def _update_event_progress(self, event: Event):
        """Update event progress based on user activity"""
        # This would integrate with the XP system to track progress
        # Implementation depends on specific event conditions
        pass

async def setup(bot):
    # Create events table
    await bot.db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            event_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            guild_id BIGINT NOT NULL,
            creator_id BIGINT,
            conditions JSON,
            rewards JSON,
            participants JSON,
            progress JSON,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_guild_status (guild_id, status),
            INDEX idx_times (start_time, end_time)
        )
    """)
    
    await bot.add_cog(EventsSystem(bot))
