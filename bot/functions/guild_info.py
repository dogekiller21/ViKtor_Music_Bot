from typing import Union

from discord import Guild

from bot import functions
from bot.utils.file_utils import ConfigFile


def get_guild_data(guild: Guild, what_to_search: str) -> Union[bool, str, None]:
    s_guild_id = str(guild.id)
    guilds_data = ConfigFile.get()["data"]["guilds"]

    if guilds_data.get(s_guild_id) is None:
        guild = functions.save_new_guild(
            guild_id=guild.id,
            owner_id=guild.owner_id,
        )
    else:
        guild = guilds_data[s_guild_id]

    return guild[what_to_search]
