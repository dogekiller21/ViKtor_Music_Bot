import asyncio
import logging
from typing import Optional

from discord import (
    Message,
    PCMVolumeTransformer,
    FFmpegPCMAudio,
    AudioSource,
    ApplicationContext,
    VoiceClient,
    VoiceProtocol,
    Guild,
    HTTPException,
)

from bot.constants import FFMPEG_OPTIONS
from db.models import Guild as DBGuild, Settings


logger = logging.getLogger(__name__)


async def delete_message(message: Message):
    try:
        await message.delete()
    except HTTPException as e:
        logger.info(
            f"(Retry in 2s) HTTP Error while deleting message ({message}): {e}"
        )
        await asyncio.sleep(2)
        await delete_message(message=message)
    except Exception as e:
        logger.info(f"Error while deleting message ({message}): {e}")


def get_source(track_url: str, volume_level: float = 0.5) -> AudioSource:
    return PCMVolumeTransformer(
        original=FFmpegPCMAudio(track_url, **FFMPEG_OPTIONS), volume=volume_level
    )


async def join_author_voice(ctx: ApplicationContext):
    channel = ctx.user.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        logger.info(f"Connecting to voice in ")
        await channel.connect()
        logger.info(f"Connected")


async def check_guild(guild: Guild):
    guild, is_created = await DBGuild.get_or_create(
        discord_id=guild.id,
        defaults={
            "name": guild.name,
        },
    )
    if is_created:
        await Settings.create(guild=guild)
        logging.info(f"New guild created: {guild.name} with id {guild.id}")
