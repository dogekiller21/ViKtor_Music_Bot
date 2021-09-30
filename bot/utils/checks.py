from bot.utils import embed_utils


async def check_self_voice(ctx) -> bool:
    voice = ctx.voice_client
    if voice is None or (not voice.is_playing() and not voice.is_paused()):
        embed = embed_utils.create_error_embed(
            "Ничего не играет :(\n"
            "Используйте команду `/play` для проигрывания"
        )
        await ctx.send(embed=embed, delete_after=5)
        return False
    return True


async def check_user_voice(ctx) -> bool:
    if ctx.author.voice is None:
        embed = embed_utils.create_error_embed(
            "Вы должны быть подключены к голосовому каналу"
        )
        await ctx.send(embed=embed, delete_after=5)
        return False
    return True
