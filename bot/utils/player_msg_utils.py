import datetime
from typing import Optional

import discord
from discord_slash import SlashContext

from bot import functions, vk_parsing
from bot.utils import embed_utils


def get_loop_str_min(guild: discord.Guild) -> str:
    """
    Loop settings in string format for embed footer
    """
    loop_settings = functions.get_guild_data(guild, "loop_queue")
    return f"Зацикливание **{'вкл' if loop_settings else 'выкл'}**"


def get_duration(duration: int) -> str:
    date = datetime.datetime.fromordinal(1) + datetime.timedelta(seconds=duration)
    duration_str = date.strftime("%M:%S")
    if date.hour != 0:
        duration_str = date.strftime("%H:") + duration_str
    return duration_str


async def get_tracks_or_playlists_by_name(
        ctx: SlashContext,
        name: str, count: int = 25,
        is_tracks: bool = True
) -> Optional[list[dict]]:
    """
    шлем ошибку или возвращаем трек(и)
    """
    if name == "":
        embed = embed_utils.create_error_embed(
            message="Пустой запрос не может быть обработан"
        )
        await ctx.send(embed=embed, hidden=True)
        return
    try:
        if is_tracks:
            result = await vk_parsing.find_tracks_by_name(requester=ctx.author.id, name=name, count=count)
        else:
            result = await vk_parsing.find_playlists_by_name(requester=ctx.author.id, playlist_name=name, count=count)
    except Exception as err:
        print(f"error: {err}")
        embed = embed_utils.create_error_embed(
            message=f"Неизвестная ошибка во время обработки запроса **({name})**"
        )
        await ctx.send(embed=embed, hidden=True)
        return

    if result is None:
        embed = embed_utils.create_error_embed(
            message=f"Не найдено {'треков' if is_tracks else 'плейлистов'} по вашему запросу: **{name}**"
        )
        await ctx.send(embed=embed, hidden=True)
        return

    return result
