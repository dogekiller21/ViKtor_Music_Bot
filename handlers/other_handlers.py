import discord

from bot import client
import functions


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

    # clearing information about tracks
    functions.clear_info()


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    first_text_channel = guild.text_channels[0].id
    functions.save_new_guild(guild_id=guild_id, owner_id=owner_id, welcome_channel=first_text_channel)
    owner = client.get_user(owner_id)
    me = client.get_user(242678412983009281)
    message = discord.Embed(
        title=f'Я был приглашен на твой сервер {guild.name}',
        description='Я умею:\n'
                    '1) Приветствовать новых пользователей и выдавать им роли.\n'
                    'Чтобы настроить канал для приветствий: -welcome_channel <id> '
                    '(без id будет выбран канал, в котором было отправлено сообщение)\n'
                    'Чтобы настроить роль для новых пользователей: -welcome_role <role> '
                    '(без упоминания информация о текущих настройках)\n\n'
                    'Управлять этим могут только администраторы и создатель\n'
                    '-admin <user> - назначить администратора\n'
                    '-user <user> - забрать права администратора\n'
                    '\nЧтобы бот имел возможность выдавать роли, ему нужно выдать '
                    'роль с правом выдачи других ролей и переместить ее выше остальных\n'
                    'Рекомендуется выдать боту роль с правами администратора\n\n'
                    '2) Проигрывать музыку из ВК\n'
                    'Для проигрывания плейлиста или альбома: -play <link>\n'
                    'Добавить одиночный трек в очередь: -add <name>\n'
                    'Пропустить трек: -skip <кол-во> (по стандарту 1)\n'
                    'Предыдущий трек: -prev <кол-во> (по стандарту 1)\n'
                    'Приостановить: -pause\n'
                    'Запустить вновь: -play\n'
                    'Прекратить прослушивание: -stop\n'
                    'Заставить бота выйти из канала: -leave',
        color=0x0a7cff
    )
    message.set_footer(text=me.name, icon_url=me.avatar_url)
    await owner.send(embed=message)


@client.event
async def on_member_join(member):
    channel = functions.get_guild_smf(member.guild.id, "welcome_channel_id")
    role = functions.get_guild_smf(member.guild.id, "welcome_role_id")
    msg_channel = client.get_channel(channel)
    if role:
        user_role = discord.utils.get(member.guild.roles, id=role)
        try:
            await member.add_roles(user_role)
        except Exception as err:
            embed = functions.create_error_embed(
                message=f'Невозможно выдать роль {user_role.mention} участнику {member.mention}'
            )
            await msg_channel.send(embed=embed)
            print(err)
    message = discord.Embed(
        title='Новый пользователь!',
        description=f'Добро пожаловать, кожаный ублюдок {member.mention}',
        color=0x0a7cff
    )

    await msg_channel.send(embed=message)
