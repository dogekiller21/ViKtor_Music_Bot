import logging

from bot.bot import client


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    logging.info(f'We have logged in as {client.user}')
