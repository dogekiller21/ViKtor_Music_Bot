from typing import Optional

import discord
from discord.embeds import EmptyEmbed

from ..cogs.constants import CustomColors


class MusicEmbed(discord.Embed):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, color=CustomColors.MUSIC_COLOR)


def create_error_embed(
        *,
        title: Optional[str] = None,
        message: str
) -> discord.Embed:
    embed = discord.Embed(description=message, color=CustomColors.ERROR_COLOR)
    if title is not None:
        embed.title = title
    return embed


def create_music_embed(
        *,
        title: Optional[str] = None,
        description: Optional[str] = EmptyEmbed,
        footer: Optional[str] = None,
        footer_img: Optional[str] = EmptyEmbed,
        image: Optional[str] = None,
) -> discord.Embed:
    embed = discord.Embed(description=description, color=CustomColors.MUSIC_COLOR)
    if title is not None:
        embed.title = title
    if footer is not None:
        embed.set_footer(text=footer, icon_url=footer_img)
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
