from discord import VoiceClient


async def join_channel(ctx) -> VoiceClient:
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    return ctx.voice_client
