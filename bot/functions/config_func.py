import json
from typing import Optional, Union

from bot.config import PathConfig


def get_info():
    with open(PathConfig.CONFIG, encoding="utf-8") as file:
        return json.load(file)


def save_info(data):
    with open(PathConfig.CONFIG, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def write_welcome_channel(guild_id: int, welcome_channel_id: int):
    all_data = get_info()
    guilds_info = all_data["data"]["guilds"]

    guilds_info[str(guild_id)]["welcome_channel_id"] = welcome_channel_id

    save_info(all_data)


def write_welcome_role(guild_id: int, welcome_role_id: int):
    all_data = get_info()
    guilds_info = all_data["data"]["guilds"]

    guilds_info[str(guild_id)]["welcome_role_id"] = welcome_role_id

    save_info(all_data)


def change_loop_option(guild_id: int, new_loop_option):
    all_data = get_info()

    all_data["data"]["guilds"][str(guild_id)]["loop_queue"] = new_loop_option

    save_info(all_data)


def save_new_guild(
    guild_id: int,
    owner_id: int,
    welcome_channel: int,
    welcome_role: Optional[int] = None,
) -> dict[str, Union[bool, int, None]]:
    all_data = get_info()
    guilds_info = all_data["data"]["guilds"]
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
        save_info(all_data)
    return guild_info
