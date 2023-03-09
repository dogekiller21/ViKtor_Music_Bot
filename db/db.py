from db.models import Guild, Settings


async def get_guild(guild_id: int) -> Guild:
    return await Guild.get(discord_id=guild_id)


async def get_settings(guild_id: int) -> Settings:
    return await Settings.get(guild__discord_id=guild_id)


async def change_volume_option(guild_id: int, volume_level: int):
    settings = await get_settings(guild_id=guild_id)
    settings.volume_option = volume_level
    await settings.save(update_fields=["volume_option"])
