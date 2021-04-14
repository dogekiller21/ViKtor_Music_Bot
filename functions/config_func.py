import json
from typing import Optional


def json_write(guild_id: int,
               owner_id: Optional[int] = None,
               welcome_channel: Optional[int] = None,
               welcome_role: Optional[int] = None,
               new_admin_id: Optional[int] = None,
               admin_demotion_id: Optional[int] = None):
    with open('config.json', 'r', encoding='utf-8') as file:
        all_data = json.load(file)
        guilds_info = all_data['data']['guilds']

        if not guilds_info.get(str(guild_id)):
            guilds_info[str(guild_id)] = {
                'owner_id': owner_id,
                'welcome_channel_id': welcome_channel,
                'welcome_role_id': welcome_role,
                'admins': [owner_id]
               }
        if welcome_role:
            guilds_info[str(guild_id)]['welcome_role_id'] = welcome_role

        if welcome_channel:
            guilds_info[str(guild_id)]['welcome_channel_id'] = welcome_channel

        if new_admin_id:
            if new_admin_id not in guilds_info[str(guild_id)]['admins']:
                guilds_info[str(guild_id)]['admins'].append(new_admin_id)

        if admin_demotion_id:
            if admin_demotion_id in guilds_info[str(guild_id)]['admins']:
                guilds_info[str(guild_id)]['admins'].remove(admin_demotion_id)

    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
