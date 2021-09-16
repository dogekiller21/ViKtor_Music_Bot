from typing import Optional

import discord
from discord.ext import commands

from bot import functions
from bot.utils import embed_utils


def check_if_owner(ctx: commands.Context):
    owner_id = ctx.guild.owner.id
    return ctx.message.author.id == owner_id


class Welcome(commands.Cog):
    """Приветствие и выдача ролей новым пользователям. (!) Требуются права администратора для работы"""

    def __init__(self, client):
        self.client = client

    @commands.command(name="welcome_channel", pass_context=True)
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def welcome_channel_command(self, ctx: commands.Context, channel_id=None):
        """Изменение канала для приветствия. После команды достаточно упомянуть канал или написать его id"""
        if not channel_id:
            channel_id = ctx.channel.id
            msg_end = f"этом канале"
        elif not channel_id.isdigit():
            embed = embed_utils.create_error_embed(
                message="ID канала может состоять только из цифр"
            )
            return await ctx.send(embed=embed)

        else:
            channel_id = int(channel_id)
            msg_end = f"канале с id {channel_id}"

        functions.write_welcome_channel(ctx.guild.id, channel_id)
        embed = discord.Embed(
            description=f"Теперь приветствие для новых пользователей будет писаться в {msg_end}"
        )
        await ctx.send(embed=embed)

    @commands.command(name="welcome_role", pass_context=True)
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def welcome_role_command(
        self, ctx: commands.Context, role: Optional[discord.Role]
    ):
        """Изменение роли для новых пользователей. После команды упомяните роль, которую хотите задать.
        Если команда будет написана без роли, бот подскажет какая роль установлена сейчас"""

        if not role:
            role_id = functions.get_guild_smf(ctx.guild.id, "welcome_role_id")
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            embed = discord.Embed(
                description=f"Текущая роль для новых пользователей {role.mention}"
            )

            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"Теперь новым пользователям будет выдаваться роль {role.mention}"
            )
            await ctx.send(embed=embed)
            functions.write_welcome_role(ctx.guild.id, role.id)

    async def _give_role(self, member: discord.Member, role: discord.Role):
        if not member.guild.me.guild_permissions.manage_roles:
            return
        user_role = discord.utils.get(member.guild.roles, id=role)
        if user_role is None:
            return
        await member.add_roles(user_role)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = functions.get_guild_smf(member.guild.id, "welcome_channel_id")
        role = functions.get_guild_smf(member.guild.id, "welcome_role_id")
        msg_channel = self.client.get_channel(channel)
        if role:
            await self._give_role(member, role)
        message = discord.Embed(
            title="Новый пользователь!",
            description=f"Добро пожаловать, кожаный ублюдок {member.mention}",
            color=0x0A7CFF,
        )

        await msg_channel.send(embed=message)


def setup(client):
    client.add_cog(Welcome(client))
