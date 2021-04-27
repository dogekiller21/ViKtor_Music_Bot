from typing import Optional

import discord


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
        title: str,
        description: str,
        image: Optional[str] = None
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=0xffa033
    )
    if image is not None:
        embed.set_thumbnail(url=image)
    return embed


def create_queue_embed(
        *,
        title: Optional[str] = None,
        description: str,
        pages: Optional[str] = None,
        image: Optional[str] = None
) -> discord.Embed:
    embed = discord.Embed(
        description=description,
        color=0xffa033
    )
    if title is not None:
        embed.title = title
    if pages is not None:
        embed.set_footer(text=pages)
    if image is not None:
        embed.set_thumbnail(url=image)
    return embed
