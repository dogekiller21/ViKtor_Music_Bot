import asyncio

import discord

from bot import client
import functions

from typing import Optional

from discord.ext import commands

from vk_parsing import get_audio, get_single_audio, NoTracksFound


def check_if_admin(ctx: commands.Context):
    guild_admins = functions.get_guild_smf(ctx.guild.id, "admins")
    return ctx.message.author.id in guild_admins


def check_if_owner(ctx: commands.Context):
    owner_id = ctx.guild.owner.id
    return ctx.message.author.id == owner_id


def check_if_me(ctx: commands.Context):
    return ctx.message.author.id == 242678412983009281


@client.command(name="admin", pass_context=True)
@commands.guild_only()
@commands.check(check_if_owner)
async def admin_command(ctx: commands.Context, member: discord.Member):
    guild_admins = functions.get_guild_smf(ctx.guild.id, "admins")

    if member.id not in guild_admins:
        functions.add_new_admin(ctx.guild.id, member.id)
        embed = discord.Embed(
            description=f'Пользователь {member.mention} назначен администратором'
        )
        await ctx.send(embed=embed)
    else:
        embed = functions.create_error_embed(
            message=f"Пользователь {member.mention} уже является администратором"
        )
        await ctx.send(embed=embed)


@client.command(name="user", pass_context=True)
@commands.guild_only()
@commands.check(check_if_owner)
async def user_command(ctx: commands.Context, member: discord.Member):
    if member.id == ctx.guild.owner.id:
        embed = functions.create_error_embed(
            message="Вы не можете забрать права администратора у владельца сервера"
        )
        return await ctx.send(embed=embed)
    guild_admin = functions.get_guild_smf(ctx.guild.id, "admins")

    if member.id in guild_admin:
        functions.demote_admin(ctx.guild.id, member.id)
        embed = functions.create_error_embed(
            message=f'Пользователь {member.mention} был разжалован'
        )
        await ctx.send(embed=embed)
    else:
        embed = functions.create_error_embed(
            message=f"Пользователь {member.mention} не является администратором"
        )
        await ctx.send(embed=embed)


@client.command(name="welcome_channel", pass_context=True)
@commands.guild_only()
@commands.check(check_if_admin)
async def welcome_channel_command(ctx: commands.Context, channel_id=None):
    if not channel_id:
        channel_id = ctx.channel.id
        msg_end = f'этом канале'
    elif not channel_id.isdigit():
        embed = functions.create_error_embed(
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


@client.command(name="welcome_role", pass_context=True)
@commands.guild_only()
@commands.check(check_if_admin)
async def welcome_role_command(ctx: commands.Context, role: Optional[discord.Role]):
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


@client.command(name="roles", pass_context=True)
@commands.guild_only()
async def roles_command(ctx: commands.Context, *, member: MemberRoles()):
    description = "\n\n".join([r.mention for r in reversed(member[1])])
    embed = discord.Embed(
        title=f"Роли {member[0].name}",
        description=description
    )
    await ctx.send(embed=embed)


# VK MUSIC


async def _join(ctx: commands.Context):
    user_channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(user_channel)
    else:
        await user_channel.connect()


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
            description=f"{new_index + 1}. {tracks[new_index]['name']}"
        )
        loop = client.loop
        asyncio.run_coroutine_threadsafe(ctx.send(embed=embed), loop)


@client.command(name="leave")
@commands.guild_only()
async def leave_command(ctx: commands.Context):
    await ctx.message.add_reaction("🚪")

    voice = ctx.voice_client
    if voice and voice.is_connected():
        functions.delete_info(ctx.guild.id)
        await voice.disconnect()
        await ctx.message.add_reaction("✔")
    else:
        embed = functions.create_error_embed("Not connected to any voice channel")

        await ctx.send(embed=embed)

        await ctx.message.add_reaction("❌")


async def nothing_is_playing_error(ctx: commands.Context):
    embed = functions.create_error_embed("Nothing is playing")
    await ctx.send(embed=embed)

    await ctx.message.add_reaction("❌")


@client.command(name="play")
@commands.guild_only()
async def play_command(ctx: commands.Context, *link: Optional[str]):
    await ctx.message.add_reaction("▶")

    if not ctx.author.voice:
        embed = functions.create_error_embed("You have to be connected to voice channel")

        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    if (len(link) > 0) and "vk.com/" not in link[0]:
        return await add_to_queue_command(ctx, *link)

    voice = ctx.voice_client

    if not voice and (len(link) == 0):
        embed = functions.create_error_embed(
            message="Add link or name of the track to command"
        )
        await ctx.message.add_reaction("❌")
        return await ctx.send(embed=embed)

    if not voice or not voice.is_connected():
        await _join(ctx)
        voice = ctx.voice_client
    elif (len(link) == 0) and not (voice.is_playing() or voice.is_paused()):
        return await nothing_is_playing_error(ctx)

    elif (voice.is_playing or voice.is_paused()) and (len(link) != 0):
        functions.delete_info(ctx.guild.id)
        voice.stop()

    elif voice.is_paused():

        voice.resume()

        return await ctx.message.add_reaction("✔")

    elif voice.is_playing():
        if len(link) == 0:
            return await ctx.message.add_reaction("✔")

        voice.stop()

    link = link[0]
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

    await ctx.message.add_reaction("✔")


