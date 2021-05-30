import json
from typing import Optional

import discord
from discord.ext import commands

from utils import embed_utils

from bot import DEFAULT_PREFIX


class Other(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(name="help", pass_context=True)
    async def help_command(self, ctx: commands.Context):
        embed = embed_utils.create_info_embed(
            title="Мои команды",
            description='Бот(я) умеет:\n'
                        '1) Приветствовать новых пользователей и выдавать им роли.\n'
                        'Чтобы настроить канал для приветствий: -welcome_channel <id> '
                        '(без id будет выбран канал, в котором было отправлено сообщение)\n'
                        'Чтобы настроить роль для новых пользователей: -welcome_role <role> '
                        '(без упоминания информация о текущих настройках)\n'
                        'Данные команды можно использовать только с правами администратора\n\n'
                        'Чтобы бот имел возможность выдавать роли, ему нужно выдать '
                        'роль с правом выдачи других ролей и переместить ее выше остальных\n'
                        'Рекомендуется выдать боту роль с правами администратора\n\n'
                        '2) Проигрывать музыку из ВК\n'
                        'Для проигрывания плейлиста или трека: -play <link|name>\n'
                        'Добавить одиночный трек в очередь: -add <name>\n'
                        'Пропустить трек: -skip <кол-во> (по стандарту 1)\n'
                        'Предыдущий трек: -prev <кол-во> (по стандарту 1)\n'
                        'Приостановить: -pause\n'
                        'Запустить вновь: -play\n'
                        'Прекратить прослушивание: -stop\n'
                        'Заставить бота выйти из канала: -leave\n'
                        'Изменить настройку лупа: -loop\n'
                        'Перемешать треки: -shuffle\n\n'
                        'Изменить префикс: -prefix <префикс>\n'
                        'Сбросить на стандартный: {префикс}prefix'
        )

        await ctx.send(embed=embed)

    def _edit_prefix(self, guild_id, prefix):
        with open("prefixes.json", "r") as file:
            data = json.load(file)
        if prefix is None:
            try:
                del data[str(guild_id)]
            except KeyError:
                return
        else:
            data[str(guild_id)] = prefix

        with open("prefixes.json", "w") as file:
            json.dump(data, file)

    @commands.command(name="prefix")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def prefix_command(self, ctx: commands.Context, prefix: Optional[str] = None):
        if prefix is not None and not prefix.endswith((".", "!", "@", "_", "*", "$", "%", "#", "^", "&", "/")):
            prefix += "."
        self._edit_prefix(ctx.guild.id, prefix)
        if prefix is None:
            prefix = DEFAULT_PREFIX
        embed = embed_utils.create_info_embed(
            title="Префикс изменен",
            description=f"Теперь команды в вашей гильдии должны начинаться с **{prefix}**\n"
                        f"Пример: **{prefix}play**"
        )
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Other(client))
