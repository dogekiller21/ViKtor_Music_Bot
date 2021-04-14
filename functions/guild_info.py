import json


def get_guild_info(guild_id: int):
    with open('config.json', 'r', encoding='utf-8') as file:
        guilds_data = json.load(file)['data']['guilds']
        guild = guilds_data[str(guild_id)]
        welcome_channel = guild['welcome_channel_id']
        welcome_role = guild['welcome_role_id']
        admins = guild['admins']
        owner_id = guild['owner_id']

    return welcome_channel, welcome_role, admins, owner_id
