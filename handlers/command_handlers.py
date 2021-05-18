import asyncio
from random import shuffle
from dataclasses import asdict
from typing import Optional
import discord

from bot import client
import functions

from discord.ext import commands
from vk_parsing import get_audio, get_single_audio
from utils import embed_utils, tracks_utils
from utils.custom_exceptions import NoTracksFound


def check_if_owner(ctx: commands.Context):
    owner_id = ctx.guild.owner.id
    return ctx.message.author.id == owner_id


def check_if_me(ctx: commands.Context):
    return ctx.message.author.id == 242678412983009281


@client.command(name="welcome_channel", pass_context=True)
@commands.guild_only()
@commands.check(check_if_owner)
async def welcome_channel_command(ctx: commands.Context, channel_id=None):
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


@client.command(name="welcome_role", pass_context=True)
@commands.guild_only()
@commands.check(check_if_owner)
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
    tracks_info = tracks_utils.get_tracks(ctx.guild.id)
    if tracks_info is not None:
        tracks, now_playing = tracks_info.tracks, tracks_info.now_playing
        loop = client.loop

        if (new_index := now_playing + 1) > len(tracks) - 1:
            args = {
                "ctx": ctx,
                "voice_client": voice,
                "default": 0
            }
            new_index = asyncio.run_coroutine_threadsafe(
                queue_index_overflow(**args),
                loop
            ).result()
        if new_index is None:
            return
        voice.stop()

        voice.play(discord.FFmpegPCMAudio(source=tracks[new_index].url),
                   after=lambda err: play_next(err, voice, ctx))
        tracks_utils.change_index(ctx.guild.id, new_index)

        asyncio.run_coroutine_threadsafe(tracks_utils.queue_message_update(ctx), loop)


@client.command(name="leave")
@commands.guild_only()
async def leave_command(ctx: commands.Context):
    await ctx.message.add_reaction("🚪")

    voice = ctx.voice_client
    if voice and voice.is_connected():
        tracks_utils.delete_info(ctx.guild.id)
        tracks_utils.clear_queue_info(ctx.guild.id)
        await voice.disconnect()
        await ctx.message.add_reaction("✔")
    else:
        embed = embed_utils.create_error_embed("Not connected to any voice channel")

        await ctx.send(embed=embed)

        await ctx.message.add_reaction("❌")


async def nothing_is_playing_error(ctx: commands.Context):
    embed = embed_utils.create_error_embed("Nothing is playing")
    await ctx.send(embed=embed)

    await ctx.message.add_reaction("❌")


@client.command(name="play")
@commands.guild_only()
async def play_command(ctx: commands.Context, *link: Optional[str]):

    if not ctx.author.voice:
        embed = embed_utils.create_error_embed("You have to be connected to voice channel")

        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    if (len(link) > 0) and "vk.com/" not in link[0]:
        return await add_to_queue_command(ctx, *link)

    voice = ctx.voice_client

    if not voice and (len(link) == 0):
        embed = embed_utils.create_error_embed(
            message="Add link or name of the track to command"
        )
        await ctx.message.add_reaction("❌")
        return await ctx.send(embed=embed)

    if not voice or not voice.is_connected():
        await _join(ctx)
        voice = ctx.voice_client
    elif (len(link) == 0) and not (voice.is_playing() or voice.is_paused()):
        return await nothing_is_playing_error(ctx)

    elif (voice.is_playing() or voice.is_paused()) and (len(link) != 0):
        tracks_utils.delete_info(ctx.guild.id)
        tracks_utils.clear_queue_info(ctx.guild.id)
        voice.stop()

    elif voice.is_paused():
        voice.resume()
        return await tracks_utils.queue_message_update(ctx)

    elif voice.is_playing():
        if len(link) == 0:
            return
        voice.stop()

    link = link[0]
    tracks = await get_audio(link)
    tracks_utils.write_tracks(ctx.guild.id, tracks)

    await queue_command(ctx)

    voice.play(discord.FFmpegPCMAudio(source=tracks[0]["url"]),
               after=lambda x: play_next(x, voice, ctx))


