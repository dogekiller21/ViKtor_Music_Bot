import traceback

from discord_slash import SlashContext, MenuContext
from discord_slash.error import CheckFailure

from bot.utils import message_utils

from ..bot import client


@client.listen(name="on_slash_command_error")
async def slash_error_handler(ctx: SlashContext, error: Exception):
    voice_client_needed = ["player", "pause", "resume", "stop", "shuffle", "prev", "next", "queue", "jump", "leave",
                           "delete"]
    member_voice_needed = ["play", "playlist"]
    if isinstance(error, CheckFailure):
        if ctx.name in voice_client_needed:
            await message_utils.send_error_message(
                ctx,
                description="Ничего не играет :(\nИспользуйте команду `/play`"
            )
            return
        if isinstance(ctx, MenuContext) or ctx.name in member_voice_needed:
            await message_utils.send_error_message(
                ctx,
                description="Вы должны быть подключены к голосовому каналу"
            )
            return
    traceback.print_exc()  # TODO сделать норм вывод tb
