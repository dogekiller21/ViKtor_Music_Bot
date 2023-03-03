from discord import (
    Message,
    PCMVolumeTransformer,
    FFmpegPCMAudio,
    AudioSource,
    ApplicationContext,
    VoiceClient,
    VoiceProtocol,
)

from bot.constants import FFMPEG_OPTIONS


async def delete_message(message: Message):
    try:
        await message.delete()
    except Exception as e:
        print(f"Error while deleting message in {message.guild.name}: {e}")
        return


def get_source(track_url: str, volume_level: float = 0.5) -> AudioSource:
    return PCMVolumeTransformer(
        original=FFmpegPCMAudio(track_url, **FFMPEG_OPTIONS), volume=volume_level
    )


async def join_author_voice(ctx: ApplicationContext) -> VoiceClient | VoiceProtocol:
    channel = ctx.user.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    return ctx.voice_client
