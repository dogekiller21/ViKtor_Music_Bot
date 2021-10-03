from typing import Optional

import discord

from ..cogs.constants import CustomColors


def create_error_embed(message: str, image: Optional[str] = None) -> discord.Embed:
    embed = discord.Embed(description=message, color=CustomColors.ERROR_COLOR)
    if image is not None:
        embed.set_thumbnail(url=image)
    return embed


def create_music_embed(
    *,
    title: Optional[str] = None,
    description: str,
    footer: Optional[str] = None,
    image: Optional[str] = None,
) -> discord.Embed:
    embed = discord.Embed(description=description, color=CustomColors.MUSIC_COLOR)
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
    embed = discord.Embed(description=description, color=CustomColors.INFO_COLOR)
    if title is not None:
        embed.title = title
    return embed
