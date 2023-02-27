from discord import ApplicationContext


async def check_user_voice(ctx: ApplicationContext) -> bool:
    return ctx.user.voice is not None


async def check_self_voice(ctx: ApplicationContext) -> bool:
    return ctx.voice_client is not None