@client.command(name="pause")
@commands.guild_only()
async def pause_command(ctx: commands.Context):
    voice = ctx.voice_client
    if not voice.is_playing():
        return await nothing_is_playing_error(ctx)
    voice.pause()
    await tracks_utils.queue_message_update(ctx)


@client.command(name="stop")
@commands.guild_only()
async def stop_command(ctx: commands.Context):
    voice = ctx.voice_client
    if voice is None or not (voice.is_playing() or voice.is_paused()):
        await nothing_is_playing_error(ctx)
    elif voice.is_connected():
        tracks_utils.delete_info(ctx.guild.id)
        tracks_utils.clear_queue_info(ctx.guild.id)
        voice.stop()


async def queue_index_overflow(
        ctx: commands.Context,
        voice_client: discord.VoiceClient,
        default: int
):

    is_looping = functions.get_guild_smf(ctx.guild.id, "loop_queue")
    if is_looping:
        new_index = default
    else:
        embed = embed_utils.create_info_embed(
            description="Queue loop is disabled in your guild\n"
                        "Deleting queue"
        )
        await ctx.send(embed=embed)
        tracks_utils.delete_info(ctx.guild.id)
        tracks_utils.clear_queue_info(ctx.guild.id)
        new_index = None
    voice_client.stop()
    return new_index


@client.command(name="skip")
@commands.guild_only()
async def skip_command(ctx: commands.Context, *, count: Optional[int] = 1):
    voice = ctx.voice_client
    if voice is None:
        await nothing_is_playing_error(ctx)

    else:
        tracks_info = tracks_utils.get_tracks(ctx.guild.id)
        if tracks_info is None:
            return await nothing_is_playing_error(ctx)

        tracks, index = tracks_info.tracks, tracks_info.now_playing
        if (new_index := index + count) > len(tracks)-1:
            new_index = await queue_index_overflow(
                ctx=ctx,
                voice_client=voice,
                default=0
            )
        if new_index is not None:
            tracks_utils.change_index(ctx.guild.id, new_index - 1)
            voice.stop()


@client.command(name="prev")
@commands.guild_only()
async def prev_command(ctx: commands.Context, *, count: Optional[int] = 1):
    voice = ctx.voice_client
    if voice is None:
        await nothing_is_playing_error(ctx)

    else:
        tracks_info = tracks_utils.get_tracks(ctx.guild.id)
        if tracks_info is None:
            return await nothing_is_playing_error(ctx)

        tracks, index = tracks_info.tracks, tracks_info.now_playing
        if (new_index := index - count) < 0:
            new_index = await queue_index_overflow(
                ctx=ctx,
                voice_client=voice,
                default=len(tracks) - 1
            )
        if new_index is not None:
            tracks_utils.change_index(ctx.guild.id, new_index - 1)
            voice.stop()


@client.command(name="queue")
@commands.guild_only()
async def queue_command(ctx: commands.Context, *, page: Optional[int] = None):
    if ctx.message.author != client.user:
        await ctx.message.add_reaction("📄")

    page, pages = tracks_utils.get_pages(ctx.guild.id, page)

    if page > pages:
        embed = embed_utils.create_error_embed("No such page in your queue")
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    embed = embed_utils.create_queue_embed(ctx, page=page)
    queue_message = await ctx.send(embed=embed)

    tracks_utils.add_queue_message(ctx.guild.id, queue_message)

    emoji_list = ["🔀", "⏪", "▶", "⏩", "⏹", "🔁"]
    for emoji in emoji_list:
        await queue_message.add_reaction(emoji)

    return queue_message


