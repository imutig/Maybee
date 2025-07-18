import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from i18n import _
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class RoleReactionCreateModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int):
        super().__init__(title=_("role_reactions.create_modal_title", None, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        
        self.title_input = discord.ui.TextInput(
            label=_("role_reactions.modal_title_label", None, guild_id),
            placeholder=_("role_reactions.modal_title_placeholder", None, guild_id),
            required=True,
            max_length=256
        )
        self.add_item(self.title_input)
        
        self.description_input = discord.ui.TextInput(
            label=_("role_reactions.modal_description_label", None, guild_id),
            placeholder=_("role_reactions.modal_description_placeholder", None, guild_id),
            style=discord.TextStyle.long,
            required=False,
            max_length=2000
        )
        self.add_item(self.description_input)
        
        self.color_input = discord.ui.TextInput(
            label=_("role_reactions.modal_color_label", None, guild_id),
            placeholder=_("role_reactions.modal_color_placeholder", None, guild_id),
            required=False,
            max_length=7
        )
        self.add_item(self.color_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse color
        color = discord.Color.blue()  # Default
        if self.color_input.value:
            try:
                color_value = self.color_input.value.strip()
                if color_value.startswith('#'):
                    color_value = color_value[1:]
                color = discord.Color(int(color_value, 16))
            except ValueError:
                pass  # Keep default color
        
        # Create embed
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value or _("role_reactions.default_description", interaction.user.id, self.guild_id),
            color=color
        )
        embed.set_footer(text=_("role_reactions.embed_footer", interaction.user.id, self.guild_id))
        
        # Send the embed message
        message = await interaction.channel.send(embed=embed)
        
        # Create configuration view for this message
        config_view = RoleReactionConfigView(self.bot, self.guild_id, message.id, embed)
        
        await interaction.response.send_message(
            _("role_reactions.message_created", interaction.user.id, self.guild_id),
            view=config_view,
            ephemeral=True
        )

class RoleReactionConfigView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_id: int, embed: discord.Embed):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id
        self.embed = embed
        self.reactions: List[Dict] = []
        
    @discord.ui.button(label="Add Reaction", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.add_reaction_button", interaction.user.id, self.guild_id)
        modal = AddReactionModal(self.bot, self.guild_id, self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove Reaction", style=discord.ButtonStyle.secondary, emoji="➖")
    async def remove_reaction(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.remove_reaction_button", interaction.user.id, self.guild_id)
        if not self.reactions:
            await interaction.response.send_message(
                _("role_reactions.no_reactions_to_remove", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Create select menu with current reactions
        select_view = RemoveReactionSelectView(self.bot, self.guild_id, self)
        await interaction.response.send_message(
            _("role_reactions.select_reaction_to_remove", interaction.user.id, self.guild_id),
            view=select_view,
            ephemeral=True
        )
    
    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.edit_message_button", interaction.user.id, self.guild_id)
        modal = EditMessageModal(self.bot, self.guild_id, self, self.embed)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Finish & Save", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.finish_button", interaction.user.id, self.guild_id)
        if not self.reactions:
            await interaction.response.send_message(
                _("role_reactions.no_reactions_added", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Save to database
        await self.save_to_database()
        
        # Update the original message
        await self.update_message_embed()
        
        await interaction.response.send_message(
            _("role_reactions.config_complete", interaction.user.id, self.guild_id),
            ephemeral=True
        )
        
        # Stop the view
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.cancel_button", interaction.user.id, self.guild_id)
        # Delete the message if no reactions were added
        if not self.reactions:
            try:
                message = await interaction.channel.fetch_message(self.message_id)
                await message.delete()
            except:
                pass
        
        await interaction.response.send_message(
            _("role_reactions.config_cancelled", interaction.user.id, self.guild_id),
            ephemeral=True
        )
        self.stop()
    
    async def save_to_database(self):
        # Clear existing reactions for this message
        await self.bot.db.query(
            "DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s",
            (self.guild_id, self.message_id)
        )
        
        # Save new reactions
        for reaction in self.reactions:
            await self.bot.db.query(
                "INSERT INTO role_reactions (guild_id, message_id, emoji, role_id) VALUES (%s, %s, %s, %s)",
                (self.guild_id, self.message_id, reaction['emoji'], reaction['role'].id)
            )
        
        # Update bot's memory
        if self.guild_id not in self.bot.role_reactions:
            self.bot.role_reactions[self.guild_id] = {}
        
        self.bot.role_reactions[self.guild_id][self.message_id] = {}
        for reaction in self.reactions:
            self.bot.role_reactions[self.guild_id][self.message_id][reaction['emoji']] = reaction['role'].id
    
    async def update_message_embed(self):
        try:
            # Try to find the message in all channels
            message = None
            for channel in self.bot.get_all_channels():
                if isinstance(channel, discord.TextChannel):
                    try:
                        message = await channel.fetch_message(self.message_id)
                        break
                    except:
                        continue
            
            if not message:
                logger.error(f"Could not find message {self.message_id}")
                return
            
            # Update embed description with reactions
            reactions_text = ""
            for reaction in self.reactions:
                reactions_text += f"{reaction['emoji']} → {reaction['role'].mention}\n"
            
            if reactions_text:
                # Clear existing fields to avoid duplication
                self.embed.clear_fields()
                self.embed.add_field(
                    name=_("role_reactions.available_roles", None, self.guild_id),
                    value=reactions_text,
                    inline=False
                )
            
            await message.edit(embed=self.embed)
            
            # Clear existing reactions and add new ones
            await message.clear_reactions()
            for reaction in self.reactions:
                try:
                    await message.add_reaction(reaction['emoji'])
                except:
                    pass  # Skip if reaction fails
                    
        except Exception as e:
            logger.error(f"Error updating message embed: {e}")

class AddReactionModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int, config_view: RoleReactionConfigView):
        super().__init__(title=_("role_reactions.add_reaction_modal_title", None, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        self.config_view = config_view
        
        self.emoji_input = discord.ui.TextInput(
            label=_("role_reactions.modal_emoji_label", None, guild_id),
            placeholder=_("role_reactions.modal_emoji_placeholder", None, guild_id),
            required=True,
            max_length=100
        )
        self.add_item(self.emoji_input)
        
        self.role_input = discord.ui.TextInput(
            label=_("role_reactions.modal_role_label", None, guild_id),
            placeholder=_("role_reactions.modal_role_placeholder", None, guild_id),
            required=True,
            max_length=100
        )
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse role
        role_input = self.role_input.value.strip()
        role = None
        
        if role_input.startswith('<@&') and role_input.endswith('>'):
            try:
                role_id = int(role_input[3:-1])
                role = interaction.guild.get_role(role_id)
            except ValueError:
                pass
        else:
            role = discord.utils.get(interaction.guild.roles, name=role_input)
        
        if not role:
            await interaction.response.send_message(
                _("role_reactions.role_not_found", interaction.user.id, self.guild_id, role=role_input),
                ephemeral=True
            )
            return
        
        # Check if emoji or role already exists
        emoji = self.emoji_input.value.strip()
        for existing in self.config_view.reactions:
            if existing['emoji'] == emoji:
                await interaction.response.send_message(
                    _("role_reactions.emoji_already_used", interaction.user.id, self.guild_id, emoji=emoji),
                    ephemeral=True
                )
                return
            if existing['role'].id == role.id:
                await interaction.response.send_message(
                    _("role_reactions.role_already_used", interaction.user.id, self.guild_id, role=role.name),
                    ephemeral=True
                )
                return
        
        # Add the reaction
        self.config_view.reactions.append({
            'emoji': emoji,
            'role': role
        })
        
        await interaction.response.send_message(
            _("role_reactions.reaction_added", interaction.user.id, self.guild_id, emoji=emoji, role=role.name),
            ephemeral=True
        )

class RemoveReactionSelectView(discord.ui.View):
    def __init__(self, bot, guild_id: int, config_view: RoleReactionConfigView):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.config_view = config_view
        
        # Create select options
        options = []
        for i, reaction in enumerate(config_view.reactions):
            options.append(discord.SelectOption(
                label=f"{reaction['emoji']} → {reaction['role'].name}",
                value=str(i),
                emoji=reaction['emoji']
            ))
        
        self.select = discord.ui.Select(
            placeholder=_("role_reactions.select_to_remove_placeholder", None, guild_id),
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        removed_reaction = self.config_view.reactions.pop(index)
        
        await interaction.response.send_message(
            _("role_reactions.reaction_removed", interaction.user.id, self.guild_id, 
              emoji=removed_reaction['emoji'], role=removed_reaction['role'].name),
            ephemeral=True
        )

class EditMessageModal(discord.ui.Modal):
    def __init__(self, bot, guild_id: int, config_view: RoleReactionConfigView, embed: discord.Embed):
        super().__init__(title=_("role_reactions.edit_message_modal_title", None, guild_id))
        self.bot = bot
        self.guild_id = guild_id
        self.config_view = config_view
        
        self.title_input = discord.ui.TextInput(
            label=_("role_reactions.modal_title_label", None, guild_id),
            placeholder=_("role_reactions.modal_title_placeholder", None, guild_id),
            default=embed.title,
            required=True,
            max_length=256
        )
        self.add_item(self.title_input)
        
        self.description_input = discord.ui.TextInput(
            label=_("role_reactions.modal_description_label", None, guild_id),
            placeholder=_("role_reactions.modal_description_placeholder", None, guild_id),
            default=embed.description,
            style=discord.TextStyle.long,
            required=False,
            max_length=2000
        )
        self.add_item(self.description_input)
        
        self.color_input = discord.ui.TextInput(
            label=_("role_reactions.modal_color_label", None, guild_id),
            placeholder=_("role_reactions.modal_color_placeholder", None, guild_id),
            default=f"#{embed.color.value:06x}" if embed.color else "#0099ff",
            required=False,
            max_length=7
        )
        self.add_item(self.color_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse color
        color = discord.Color.blue()  # Default
        if self.color_input.value:
            try:
                color_value = self.color_input.value.strip()
                if color_value.startswith('#'):
                    color_value = color_value[1:]
                color = discord.Color(int(color_value, 16))
            except ValueError:
                pass  # Keep default color
        
        # Update embed
        self.config_view.embed.title = self.title_input.value
        self.config_view.embed.description = self.description_input.value or _("role_reactions.default_description", interaction.user.id, self.guild_id)
        self.config_view.embed.color = color
        
        await interaction.response.send_message(
            _("role_reactions.message_updated", interaction.user.id, self.guild_id),
            ephemeral=True
        )

class RoleReactionManageView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Create New", style=discord.ButtonStyle.primary, emoji="🆕")
    async def create_new(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.create_new_button", interaction.user.id, self.guild_id)
        modal = RoleReactionCreateModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Edit Existing", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.edit_existing_button", interaction.user.id, self.guild_id)
        
        # Get existing role reaction messages
        result = await self.bot.db.query(
            "SELECT DISTINCT message_id FROM role_reactions WHERE guild_id = %s",
            (self.guild_id,),
            fetchall=True
        )
        
        if not result:
            await interaction.response.send_message(
                _("role_reactions.no_existing_messages", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Create select menu for existing messages
        select_view = EditExistingSelectView(self.bot, self.guild_id, result)
        await interaction.response.send_message(
            _("role_reactions.select_message_to_edit", interaction.user.id, self.guild_id),
            view=select_view,
            ephemeral=True
        )
    
    @discord.ui.button(label="Delete Message", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.delete_message_button", interaction.user.id, self.guild_id)
        
        # Get existing role reaction messages
        result = await self.bot.db.query(
            "SELECT DISTINCT message_id FROM role_reactions WHERE guild_id = %s",
            (self.guild_id,),
            fetchall=True
        )
        
        if not result:
            await interaction.response.send_message(
                _("role_reactions.no_existing_messages", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Create select menu for deletion
        select_view = DeleteMessageSelectView(self.bot, self.guild_id, result)
        await interaction.response.send_message(
            _("role_reactions.select_message_to_delete", interaction.user.id, self.guild_id),
            view=select_view,
            ephemeral=True
        )

class EditExistingSelectView(discord.ui.View):
    def __init__(self, bot, guild_id: int, messages: List[Dict]):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        
        # Create select options
        options = []
        for message_data in messages[:25]:  # Discord limit
            message_id = message_data['message_id']
            options.append(discord.SelectOption(
                label=f"Message ID: {message_id}",
                value=str(message_id),
                description=f"Click to edit this role reaction message"
            ))
        
        self.select = discord.ui.Select(
            placeholder=_("role_reactions.select_message_placeholder", None, guild_id),
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: discord.Interaction):
        message_id = int(self.select.values[0])
        
        # Try to fetch the message
        message = None
        for channel in interaction.guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                break
            except:
                continue
        
        if not message:
            await interaction.response.send_message(
                _("role_reactions.message_not_found", interaction.user.id, self.guild_id),
                ephemeral=True
            )
            return
        
        # Get existing reactions for this message
        result = await self.bot.db.query(
            "SELECT emoji, role_id FROM role_reactions WHERE guild_id = %s AND message_id = %s",
            (self.guild_id, message_id),
            fetchall=True
        )
        
        # Create config view with existing data
        embed = message.embeds[0] if message.embeds else discord.Embed(title="Role Reactions", color=discord.Color.blue())
        config_view = RoleReactionConfigView(self.bot, self.guild_id, message_id, embed)
        
        # Load existing reactions
        for row in result:
            role = interaction.guild.get_role(row['role_id'])
            if role:
                config_view.reactions.append({
                    'emoji': row['emoji'],
                    'role': role
                })
        
        await interaction.response.send_message(
            _("role_reactions.editing_message", interaction.user.id, self.guild_id, message_id=message_id),
            view=config_view,
            ephemeral=True
        )

class DeleteMessageSelectView(discord.ui.View):
    def __init__(self, bot, guild_id: int, messages: List[Dict]):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        
        # Create select options
        options = []
        for message_data in messages[:25]:  # Discord limit
            message_id = message_data['message_id']
            options.append(discord.SelectOption(
                label=f"Message ID: {message_id}",
                value=str(message_id),
                description=f"Click to delete this role reaction message",
                emoji="🗑️"
            ))
        
        self.select = discord.ui.Select(
            placeholder=_("role_reactions.select_message_to_delete_placeholder", None, guild_id),
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: discord.Interaction):
        message_id = int(self.select.values[0])
        
        # Create confirmation view
        confirm_view = ConfirmDeleteView(self.bot, self.guild_id, message_id)
        await interaction.response.send_message(
            _("role_reactions.confirm_delete", interaction.user.id, self.guild_id, message_id=message_id),
            view=confirm_view,
            ephemeral=True
        )

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, bot, guild_id: int, message_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.message_id = message_id
    
    @discord.ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.confirm_delete_button", interaction.user.id, self.guild_id)
        
        # Defer the response to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Delete from database
            await self.bot.db.query(
                "DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s",
                (self.guild_id, self.message_id)
            )
            
            # Remove from bot memory
            if self.guild_id in self.bot.role_reactions:
                if self.message_id in self.bot.role_reactions[self.guild_id]:
                    del self.bot.role_reactions[self.guild_id][self.message_id]
            
            # Try to delete the actual message
            message = None
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(self.message_id)
                    await message.delete()
                    break
                except:
                    continue
            
            await interaction.followup.send(
                _("role_reactions.message_deleted", interaction.user.id, self.guild_id),
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Error deleting message: {str(e)}",
                ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = _("role_reactions.cancel_delete_button", interaction.user.id, self.guild_id)
        await interaction.response.send_message(
            _("role_reactions.delete_cancelled", interaction.user.id, self.guild_id),
            ephemeral=True
        )
        self.stop()

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
        logger.info(f"Réaction ajoutée détectée: {payload.emoji}")

        if payload.user_id == self.bot.user.id:
            return

        role_map = self.bot.role_reactions.get(payload.guild_id, {}).get(payload.message_id)
        if role_map and str(payload.emoji) in role_map:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                logger.error("Guild introuvable")
                return

            member = guild.get_member(payload.user_id)
            if not member:
                logger.error("Membre introuvable")
                return

            role_id = role_map[str(payload.emoji)]
            role = guild.get_role(role_id)
            if not role:
                logger.error(f"Rôle ID {role_id} introuvable dans la guilde")
                return

            try:
                await member.add_roles(role)
                logger.info(f"Rôle {role.name} ajouté à {member.display_name}")

                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    user_id = payload.user_id
                    guild_id = payload.guild_id
                    msg = await channel.send(
                        _("role_reactions.role_gained", user_id, guild_id, user=f"<@{user_id}>", role=role.name)
                    )
                    await msg.delete(delay=5)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout du rôle: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        logger.info(f"Réaction supprimée détectée: {payload.emoji}")

        if payload.user_id == self.bot.user.id:
            return

        role_map = self.bot.role_reactions.get(payload.guild_id, {}).get(payload.message_id)
        if role_map and str(payload.emoji) in role_map:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                logger.error("Guild introuvable")
                return

            member = guild.get_member(payload.user_id)
            if not member:
                logger.error("Membre introuvable")
                return

            role_id = role_map[str(payload.emoji)]
            role = guild.get_role(role_id)
            if not role:
                logger.error(f"Rôle ID {role_id} introuvable dans la guilde")
                return

            try:
                await member.remove_roles(role)
                logger.info(f"Rôle {role.name} retiré de {member.display_name}")

                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    user_id = payload.user_id
                    guild_id = payload.guild_id
                    msg = await channel.send(
                        _("role_reactions.role_removed", user_id, guild_id, user=f"<@{user_id}>", role=role.name)
                    )
                    await msg.delete(delay=5)
            except Exception as e:
                logger.error(f"Erreur lors du retrait du rôle: {e}")

    @app_commands.command(name="rolereact", description="Configure role reactions with modern interface")
    @app_commands.checks.has_permissions(administrator=True)
    async def rolereact(self, interaction: discord.Interaction):
        logger.info("Commande rolereact appelée")
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Create main management view
        view = RoleReactionManageView(self.bot, guild_id)
        
        embed = discord.Embed(
            title=_("role_reactions.management_title", user_id, guild_id),
            description=_("role_reactions.management_description", user_id, guild_id),
            color=discord.Color.blue()
        )
        
        # Add current status
        result = await self.bot.db.query(
            "SELECT COUNT(DISTINCT message_id) as message_count, COUNT(*) as reaction_count FROM role_reactions WHERE guild_id = %s",
            (guild_id,),
            fetchone=True
        )
        
        if result:
            embed.add_field(
                name=_("role_reactions.current_status", user_id, guild_id),
                value=_("role_reactions.status_info", user_id, guild_id, 
                       messages=result['message_count'], reactions=result['reaction_count']),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RoleReact(bot))
    logger.info("Cog RoleReact chargé avec succès")
