from .. import functions
from ..bot import client


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    functions.save_new_guild(guild_id=guild_id, owner_id=owner_id)