@client.command(name="add", aliases=["add_to_queue"])
@commands.guild_only()
async def add_to_queue_command(ctx: commands.Context, *name):
    await ctx.message.add_reaction("🎧")

    if not ctx.author.voice:
        embed = embed_utils.create_error_embed(
            message="You have to be connected to voice channel"
        )
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    voice = ctx.voice_client
    name = " ".join(name)
    try:
        track = await get_single_audio(name)
        tracks_utils.add_track(ctx.guild.id, track)

    except NoTracksFound:
        embed = embed_utils.create_error_embed(
            message=f"No tracks founded for you request **{name}**"
        )
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    except Exception as err:
        print(f"error: {err}")
        embed = embed_utils.create_error_embed(
            message=f"Unknown error while processing request **{name}**"
        )
        await ctx.send(embed=embed)

        return await ctx.message.add_reaction("❌")

    if not voice or not voice.is_connected() or not (voice.is_paused() or voice.is_playing()):

        await _join(ctx=ctx)
        voice = ctx.voice_client
        await queue_command(ctx)

        voice.play(discord.FFmpegPCMAudio(source=track["url"]),
                   after=lambda x: play_next(x, voice, ctx))

    else:
        embed = embed_utils.create_music_embed(
            title="Track added to queue",
            description=track["name"]
        )
        await ctx.send(embed=embed)
        try:
            await tracks_utils.queue_message_update(ctx)
        except Exception as err:
            print(err)


@client.command(name="delete", aliases=["remove"], pass_context=True)
@commands.guild_only()
async def delete_command(ctx: commands.Context, index: int):
    await ctx.message.add_reaction("💔")
    tracks_info = tracks_utils.get_tracks(ctx.guild.id)
    tracks, now_playing = tracks_info.tracks, tracks_info.now_playing

    if (index <= 0) or (index > len(tracks)):
        embed = embed_utils.create_error_embed(
            message="Incorrect index passed"
        )
        await ctx.message.add_reaction("❌")
        return await ctx.send(embed=embed)

    tracks_utils.delete_single_track(ctx.guild.id, index)
    if index - 1 == now_playing:
        if len(tracks) == 1:
            tracks_utils.delete_info(ctx.guild.id)
            tracks_utils.clear_queue_info(ctx.guild.id)
        else:
            tracks_utils.change_index(ctx.guild.id, now_playing - 1)
        voice = ctx.voice_client
        voice.stop()
    embed = embed_utils.create_music_embed(
        description=f"Track deleted: {tracks[index - 1].name}"
    )

    await ctx.message.add_reaction("✔")
    await ctx.send(embed=embed)

    if ctx.message.author == client.user:
        await tracks_utils.queue_message_update(ctx)


@client.command(name="jump", pass_context=True)
@commands.guild_only()
async def jump_command(ctx: commands.Context, index: int):
    voice = ctx.voice_client
    if not voice or not voice.is_connected():
        return await nothing_is_playing_error(ctx)

    tracks_info = tracks_utils.get_tracks(ctx.guild.id)
    tracks = tracks_info.tracks
    if index > len(tracks) or index <= 0:
        embed = embed_utils.create_error_embed(
            message=f"Incorrect index passed. Max index is {len(tracks)}"
        )
        await ctx.send(embed=embed)
        return await ctx.message.add_reaction("✔")
    tracks_utils.change_index(ctx.guild.id, index - 2)
    voice.stop()


@client.command(name="loop", pass_context=True)
@commands.guild_only()
async def loop_command(ctx: commands.Context):
    is_looped = functions.get_guild_smf(ctx.guild.id, "loop_queue")
    functions.change_loop_option(ctx.guild.id, not is_looped)
    if ctx.message.author == client.user:
        await tracks_utils.queue_message_update(ctx)
        return
    if is_looped:
        embed = embed_utils.create_info_embed(
            description="Loop option set as False\n"
                        "Queue in your guild is not looped now"
        )
    else:
        embed = embed_utils.create_info_embed(
            description="Loop option set as True\n"
                        "Queue in your guilds is looped now"
        )
    await ctx.send(embed=embed)


@client.command(name="shuffle", pass_context=True)
@commands.guild_only()
async def shuffle_command(ctx: commands.Context):
    voice = ctx.voice_client
    if voice is not None and (voice.is_playing() or voice.is_paused()):
        tracks = tracks_utils.get_tracks(ctx.guild.id).tracks
        if len(tracks) == 1:
            return
        shuffle(tracks)
        tracks_utils.write_tracks(
            guild_id=ctx.guild.id,
            track_list=[asdict(track) for track in tracks],
            index=-1
        )
        voice.stop()
