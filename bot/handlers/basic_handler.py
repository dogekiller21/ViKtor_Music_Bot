import logging

from discord import Guild

from bot.bot import client
from bot.utils import check_guild


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    logging.info(f"We have logged in as {client.user}")


@client.event
async def on_guild_join(guild: Guild):
    await check_guild(guild=guild)
