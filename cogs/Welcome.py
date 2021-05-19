from typing import Optional

import discord
from discord.ext import commands

import functions
from utils import embed_utils


def check_if_owner(ctx: commands.Context):
    owner_id = ctx.guild.owner.id
    return ctx.message.author.id == owner_id


class Welcome(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(name="welcome_channel", pass_context=True)
    @commands.guild_only()
    @commands.check(check_if_owner)
    async def welcome_channel_command(self, ctx: commands.Context, channel_id=None):
        if not channel_id:
            channel_id = ctx.channel.id
            msg_end = f'этом канале'
        elif not channel_id.isdigit():
            embed = embed_utils.create_error_embed(
                message="ID канала может состоять только из цифр"
            )
            return await ctx.send(embed=embed)

        else:
            channel_id = int(channel_id)
            msg_end = f'канале с id {channel_id}'

        functions.write_welcome_channel(ctx.guild.id, channel_id)
        embed = discord.Embed(
            description=f'Теперь приветствие для новых пользователей будет писаться в {msg_end}'
        )
        await ctx.send(embed=embed)

    @commands.command(name="welcome_role", pass_context=True)
    @commands.guild_only()
    @commands.check(check_if_owner)
    async def welcome_role_command(self, ctx: commands.Context, role: Optional[discord.Role]):
        if not role:
            role_id = functions.get_guild_smf(ctx.guild.id, "welcome_role_id")
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            embed = discord.Embed(
                description=f'Текущая роль для новых пользователей {role.mention}'
            )

            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f'Теперь новым пользователям будет выдаваться роль {role.mention}'
            )
            await ctx.send(embed=embed)
            functions.write_welcome_role(ctx.guild.id, role.id)

    # Converter for user's roles
    # Return list of discord.Role objects
    class MemberRoles(commands.MemberConverter):
        async def convert(self, ctx: commands.Context, argument):
            member = await super().convert(ctx, argument)
            return member, member.roles[1:]

    @commands.command(name="roles", pass_context=True)
    @commands.guild_only()
    async def roles_command(self, ctx: commands.Context, *, member: MemberRoles()):
        description = "\n\n".join([r.mention for r in reversed(member[1])])
        embed = discord.Embed(
            title=f"Роли {member[0].name}",
            description=description
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = functions.get_guild_smf(member.guild.id, "welcome_channel_id")
        role = functions.get_guild_smf(member.guild.id, "welcome_role_id")
        msg_channel = self.client.get_channel(channel)
        if role:
            user_role = discord.utils.get(member.guild.roles, id=role)
            try:
                await member.add_roles(user_role)
            except Exception as err:
                embed = embed_utils.create_error_embed(
                    message=f'Невозможно выдать роль {user_role.mention} участнику {member.mention}'
                )
                await msg_channel.send(embed=embed)
                print(err)
        message = discord.Embed(
            title='Новый пользователь!',
            description=f'Добро пожаловать, кожаный ублюдок {member.mention}',
            color=0x0a7cff
        )

        await msg_channel.send(embed=message)


def setup(client):
    client.add_cog(Welcome(client))
