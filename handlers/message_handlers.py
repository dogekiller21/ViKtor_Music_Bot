from bot import client

import functions


@client.event
async def on_message(message):
    await client.process_commands(message)
    if message.author == client.user:
        return

    if message.content.startswith('hello'):
        await message.channel.send('Hello!')
