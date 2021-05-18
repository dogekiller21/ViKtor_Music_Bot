from typing import Optional

import discord

import functions
from utils import tracks_utils
from utils.custom_exceptions import EmptyQueue


def create_error_embed(
        message: str,
        image: Optional[str] = None
) -> discord.Embed:
    embed = discord.Embed(
        description=message,
        color=0xe74c3c
    )
    if image is not None:
        embed.set_thumbnail(url=image)
    return embed


def create_music_embed(
        *,
        title: Optional[str] = None,
        description: str,
        footer: Optional[str] = None,
        image: Optional[str] = None
) -> discord.Embed:
    embed = discord.Embed(
        description=description,
        color=0xffa033
    )
    if title is not None:
        embed.title = title
    if footer is not None:
        embed.set_footer(text=footer)
    if image is not None:
        embed.set_thumbnail(url=image)
    return embed


def create_info_embed(
        *,
        title: Optional[str] = None,
        description: str,
) -> discord.Embed:
    embed = discord.Embed(
        description=description,
        color=0x3489eb
    )
    if title is not None:
        embed.title = title
    return embed


def create_queue_embed(ctx, page: Optional[int] = None) -> discord.Embed:
    voice = ctx.voice_client
    if voice.is_paused():
        paused = True
    else:
        paused = False
    tracks_info = tracks_utils.get_tracks(ctx.guild.id)
    if tracks_info is None:
        raise EmptyQueue
    track_list, now_playing = tracks_info.tracks, tracks_info.now_playing

    page, pages = tracks_utils.get_pages(ctx.guild.id, page)

    loop_settings = functions.get_guild_smf(ctx.guild.id, "loop_queue")

    if page == 1:
        page_index = 0
    else:
        page_index = (page - 1) * 10

    tracks = []
    for i, track in enumerate(track_list[page_index::]):
        if i == 10:
            break

        hours = track.duration // 3600
        minutes = (track.duration % 3600) // 60
        seconds = (track.duration % 3600) % 60
        dur = f""
        if hours != 0:
            dur += f"{hours}:"
        dur += f"{minutes:02d}:{seconds:02d}"
        track_index = i + page_index
        tracks.append(
            f"**{track_index + 1}. {track.name}** {dur}"
        )
        if track_index == now_playing:
            if paused:
                tracks[-1] += "\n↑ paused ↑"
            else:
                tracks[-1] += "\n↑ now playing ↑"

    if loop_settings:
        loop_str = "Queue loop is enabled"
    else:
        loop_str = "Queue loop is disabled"

    if (len(track_list)) > 10:
        pages = f"Page: {page} / {pages} | {loop_str}"
    else:
        pages = f"{loop_str}"

    embed = create_music_embed(
        description="\n\n".join(tracks),
        image="https://avatanplus.ru/files/resources/original/567059bd72e8a151a6de8c1f.png",
        footer=pages
    )
    return embed
