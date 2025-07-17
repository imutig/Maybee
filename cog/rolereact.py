import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from i18n import _

logger = logging.getLogger(__name__)

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

    @app_commands.command(name="rolereact",
                          description="Configurer les rôles par réaction")
    @app_commands.checks.has_permissions(administrator=True)
    async def rolereact(self, interaction: discord.Interaction):
        logger.info("Commande rolereact appelée")
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        await interaction.response.send_message(
            _("role_reactions.config_start", user_id, guild_id),
            ephemeral=True)
        config_list = []

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        while True:
            await interaction.followup.send(
                _("role_reactions.enter_message", user_id, guild_id),
                ephemeral=True)
            try:
                msg_input = await self.bot.wait_for('message',
                                                    check=check,
                                                    timeout=300.0)
            except asyncio.TimeoutError:
                logger.warning("Temps écoulé pour l'entrée du message")
                await interaction.followup.send(_("role_reactions.timeout", user_id, guild_id),
                                                ephemeral=True)
                return

            if msg_input.content.lower() == 'stop':
                logger.info("Configuration terminée par l'utilisateur")
                await interaction.followup.send(_("role_reactions.config_finished", user_id, guild_id),
                                                ephemeral=True)
                break

            await msg_input.delete()

            await interaction.followup.send(_("role_reactions.enter_emoji", user_id, guild_id),
                                            ephemeral=True)
            try:
                emoji_input = await self.bot.wait_for('message',
                                                      check=check,
                                                      timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning("Temps écoulé pour l'entrée de l'emoji")
                await interaction.followup.send(_("role_reactions.timeout", user_id, guild_id),
                                                ephemeral=True)
                return

            if emoji_input.content.lower() == 'stop':
                logger.info("Configuration terminée par l'utilisateur")
                await interaction.followup.send(_("role_reactions.config_finished", user_id, guild_id),
                                                ephemeral=True)
                break

            await emoji_input.delete()

            await interaction.followup.send(
                _("role_reactions.mention_role", user_id, guild_id), ephemeral=True)
            try:
                role_input = await self.bot.wait_for('message',
                                                     check=check,
                                                     timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning("Temps écoulé pour l'entrée du rôle")
                await interaction.followup.send(_("role_reactions.timeout", user_id, guild_id),
                                                ephemeral=True)
                return

            if role_input.content.lower() == 'stop':
                logger.info("Configuration terminée par l'utilisateur")
                await interaction.followup.send(_("role_reactions.config_finished", user_id, guild_id),
                                                ephemeral=True)
                break

            await role_input.delete()

            role_mention = role_input.content
            guild = interaction.guild
            if role_mention.startswith('<@&') and role_mention.endswith('>'):
                role_id = int(role_mention[3:-1])
                role = guild.get_role(role_id)
            else:
                role = discord.utils.get(guild.roles, name=role_mention)

            if not role:
                logger.warning(f"Le rôle {role_mention} n'existe pas")
                await interaction.followup.send(
                    _("role_reactions.role_not_found", user_id, guild_id, role=role_mention),
                    ephemeral=True)
                continue

            config_list.append({
                'message': msg_input.content,
                'emoji': emoji_input.content,
                'role': role
            })

        if not config_list:
            logger.warning("Aucune configuration ajoutée")
            await interaction.followup.send(_("role_reactions.no_config", user_id, guild_id),
                                            ephemeral=True)
            return

        embed_desc = ""
        for item in config_list:
            embed_desc += f"{item['emoji']} → {item['role'].mention} : {item['message']}\n"

        embed = discord.Embed(
            title=_("role_reactions.embed_title", user_id, guild_id),
            description=embed_desc,
            color=discord.Color.green())
        message = await interaction.channel.send(embed=embed)
        for item in config_list:
            await message.add_reaction(item['emoji'])

        self.bot.role_reactions.setdefault(interaction.guild.id, {})[message.id] = {}

        # Nettoyer la config existante en DB pour ce message et cette guild
        await self.bot.db.execute(
            "DELETE FROM role_reactions WHERE guild_id = %s AND message_id = %s",
            (interaction.guild.id, message.id)
        )
        for item in config_list:
            self.bot.role_reactions[interaction.guild.id][message.id][item['emoji']] = item['role'].id
            await self.bot.db.execute(
                "INSERT INTO role_reactions (guild_id, message_id, emoji, role_id) VALUES (%s, %s, %s, %s)",
                (interaction.guild.id, message.id, item['emoji'], item['role'].id)
            )

        confirmation_message = await interaction.channel.send(
            _("role_reactions.config_complete", user_id, guild_id)
        )
        await confirmation_message.delete(delay=5)


async def setup(bot):
    await bot.add_cog(RoleReact(bot))
    logger.info("Cog RoleReact chargé avec succès")
