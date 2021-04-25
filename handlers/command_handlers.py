import discord

from bot import client
import functions

from typing import Optional

from discord.ext import commands

from vk_parsing import get_audio

from get_tracks import *


def check_if_admin(ctx: commands.Context):
    _, _, guild_admins, _ = functions.get_guild_info(ctx.guild.id)
    return ctx.message.author.id in guild_admins


def check_if_owner(ctx: commands.Context):
    _, _, _, owner_id = functions.get_guild_info(ctx.guild.id)
    return ctx.message.author.id == owner_id


def check_if_me(ctx: commands.Context):
    return ctx.message.author.id == 242678412983009281


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


# VK MUSIC


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
@commands.check(check_if_me)
async def leave_command(ctx: commands.Context):
    voice = ctx.voice_client
    if voice.is_connected():
        await ctx.send("Leaving")
        await voice.disconnect()
    else:
        await ctx.send("Not connected to any voice channel")

skipped = {}


def play_next(error, voice, ctx, tracks, now_playing):
    global skipped
    if not skipped[ctx.guild.id]:
        voice.stop()
        print("ok")
        print(error)

        if (new_index := now_playing + 1) > len(tracks) - 1:
            new_index = 0
        voice.stop()
        voice.play(discord.FFmpegPCMAudio(source=tracks[new_index]["url"]),
                   after=lambda x: play_next(x, voice, ctx, tracks, new_index))
        change_index(ctx.guild.id, new_index)
    else:
        print("skipped")
        skipped[ctx.guild.id] = False


@client.command(name="play")
@commands.guild_only()
async def play_command(ctx: commands.Context, link: Optional[str] = None):
    voice = ctx.voice_client

    skipped[ctx.guild.id] = False
    if not voice or not voice.is_connected():
        await join_command(ctx)
        voice = ctx.voice_client

    if voice.is_paused():
        voice.resume()
        return
    if voice.is_playing():
        if not link:
            return

        voice.stop()
    tracks = await get_audio(link)
    write_tracks(ctx.guild.id, tracks)

    voice.play(discord.FFmpegPCMAudio(source=tracks[0]["url"]),
               after=lambda x: play_next(x, voice, ctx, tracks, 0))
    await ctx.send(f"Now playing: {tracks[0]['name']}")


@client.command(name="pause")
@commands.guild_only()
@commands.check(check_if_me)
async def pause_command(ctx: commands.Context):
    voice = ctx.voice_client
    if not voice.is_playing():
        await ctx.send("Nothing is playing")
        return
    voice.pause()


@client.command(name="stop")
@commands.guild_only()
@commands.check(check_if_me)
async def stop_command(ctx: commands.Context):
    voice = ctx.voice_client
    if not voice.is_playing():
        await ctx.send("Nothing is playing")
    else:
        voice.stop()

    delete_info(ctx.guild.id)
    del skipped[ctx.guild.id]


async def play_new_track(voice, ctx, tracks, index):
    voice.stop()
    voice.play(discord.FFmpegPCMAudio(source=tracks[index]["url"]),
               after=lambda x: play_next(x, voice, ctx, tracks, index))
    await ctx.send(f"Now playing: {tracks[index]['name']}")
    change_index(ctx.guild.id, index)


@client.command(name="skip")
@commands.guild_only()
async def skip_command(ctx: commands.Context, count: Optional[int] = 1):
    global skipped
    skipped[ctx.guild.id] = True
    voice = ctx.voice_client
    if not voice or not voice.is_connected():
        await ctx.send("Закинь в голосовой канал, ебана")
    else:
        tracks_info = get_tracks(ctx.guild.id)
        tracks, now_playing = tracks_info["tracks"], tracks_info["now_playing"]

        if (new_index := now_playing + count) > len(tracks)-1:
            new_index = 0
        await play_new_track(voice, ctx, tracks, new_index)


@client.command(name="prev")
@commands.guild_only()
async def prev_command(ctx: commands.Context, count: Optional[int] = 1):
    voice = ctx.voice_client
    if not voice or not voice.is_connected():
        await ctx.send("Ну ты совсем еблан чтоль?")
    else:
        tracks_info = get_tracks(ctx.guild.id)
        tracks, now_playing = tracks_info["tracks"], tracks_info["now_playing"]

        if (new_index := now_playing - count) < 0:
            new_index = len(tracks) - 1
        await play_new_track(voice, ctx, tracks, new_index)

# TODO сделать шобы перематывалось
