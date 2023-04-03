import asyncio

from discord import Guild

from bot.bot import client


@client.event
async def on_end_play(guild: Guild):

    def check(g: Guild):
        return g.id == guild.id
    try:
        await client.wait_for("start_play", check=check, timeout=60)
    except asyncio.TimeoutError:
        if guild.voice_client is not None:
            await guild.voice_client.disconnect(force=True)
