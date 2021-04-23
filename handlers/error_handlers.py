from bot import client

from discord.ext import commands

from handlers.command_handlers import (admin_command, user_command, welcome_role_command)


@admin_command.error
async def admin_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.channel.send('Упомяните пользователя, которому хотите выдать права администратора')


@user_command.error
async def user_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.channel.send('Упомяните пользователя, у которого хотите забрать права администратора')


@welcome_role_command.error
async def welcome_role_command_error(ctx, error):
    if isinstance(error, commands.RoleNotFound):
        ctx.channel.send('Введите корректную роль')
