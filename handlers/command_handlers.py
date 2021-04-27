import asyncio

import discord

from bot import client
import functions

from typing import Optional

from discord.ext import commands

from vk_parsing import get_audio

import concurrent.futures


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

@client.command(name="leave")
@commands.guild_only()
async def leave_command(ctx: commands.Context):
    voice = ctx.voice_client
    if voice and voice.is_connected():
        await voice.disconnect()
    else:
        embed = discord.Embed(
            description="Not connected to any voice channel",
            colour=0xe74c3c
        )
        await ctx.send(embed=embed)


async def _join(ctx: commands.Context):
    user_channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(user_channel)
    else:
        await user_channel.connect()

pool = concurrent.futures.ThreadPoolExecutor()


def play_next(error, voice: discord.VoiceClient, ctx: commands.Context):
    if error is not None:
        print(error)
    tracks_info = functions.get_tracks(ctx.guild.id)
    if tracks_info is not None:
        tracks, now_playing = tracks_info["tracks"], tracks_info["now_playing"]

        if (new_index := now_playing + 1) > len(tracks) - 1:
            new_index = 0
        voice.stop()

        voice.play(discord.FFmpegPCMAudio(source=tracks[new_index]["url"]),
                   after=lambda err: play_next(err, voice, ctx))
        functions.change_index(ctx.guild.id, new_index)
        embed = functions.create_music_embed(
            title="Now playing",
            description=f"{new_index+1}. {tracks[new_index]['name']}"
        )
        loop = client.loop
        asyncio.run_coroutine_threadsafe(ctx.send(embed=embed), loop)


@client.command(name="play")
@commands.guild_only()
async def play_command(ctx: commands.Context, *, link: Optional[str] = None):
    if not ctx.author.voice:
        embed = discord.Embed(
            description="You have to be connected to voice channel",
            colour=0xe74c3c
        )
        await ctx.send(embed=embed)
        return

    if link and "vk.com/" not in link:
        embed = discord.Embed(
            description="I can play only VK music!",
            colour=0xe74c3c
        )
        await ctx.send(embed=embed)
        return

    voice = ctx.voice_client
    if not voice or not voice.is_connected():
        await _join(ctx)
        voice = ctx.voice_client

    elif (voice.is_playing or voice.is_paused()) and link is not None:
        try:
            functions.delete_info(ctx.guild.id)
        except KeyError:
            pass
        finally:
            voice.stop()

    elif voice.is_paused():
        voice.resume()
        return
    elif voice.is_playing():
        if not link:
            return

        voice.stop()
    tracks = await get_audio(link)
    functions.write_tracks(ctx.guild.id, tracks)

    voice.play(discord.FFmpegPCMAudio(source=tracks[0]["url"]),
               after=lambda x: play_next(x, voice, ctx))

    if len(tracks) > 1:
        description = f"1. {tracks[0]['name']}"
    else:
        description = f"{tracks[0]['name']}"

    embed = functions.create_music_embed(
        title="Now playing",
        description=description
    )

    await ctx.send(embed=embed)


@client.command(name="pause")
@commands.guild_only()
async def pause_command(ctx: commands.Context):
    voice = ctx.voice_client
    if not voice.is_playing():
        embed = functions.create_error_embed("Nothing is playing")

        await ctx.send(embed=embed)
        return
    voice.pause()


@client.command(name="stop")
@commands.guild_only()
async def stop_command(ctx: commands.Context):
    voice = ctx.voice_client
    if voice.is_connected():
        functions.delete_info(ctx.guild.id)
        voice.stop()
    else:
        embed = functions.create_error_embed("Not connected to any voice channel")

        await ctx.send(embed=embed)


@client.command(name="skip")
@commands.guild_only()
async def skip_command(ctx: commands.Context, *, count: Optional[int] = 1):
    voice = ctx.voice_client
    if not voice or not voice.is_connected():
        embed = functions.create_error_embed("Закинь в голосовой канал, ебана")

        await ctx.send(embed=embed)
    else:
        tracks_info = functions.get_tracks(ctx.guild.id)
        if tracks_info is None:
            embed = functions.create_error_embed("Nothing is playing")
            await ctx.send(embed=embed)
            return

        tracks, index = tracks_info["tracks"], tracks_info["now_playing"]
        if (new_index := index + count) > len(tracks):
            new_index = 0

        # Change index and skip track by stopping playing current one
        functions.change_index(ctx.guild.id, new_index-1)

        voice.stop()


@client.command(name="prev")
@commands.guild_only()
async def prev_command(ctx: commands.Context, *, count: Optional[int] = 1):

    voice = ctx.voice_client
    if not voice or not voice.is_connected():
        embed = functions.create_error_embed("Ну ты совсем еблан чтоль?")

        await ctx.send(embed=embed)
    else:
        tracks_info = functions.get_tracks(ctx.guild.id)
        if tracks_info is None:
            embed = functions.create_error_embed("Nothing is playing")
            await ctx.send(embed=embed)
            return

        tracks, index = tracks_info["tracks"], tracks_info["now_playing"]
        if (new_index := index - count) < 0:
            new_index = len(tracks) - 1

        functions.change_index(ctx.guild.id, new_index-1)

        voice.stop()


@client.command(name="queue")
@commands.guild_only()
async def queue_command(ctx: commands.Context, *, page: Optional[int] = 1):
    tracks_info = functions.get_tracks(ctx.guild.id)
    track_list, now_playing = tracks_info["tracks"], tracks_info["now_playing"]
    if page == 1:
        page_index = 0
    else:
        page_index = (page-1) * 10
    tracks = []
    for i, track in enumerate(track_list[page_index::]):
        if i == 10:
            break
        track_index = i+(page-1)*10
        tracks.append(
            f"**{track_index+1}. {track['name']}**"
        )
        if track_index == now_playing:
            tracks[-1] += "\n↑ now playing ↑"

    pages = None
    if (length := len(track_list)) > 10:
        if length % 10 != 0:
            pages = length // 10 + 1
        else:
            pages = length // 10
        pages = f"Page: {page} / {pages}"

    embed = functions.create_queue_embed(
        description="\n\n".join(tracks),
        image="https://avatanplus.ru/files/resources/original/567059bd72e8a151a6de8c1f.png",
        pages=pages
    )

    await ctx.send(embed=embed)
