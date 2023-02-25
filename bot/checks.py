from discord import ApplicationContext


async def check_user_voice(ctx: ApplicationContext) -> bool:
    return ctx.user.voice is not None
