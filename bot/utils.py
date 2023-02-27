from discord import Message, PCMVolumeTransformer, FFmpegPCMAudio, AudioSource

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
