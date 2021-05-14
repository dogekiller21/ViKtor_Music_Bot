import json


def get_guild_smf(guild_id: int, what_to_search: str):
    with open('config.json', 'r', encoding='utf-8') as file:
        guilds_data = json.load(file)['data']['guilds']
        guild = guilds_data[str(guild_id)]
        return guild[what_to_search]
