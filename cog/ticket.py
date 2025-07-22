import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from i18n import _
import json


class Ticket(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions from dashboard-created ticket panels"""
        if interaction.type != discord.InteractionType.component:
            return
            
        if not interaction.data.get('custom_id', '').startswith('ticket_button_'):
            return
            
        # Extract button ID from custom_id
        button_id = interaction.data['custom_id'].replace('ticket_button_', '')
        
        try:
            # Get button configuration from database
            button_data = await self.bot.db.query("""
                SELECT tb.id, tb.panel_id, tb.button_label, tb.button_emoji, tb.button_style, 
                       tb.category_id, tb.ticket_name_format, tb.ping_roles, tb.initial_message, 
                       tb.button_order, tp.panel_name, tp.guild_id 
                FROM ticket_buttons tb 
                JOIN ticket_panels tp ON tb.panel_id = tp.id 
                WHERE tb.id = %s
            """, (button_id,), fetchone=True)
            
            if not button_data:
                await interaction.response.send_message("Button configuration not found.", ephemeral=True)
                return
            
            # Debug logging
            print(f"DEBUG: Retrieved button data: {button_data}")
            
            # Extract values from dictionary result
            btn_id = button_data['id']
            panel_id = button_data['panel_id']
            button_label = button_data['button_label']
            button_emoji = button_data['button_emoji']
            button_style = button_data['button_style']
            category_id = button_data['category_id']
            ticket_name_format = button_data['ticket_name_format']
            ping_roles_json = button_data['ping_roles']
            initial_message = button_data['initial_message']
            button_order = button_data['button_order']
            panel_name = button_data['panel_name']
            guild_id = button_data['guild_id']
            
            # Debug logging
            print(f"DEBUG: Category ID: {category_id} (type: {type(category_id)})")
            
            # Validate category_id - handle both integer and string types
            try:
                category_id = int(category_id) if category_id is not None else None
                if not category_id or category_id <= 0:
                    print(f"DEBUG: Category ID validation failed - value: {category_id}")
                    await interaction.response.send_message("Invalid ticket category configuration. Please recreate your ticket panel in the dashboard.", ephemeral=True)
                    return
            except (ValueError, TypeError):
                print(f"DEBUG: Category ID conversion failed - original value: {category_id}")
                await interaction.response.send_message("Invalid ticket category configuration. Please recreate your ticket panel in the dashboard.", ephemeral=True)
                return
            
            # Parse ping roles - handle empty string, None, and valid JSON
            ping_roles = []
            if ping_roles_json and ping_roles_json.strip():
                try:
                    ping_roles = json.loads(ping_roles_json)
                except json.JSONDecodeError:
                    print(f"Invalid JSON in ping_roles: {ping_roles_json}")
                    ping_roles = []
            
            # Create ticket
            await self.create_dashboard_ticket(
                interaction, category_id, ticket_name_format, 
                initial_message, ping_roles, button_label, btn_id
            )
            
        except Exception as e:
            print(f"Error handling ticket button interaction: {e}")
            await interaction.response.send_message("An error occurred while creating your ticket.", ephemeral=True)

    async def create_dashboard_ticket(self, interaction, category_id, name_format, initial_message, ping_roles, button_label, button_id):
        """Create a ticket from dashboard button click"""
        guild = interaction.guild
        user = interaction.user
        
        # Get category
        category = guild.get_channel(int(category_id)) if category_id else None
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("Invalid ticket category configuration.", ephemeral=True)
            return
        
        # Format ticket name
        ticket_name = name_format.replace("{user}", user.name.lower()).replace("{username}", user.name.lower())
        if not ticket_name:
            ticket_name = f"ticket-{user.name.lower()}"
        
        # Check if user already has a ticket in this category
        existing = discord.utils.get(category.channels, name=ticket_name)
        if existing:
            await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
            return
        
        # Set up permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        }
        
        # Add ping roles to permissions
        for role_id in ping_roles:
            role = guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        # Create ticket channel
        try:
            channel = await guild.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                category=category,
                reason=f"Ticket created by {user} via {button_label} button"
            )
            
            # Create initial message
            embed = discord.Embed(
                title=f"🎫 {button_label}",
                description=initial_message or f"Hello {user.mention}! Please describe your issue and someone will help you soon.",
                color=0x5865F2
            )
            embed.set_footer(text=f"Ticket created by {user}", icon_url=user.display_avatar.url)
            
            # Mention roles if specified
            mentions = []
            for role_id in ping_roles:
                role = guild.get_role(int(role_id))
                if role:
                    mentions.append(role.mention)
            
            mention_content = " ".join(mentions) if mentions else ""
            
            # Add close button
            view = TicketCloseView()
            
            await channel.send(content=f"{user.mention} {mention_content}".strip(), embed=embed, view=view)
            
            # Store ticket in database
            await self.bot.db.execute("""
                INSERT INTO active_tickets (guild_id, channel_id, user_id, button_id, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (str(guild.id), str(channel.id), str(user.id), button_id))
            
            await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to create channels in that category.", ephemeral=True)
        except Exception as e:
            print(f"Error creating ticket: {e}")
            await interaction.response.send_message("An error occurred while creating your ticket.", ephemeral=True)

    @app_commands.command(name="cleanup_ticket_data",
                          description="Clean up invalid ticket data from database (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def cleanup_ticket_data(self, interaction: discord.Interaction):
        """Clean up invalid ticket data from the database"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get all ticket buttons with potential issues
            buttons_data = await self.bot.db.query("""
                SELECT id, category_id, ping_roles, button_label 
                FROM ticket_buttons
            """, fetchall=True)
            
            if not buttons_data:
                await interaction.followup.send("✅ No ticket buttons found in database.", ephemeral=True)
                return
            
            invalid_buttons = []
            issues_found = []
            
            for button_id, category_id, ping_roles, button_label in buttons_data:
                is_invalid = False
                button_issues = []
                
                # Check if category_id is a literal string instead of a number
                if category_id and not str(category_id).isdigit():
                    button_issues.append(f"Invalid category_id: '{category_id}'")
                    is_invalid = True
                
                # Check if ping_roles is a literal string instead of JSON
                if ping_roles and ping_roles in ['ping_roles', '["ping_roles"]']:
                    button_issues.append(f"Invalid ping_roles: '{ping_roles}'")
                    is_invalid = True
                
                if is_invalid:
                    invalid_buttons.append(button_id)
                    issues_found.append(f"Button '{button_label}' (ID: {button_id}): {', '.join(button_issues)}")
            
            if not invalid_buttons:
                await interaction.followup.send(
                    f"✅ Database is clean! Found {len(buttons_data)} valid ticket buttons.",
                    ephemeral=True
                )
                return
            
            # Delete invalid buttons
            for button_id in invalid_buttons:
                await self.bot.db.execute("DELETE FROM ticket_buttons WHERE id = %s", (button_id,))
            
            # Check for orphaned panels
            orphaned_panels = await self.bot.db.query("""
                SELECT tp.id, tp.panel_name 
                FROM ticket_panels tp 
                LEFT JOIN ticket_buttons tb ON tp.id = tb.panel_id 
                WHERE tb.panel_id IS NULL
            """, fetchall=True)
            
            for panel_id, panel_name in orphaned_panels:
                await self.bot.db.execute("DELETE FROM ticket_panels WHERE id = %s", (panel_id,))
            
            # Send cleanup report
            report = f"🗑️ **Ticket Database Cleanup Complete**\n\n"
            report += f"**Removed {len(invalid_buttons)} invalid buttons:**\n"
            for issue in issues_found[:10]:  # Limit to first 10 to avoid message length issues
                report += f"• {issue}\n"
            
            if len(issues_found) > 10:
                report += f"• ... and {len(issues_found) - 10} more\n"
            
            if orphaned_panels:
                report += f"\n**Removed {len(orphaned_panels)} orphaned panels**\n"
            
            report += f"\n✅ **Database is now clean and ready for use!**"
            
            await interaction.followup.send(report, ephemeral=True)
            
        except Exception as e:
            print(f"Error during ticket cleanup: {e}")
            await interaction.followup.send(f"❌ Error during cleanup: {str(e)}", ephemeral=True)


class TicketCreateButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green,
                         label="Create a ticket",
                         custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            await interaction.response.send_message(
                _("ticket_system.create.category_not_found", user_id, guild_id), ephemeral=True)
            return

        existing = discord.utils.get(category.channels,
                                     name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(
                _("ticket_system.create.already_exists", user_id, guild_id), ephemeral=True)
            return

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(view_channel=False),
            user:
            discord.PermissionOverwrite(view_channel=True,
                                        send_messages=True,
                                        read_message_history=True),
            guild.me:
            discord.PermissionOverwrite(view_channel=True)
        }
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            overwrites=overwrites,
            category=category,
            reason=f"Ticket created by {user}")
        embed = discord.Embed(
            title=_("ticket_system.create.embed_title", user_id, guild_id),
            description=_("ticket_system.create.embed_description", user_id, guild_id, user=user.mention),
            color=discord.Color.blue())
        view = TicketCloseView()
        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            _("ticket_system.create.success", user_id, guild_id, channel=channel.mention), ephemeral=True)


class TicketCloseButton(discord.ui.Button):

    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red,
                         label="Close ticket",
                         custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        
        channel = interaction.channel
        await interaction.response.send_message(
            _("ticket_system.close.closing", user_id, guild_id), ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket closed by {interaction.user}")


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())


class TicketCloseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())


async def setup(bot):
    await bot.add_cog(Ticket(bot))
