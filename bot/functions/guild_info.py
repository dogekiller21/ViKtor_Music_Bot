import json

from discord import Guild

from bot import functions
from bot.config import PathConfig


def get_guild_smf(guild: Guild, what_to_search: str):
    s_guild_id = str(guild.id)
    with open(PathConfig.CONFIG, "r", encoding="utf-8") as file:
        guilds_data = json.loads(file.read())["data"]["guilds"]
        if guilds_data.get(s_guild_id) is None:
            guild = functions.save_new_guild(
                guild_id=guild.id, owner_id=guild.owner_id, welcome_channel=guild.text_channels[0].id
            )
        else:
            guild = guilds_data[s_guild_id]
    return guild[what_to_search]
