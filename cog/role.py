import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button
import yaml
import os

ROLE_REQUEST_CHANNEL_ID = 1393935449944227931
REQUESTS_FILE = "data/role_requests.yaml"


def load_requests():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_requests(data):
    with open(REQUESTS_FILE, "w") as f:
        yaml.dump(data, f)


class RoleRequestView(View):

    def __init__(self, bot, user_id, role_id, action, message_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.role_id = role_id
        self.action = action
        self.message_id = message_id

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "🚫 Tu n'as pas la permission.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Accepter",
                       style=ButtonStyle.green,
                       custom_id="role_accept")
    async def accept_button(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        role = guild.get_role(self.role_id)

        if not member or not role:
            await interaction.response.send_message(
                "Erreur : membre ou rôle introuvable.", ephemeral=True)
            return

        try:
            if self.action == "add":
                await member.add_roles(role)
                action_done = "ajouté"
            else:
                await member.remove_roles(role)
                action_done = "retiré"
        except Exception as e:
            await interaction.response.send_message(f"Erreur : {e}",
                                                    ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Statut",
                        value=f"✅ Accepté par {interaction.user.mention}",
                        inline=False)
        embed.add_field(
            name="Action effectuée",
            value=f"Rôle **{role.name}** {action_done} à {member.mention}",
            inline=False)

        await interaction.response.edit_message(content=None,
                                                embed=embed,
                                                view=None)

        data = load_requests()
        data.pop(str(self.message_id), None)
        save_requests(data)

    @discord.ui.button(label="❌ Refuser",
                       style=ButtonStyle.red,
                       custom_id="role_deny")
    async def deny_button(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        role = guild.get_role(self.role_id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Statut",
                        value=f"❌ Refusé par {interaction.user.mention}",
                        inline=False)

        await interaction.response.edit_message(content=None,
                                                embed=embed,
                                                view=None)

        data = load_requests()
        data.pop(str(self.message_id), None)
        save_requests(data)


class RoleRequest(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    role_group = app_commands.Group(name="role", description="Demande un rôle")

    @role_group.command(name="add", description="Demande à ajouter un rôle")
    async def role_add(self, interaction: Interaction, role: discord.Role):
        await self.handle_request(interaction, role, "add")

    @role_group.command(name="remove", description="Demande à retirer un rôle")
    async def role_remove(self, interaction: Interaction, role: discord.Role):
        await self.handle_request(interaction, role, "remove")

    async def handle_request(self, interaction: Interaction,
                             role: discord.Role, action: str):
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Je ne peux pas modifier ce rôle (trop haut).",
                ephemeral=True)
            return

        verb = "ajouter" if action == "add" else "retirer"
        embed = discord.Embed(
            title="Demande de rôle",
            description=
            f"{interaction.user.mention} demande de **{verb}** le rôle {role.mention}",
            color=discord.Color.blurple(),
        )
        embed.set_footer(
            text=f"ID Utilisateur : {interaction.user.id} | ID Rôle : {role.id}"
        )

        view = RoleRequestView(self.bot,
                               user_id=interaction.user.id,
                               role_id=role.id,
                               action=action)

        channel = interaction.guild.get_channel(ROLE_REQUEST_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message(
                "⚠️ Salon de demandes introuvable.", ephemeral=True)
            return

        message = await channel.send(embed=embed, view=view)
        view.message_id = message.id

        # Enregistrer la demande
        data = load_requests()
        data[str(message.id)] = {
            "user_id": interaction.user.id,
            "role_id": role.id,
            "action": action,
        }
        save_requests(data)

        await interaction.response.send_message(
            f"📨 Ta demande pour **{verb}** le rôle a été envoyée dans {channel.mention} !",
            ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        data = load_requests()
        for guild in self.bot.guilds:
            for message_id, info in data.items():
                try:
                    channel = guild.get_channel(ROLE_REQUEST_CHANNEL_ID)
                    if not channel:
                        continue
                    message = await channel.fetch_message(int(message_id))
                    view = RoleRequestView(
                        self.bot,
                        user_id=info["user_id"],
                        role_id=info["role_id"],
                        action=info.get("action", "add"),
                        message_id=message.id,
                    )
                    await message.edit(view=view)
                except Exception as e:
                    print(
                        f"[ERREUR] Impossible de restaurer une demande : {e}")


async def setup(bot):
    await bot.add_cog(RoleRequest(bot))
