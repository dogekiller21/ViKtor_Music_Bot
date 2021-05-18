from bot import client

from discord.ext import commands

from handlers.command_handlers import welcome_role_command

from discord.errors import ClientException


# @client.event
# async def on_command_error(_, error):
#     if isinstance(error, commands.CommandNotFound):
#         return
#     if isinstance(error, commands.CommandError):
#         if isinstance(error, commands.MemberNotFound):
#             return
#         if isinstance(error, commands.RoleNotFound):
#             return
#         print(f'Command error: "{error}"')
#
#     if isinstance(error, ClientException):
#         print(f'Client exception: "{error}"')
#     else:
#         print(error)


@welcome_role_command.error
async def welcome_role_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.RoleNotFound):
        await ctx.channel.send('Введите корректную роль')
