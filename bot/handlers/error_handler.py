import sys
import traceback

from discord import ApplicationContext, DiscordException, CheckFailure

from bot.bot import client
from vk_parsing.exceptions import NoTracksParsedException, IncorrectPlaylistUrlException


@client.listen("on_application_command_error")
async def command_error_handler(ctx: ApplicationContext, error: DiscordException):
    if isinstance(
        error, (CheckFailure, IncorrectPlaylistUrlException, NoTracksParsedException)
    ):
        pass
    else:
        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )
