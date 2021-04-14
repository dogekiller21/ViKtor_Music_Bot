import discord

from bot import client
import functions

from typing import Optional

from discord.ext import commands


def check_if_admin(ctx: commands.Context):
    _, _, guild_admins, _ = functions.get_guild_info(ctx.guild.id)
    return ctx.message.author.id in guild_admins


def check_if_owner(ctx: commands.Context):
    _, _, _, owner_id = functions.get_guild_info(ctx.guild.id)
    return ctx.message.author.id == owner_id


# @client.command(pass_context=True)
# @commands.guild_only()
# @commands.check(check_if_admin)
# async def test(ctx, member: discord.Member):
#     role = discord.utils.get(ctx.guild.roles, id=823136239711420437)
#     try:
#         await member.add_roles(role)
#     except Exception as err:
#         print(err)


@client.command(name="admin", pass_context=True)
@commands.guild_only()
@commands.check(check_if_owner)
async def admin_command(ctx: commands.Context, member: discord.Member):
    functions.json_write(ctx.guild.id, new_admin_id=int(member.id))
    await ctx.channel.send(f'Пользователь {member.mention} назначен администратором')


@client.command(name="user", pass_context=True)
@commands.guild_only()
@commands.check(check_if_owner)
async def user_command(ctx: commands.Context, member: discord.Member):
    functions.json_write(ctx.guild.id, admin_demotion_id=int(member.id))
    await ctx.channel.send(f'Пользователь {member.mention} был разжалован')


@client.command(name="welcome_channel", pass_context=True)
@commands.guild_only()
@commands.check(check_if_admin)
async def welcome_channel_command(ctx: commands.Context, channel_id=None):
    if not channel_id:
        channel_id = ctx.channel.id
        msg_end = f'этом канале'
    elif not channel_id.isdigit():
        await ctx.channel.send('ID канала может состоять только из цифр')
        return
    else:
        channel_id = int(channel_id)
        msg_end = f'канале с id {channel_id}'
    guild_id = ctx.guild.id
    functions.json_write(guild_id=guild_id, welcome_channel=channel_id)
    await ctx.channel.send(f'Теперь приветствие для новых пользователей будет писаться в {msg_end}')


@client.command(name="welcome_role", pass_context=True)
@commands.guild_only()
@commands.check(check_if_admin)
async def welcome_role_command(ctx: commands.Context, role: Optional[discord.Role]):
    if not role:
        role_id = functions.get_guild_info(ctx.guild.id)[1]
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        await ctx.channel.send(f'Текущая роль для новых пользователей {role.mention}\n'
                               f'Ее id: {role_id}')
    else:
        await ctx.channel.send(f'Теперь новым пользователям будет выдаваться роль {role.mention} с id: {role.id}')
        functions.json_write(guild_id=ctx.guild.id, welcome_role=role.id)


# Converter for user's roles
# Return list of discord.Role objects
class MemberRoles(commands.MemberConverter):
    async def convert(self, ctx: commands.Context, argument):
        member = await super().convert(ctx, argument)
        return member.roles[1:]


@client.command(name="roles", pass_context=True)
@commands.guild_only()
async def roles_command(ctx: commands.Context, *, member: MemberRoles()):
    msg = "\n".join([r.name for r in reversed(member)])
    await ctx.send(f"Твои роли:\n{msg}")


@client.command(name="join")
@commands.guild_only()
async def join_command(ctx: commands.Context):
    user_channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(user_channel)
    else:
        await ctx.send("Joining...")
        await user_channel.connect()


@client.command(name="leave")
@commands.guild_only()
async def leave_command(ctx: commands.Context):
    voice = ctx.voice_client
    if voice.is_connected():
        await ctx.send("Leaving")
        await voice.disconnect()
    else:
        await ctx.send("Not connected to any voice channel")


@client.command(name="play")
@commands.guild_only()
async def play_command(ctx: commands.Context):
    voice = ctx.voice_client

    if not voice or not voice.is_connected():
        await join_command(ctx)
        voice = ctx.voice_client
    if voice.is_paused():
        voice.resume()
        return
    voice.play(discord.FFmpegPCMAudio(source="music.mp3"))


@client.command(name="pause")
@commands.guild_only()
async def pause_command(ctx: commands.Context):
    voice = ctx.voice_client
    if not voice.is_playing():
        await ctx.send("Nothing is playing")
        return
    voice.pause()


@client.command(name="stop")
@commands.guild_only()
async def stop_command(ctx: commands.Context):
    voice = ctx.voice_client
    if not voice.is_playing():
        await ctx.send("Nothing is playing")
    else:
        voice.stop()