@client.command(name="pause")
@commands.guild_only()
async def pause_command(ctx: commands.Context):
    await ctx.message.add_reaction("⏸")
    voice = ctx.voice_client
    if not voice.is_playing():
        return await nothing_is_playing_error(ctx)

    voice.pause()

    await ctx.message.add_reaction("✔")


@client.command(name="stop")
@commands.guild_only()
async def stop_command(ctx: commands.Context):
    await ctx.message.add_reaction("⏹")
    voice = ctx.voice_client
    if voice is None or not (voice.is_playing() or voice.is_paused()):
        await nothing_is_playing_error(ctx)
    elif voice.is_connected():
        functions.delete_info(ctx.guild.id)
        voice.stop()

        await ctx.message.add_reaction("✔")


@client.command(name="skip")
@commands.guild_only()
async def skip_command(ctx: commands.Context, *, count: Optional[int] = 1):
    await ctx.message.add_reaction("⏩")
    voice = ctx.voice_client
    if voice is None:
        await nothing_is_playing_error(ctx)

    else:
        tracks_info = functions.get_tracks(ctx.guild.id)
        if tracks_info is None:
            return await nothing_is_playing_error(ctx)

        tracks, index = tracks_info["tracks"], tracks_info["now_playing"]
        if (new_index := index + count) > len(tracks):
            new_index = 0

        # Change index and skip track by stopping playing current one
        functions.change_index(ctx.guild.id, new_index - 1)

        voice.stop()

        await ctx.message.add_reaction("✔")


@client.command(name="prev")
@commands.guild_only()
async def prev_command(ctx: commands.Context, *, count: Optional[int] = 1):
    await ctx.message.add_reaction("⏪")
    voice = ctx.voice_client
    if voice is None:
        await nothing_is_playing_error(ctx)

    else:
        tracks_info = functions.get_tracks(ctx.guild.id)
        if tracks_info is None:
            return await nothing_is_playing_error(ctx)

        tracks, index = tracks_info["tracks"], tracks_info["now_playing"]
        if (new_index := index - count) < 0:
            new_index = len(tracks) - 1

        functions.change_index(ctx.guild.id, new_index - 1)

        voice.stop()

        await ctx.message.add_reaction("✔")


@client.command(name="queue")
@commands.guild_only()
async def queue_command(ctx: commands.Context, *, page: Optional[int] = None):
    await ctx.message.add_reaction("📄")

    tracks_info = functions.get_tracks(ctx.guild.id)
    if tracks_info is None:
        embed = functions.create_error_embed("Queue is empty")
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    track_list, now_playing = tracks_info["tracks"], tracks_info["now_playing"]
    if page is None:
        if ((now_playing + 1) / 10) != 0:
            page = (now_playing + 1) // 10 + 1
        else:
            page = (now_playing + 1) // 10
    if page == 1:
        page_index = 0
    else:
        page_index = (page - 1) * 10
    tracks = []
    for i, track in enumerate(track_list[page_index::]):
        if i == 10:
            break
        track_index = i + (page - 1) * 10
        tracks.append(
            f"**{track_index + 1}. {track['name']}**"
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

    await ctx.message.add_reaction("✔")


@client.command(name="add", aliases=["add_to_queue"])
@commands.guild_only()
async def add_to_queue_command(ctx: commands.Context, *name):

    await ctx.message.add_reaction("🎧")

    reactions = ctx.message.reactions
    if reactions is not []:
        for reaction in reactions:
            if reaction.emoji == "▶":
                await ctx.message.remove_reaction("▶", client.user)
                break

    name = " ".join(name)
    voice = ctx.voice_client
    if not ctx.author.voice:
        embed = functions.create_error_embed(
            message="You have to be connected to voice channel"
        )
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    try:
        track = await get_single_audio(name)
        functions.add_track(ctx.guild.id, track)

        await ctx.message.add_reaction("✔")

    except NoTracksFound:
        embed = functions.create_error_embed(
            message=f"No tracks founded for you request {name}"
        )
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    except Exception as err:
        print(f"error: {err}")
        embed = functions.create_error_embed(
            message=f"Unknown error while processing request {name}"
        )
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    if not voice or not voice.is_connected() or not (voice.is_paused() or voice.is_playing()):

        await _join(ctx=ctx)
        voice = ctx.voice_client

        voice.play(discord.FFmpegPCMAudio(source=track["url"]),
                   after=lambda x: play_next(x, voice, ctx))
        embed = functions.create_music_embed(
            title="Now playing",
            description=track["name"]
        )
        await ctx.send(embed=embed)
    else:
        embed = functions.create_music_embed(
            title="Track added to queue",
            description=track["name"]
        )
        await ctx.send(embed=embed)


@client.command(name="delete", aliases=["remove"], pass_context=True)
@commands.guild_only()
async def delete_command(ctx: commands.Context, index: int):
    await ctx.message.add_reaction("💔")
    tracks_info = functions.get_tracks(ctx.guild.id)
    tracks, now_playing = tracks_info["tracks"], tracks_info["now_playing"]

    if (index <= 0) or (index > len(tracks)):
        embed = functions.create_error_embed(
            message="Incorrect index passed"
        )
        await ctx.message.add_reaction("❌")
        return await ctx.send(embed=embed)

    functions.delete_single_track(ctx.guild.id, index)
    if index - 1 == now_playing:
        if len(tracks) == 1:
            functions.delete_info(ctx.guild.id)
        else:
            functions.change_index(ctx.guild.id, now_playing - 1)
        voice = ctx.voice_client
        voice.stop()

    await ctx.message.add_reaction("✔")
