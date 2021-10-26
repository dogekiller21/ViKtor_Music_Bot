import traceback

from discord_slash import SlashContext
from discord_slash.error import CheckFailure

from bot.utils import embed_utils

from ..bot import client


@client.listen(name="on_slash_command_error")
async def slash_error_handler(ctx: SlashContext, error: Exception):
    voice_client_needed = ["player", "pause", "resume", "stop", "shuffle", "prev", "next", "queue", "jump", "leave",
                           "delete"]
    member_voice_needed = ["play", "playlist"]
    if isinstance(error, CheckFailure):
        if ctx.name in voice_client_needed:
            embed = embed_utils.create_error_embed(
                message="Ничего не играет :(\nИспользуйте команду `/play` или `/search`"
            )
            await ctx.send(embed=embed)
            return
        if ctx.name in member_voice_needed:
            embed = embed_utils.create_error_embed(
                message="Вы должны быть подключены к голосовому каналу"
            )
            await ctx.send(embed=embed)
            return
    traceback.print_exc()
