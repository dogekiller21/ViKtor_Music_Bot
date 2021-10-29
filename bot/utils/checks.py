async def check_self_voice(ctx) -> bool:
    voice = ctx.voice_client
    return voice is not None and (voice.is_playing() or voice.is_paused())


async def check_user_voice(ctx) -> bool:
    return ctx.author.voice is not None
