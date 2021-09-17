import json
from typing import Optional, Union

from bot._types import JSON_DATA
from bot.config import PathConfig
from bot.utils.file_utils import ConfigFile, update_json


@update_json(PathConfig.CONFIG)
def write_welcome_channel(guild_id: int, welcome_channel_id: int, json_data: JSON_DATA):
    guilds_info = json_data["data"]["guilds"]
    guilds_info[str(guild_id)]["welcome_channel_id"] = welcome_channel_id


@update_json(PathConfig.CONFIG)
def write_welcome_role(guild_id: int, welcome_role_id: int, json_data: JSON_DATA):
    guilds_info = json_data["data"]["guilds"]
    guilds_info[str(guild_id)]["welcome_role_id"] = welcome_role_id


@update_json(PathConfig.CONFIG)
def change_loop_option(guild_id: int, new_loop_option, json_data: JSON_DATA):
    json_data["data"]["guilds"][str(guild_id)]["loop_queue"] = new_loop_option


@update_json(PathConfig.CONFIG)
def save_new_guild(
    guild_id: int,
    owner_id: int,
    welcome_channel: int,
    json_data: JSON_DATA,
    welcome_role: Optional[int] = None,
) -> dict[str, Union[bool, int, None]]:
    guilds_info = json_data["data"]["guilds"]
    guild_id = str(guild_id)
    guild_info = guilds_info.get(guild_id)

    if guild_info is None:
        guild_info = {
            "owner_id": owner_id,
            "welcome_channel_id": welcome_channel,
            "welcome_role_id": welcome_role,
            "loop_queue": False,
        }
        guilds_info[guild_id] = guild_info
    return guild_info
