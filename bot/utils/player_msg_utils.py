import datetime
from typing import Sequence

import discord

from bot import functions


def get_loop_str_min(guild: discord.Guild) -> str:
    """
    Loop settings in string format for embed footer
    """
    loop_settings = functions.get_guild_data(guild, "loop_queue")
    cliche = "Зацикливание **{}**"
    if loop_settings:
        return cliche.format("вкл")
    return cliche.format("выкл")


def get_duration(duration: int) -> str:
    date = datetime.datetime.fromordinal(1) + datetime.timedelta(seconds=duration)
    duration_str = date.strftime("%M:%S")
    if date.hour != 0:
        duration_str = date.strftime("%H:") + duration_str
    return duration_str


async def add_reactions(emojis: Sequence[str], message: discord.Message) -> None:
    for emoji in emojis:
        try:
            await message.add_reaction(emoji)
        except discord.NotFound:
            return
