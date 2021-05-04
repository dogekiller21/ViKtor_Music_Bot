import json
from typing import Optional


def get_info():
    with open("config.json", "r", encoding="utf-8") as file:
        return json.load(file)


def save_info(data):
    with open("config.json", "w", encoding="utf-8") as file:
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


def add_new_admin(guild_id: int, user_id: int):
    all_data = get_info()
    guilds_info = all_data["data"]["guilds"]

    if user_id not in guilds_info[str(guild_id)]['admins']:
        guilds_info[str(guild_id)]['admins'].append(user_id)

        save_info(all_data)


def demote_admin(guild_id: int, user_id: int):
    all_data = get_info()
    guilds_info = all_data["data"]["guilds"]

    if user_id in guilds_info[str(guild_id)]['admins']:
        guilds_info[str(guild_id)]['admins'].remove(user_id)

        save_info(all_data)


def save_new_guild(
        guild_id: int,
        owner_id: int,
        welcome_channel: int,
        welcome_role: Optional[int] = None
):
    all_data = get_info()
    guilds_info = all_data["data"]["guilds"]

    if not guilds_info.get(str(guild_id)):
        guilds_info[str(guild_id)] = {
            'owner_id': owner_id,
            'welcome_channel_id': welcome_channel,
            'welcome_role_id': welcome_role,
            'admins': [owner_id]
        }
