import discord
from discord.ext import commands
from datetime import datetime


class RulesValidation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _format_template(self, text: str, member: discord.Member) -> str:
        base = text or ""
        return (
            base
            .replace("{user}", member.mention)
            .replace("{username}", member.display_name)
            .replace("{server}", member.guild.name)
            .replace("{channel}", "#" + member.guild.system_channel.name if member.guild.system_channel else "")
            .replace("{avatar}", str(member.display_avatar.url))
        )

    def _safe_color(self, hex_color: str, fallback: int = 0x5865F2) -> int:
        try:
            return int((hex_color or "#5865F2").replace("#", ""), 16)
        except Exception:
            return fallback

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "") if interaction.data else ""
        if not custom_id.startswith("rules_accept_"):
            return

        guild = interaction.guild
        member = interaction.user
        if not guild or not isinstance(member, discord.Member):
            return

        try:
            config = await self.bot.db.query(
                "SELECT * FROM rules_validation_config WHERE guild_id = %s",
                (str(guild.id),),
                fetchone=True
            )
            if not config:
                await interaction.response.send_message("Configuration du règlement introuvable.", ephemeral=True)
                return

            acceptance = await self.bot.db.query(
                "SELECT accepted_at FROM rules_acceptances WHERE guild_id = %s AND user_id = %s",
                (str(guild.id), str(member.id)),
                fetchone=True
            )
            if acceptance:
                await interaction.response.send_message("Tu as déjà validé le règlement.", ephemeral=True)
                return

            await self.bot.db.query(
                "INSERT INTO rules_acceptances (guild_id, user_id, accepted_at) VALUES (%s, %s, %s)",
                (str(guild.id), str(member.id), datetime.utcnow())
            )

            granted_role_name = None
            grant_role_id = config.get("grant_role_id")
            if grant_role_id:
                role = guild.get_role(int(grant_role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Rules validated")
                        granted_role_name = role.name
                    except Exception:
                        granted_role_name = None

            if config.get("welcome_enabled") and config.get("welcome_channel_id"):
                welcome_channel = guild.get_channel(int(config["welcome_channel_id"]))
                if welcome_channel:
                    embed_title = self._format_template(config.get("welcome_embed_title") or "Bienvenue {username} !", member)
                    embed_description = self._format_template(config.get("welcome_embed_description") or "{user} vient de valider le règlement.", member)
                    embed_footer = self._format_template(config.get("welcome_embed_footer") or "Profite bien de ton arrivée !", member)
                    thumb_value = self._format_template(config.get("welcome_embed_thumbnail_url") or "{avatar}", member)
                    image_value = self._format_template(config.get("welcome_embed_image_url") or "", member)

                    embed = discord.Embed(
                        title=embed_title,
                        description=embed_description,
                        color=self._safe_color(config.get("welcome_embed_color"))
                    )
                    if thumb_value:
                        embed.set_thumbnail(url=thumb_value)
                    if image_value:
                        embed.set_image(url=image_value)
                    if embed_footer:
                        embed.set_footer(text=embed_footer)

                    await welcome_channel.send(content=member.mention, embed=embed)

            ack = "✅ Règlement validé."
            if granted_role_name:
                ack += f" Rôle attribué: {granted_role_name}."

            await interaction.response.send_message(ack, ephemeral=True)

        except Exception as e:
            print(f"Rules validation interaction error: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Erreur lors de la validation du règlement.", ephemeral=True)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(RulesValidation(bot))
