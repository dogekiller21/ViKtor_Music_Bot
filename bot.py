import discord

import functions
from cfg import DC_TOKEN
from discord.ext import commands

import os

prefix = '-'
intents = discord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix=prefix, intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    first_text_channel = guild.text_channels[0].id
    functions.save_new_guild(guild_id=guild_id, owner_id=owner_id, welcome_channel=first_text_channel)
    owner = client.get_user(owner_id)
    me = client.get_user(242678412983009281)  # delete this before using
    message = discord.Embed(
        title=f'Я был приглашен на твой сервер {guild.name}',
        description='Бот(я) умеет:\n'
                    '1) Приветствовать новых пользователей и выдавать им роли.\n'
                    'Чтобы настроить канал для приветствий: -welcome_channel <id> '
                    '(без id будет выбран канал, в котором было отправлено сообщение)\n'
                    'Чтобы настроить роль для новых пользователей: -welcome_role <role> '
                    '(без упоминания информация о текущих настройках)\n\n'
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
                    'Чтобы просмотреть эту информацию еще раз, напишите -help',
        color=0x0a7cff
    )
    message.set_footer(text=me.name, icon_url=me.avatar_url)  # delete this too
    await owner.send(embed=message)

if __name__ == '__main__':
    client.remove_command("help")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            client.load_extension(f"cogs.{filename[:-3]}")

    client.run(DC_TOKEN)
