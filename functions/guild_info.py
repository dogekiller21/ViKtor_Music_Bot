import json


# def get_guild_admins(guild_id: int):
#     with open('config.json', 'r', encoding='utf-8') as file:
#         guilds_data = json.load(file)['data']['guilds']
#         guild = guilds_data[str(guild_id)]
#         return guild["admins"]
#
#
# def get_guild_welcome_channel(guild_id: int):
#     with open('config.json', 'r', encoding='utf-8') as file:
#         guilds_data = json.load(file)['data']['guilds']
#         guild = guilds_data[str(guild_id)]
#         return guild["welcome_channel_id"]
#
#
# def get_guild_welcome_role(guild_id: int):
#     with open('config.json', 'r', encoding='utf-8') as file:
#         guilds_data = json.load(file)['data']['guilds']
#         guild = guilds_data[str(guild_id)]
#         return guild["welcome_role_id"]
#
#
# def get_guild_owner_id(guild_id: int):
#     with open('config.json', 'r', encoding='utf-8') as file:
#         guilds_data = json.load(file)['data']['guilds']
#         guild = guilds_data[str(guild_id)]
#         return guild["owner_id"]


def get_guild_smf(guild_id: int, what_to_search: str):
    with open('config.json', 'r', encoding='utf-8') as file:
        guilds_data = json.load(file)['data']['guilds']
        guild = guilds_data[str(guild_id)]
        return guild[what_to_search]
