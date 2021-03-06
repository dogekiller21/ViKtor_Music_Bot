from typing import Union

from bot._types import JSON_DATA
from bot.utils.file_utils import update_json, ConfigFile


@update_json(ConfigFile)
def change_loop_option(guild_id: int, new_loop_option, json_data: JSON_DATA):
    json_data["data"]["guilds"][str(guild_id)]["loop_queue"] = new_loop_option


@update_json(ConfigFile)
def save_new_guild(
    guild_id: int,
    owner_id: int,
    json_data: JSON_DATA,
) -> dict[str, Union[bool, int, None]]:
    guilds_info = json_data["data"]["guilds"]
    guild_id = str(guild_id)
    guild_info = guilds_info.get(guild_id)

    if guild_info is None:
        guild_info = {
            "owner_id": owner_id,
            "loop_queue": False,
        }
        guilds_info[guild_id] = guild_info
    return guild_info
