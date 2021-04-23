import discord

from bot import client
import functions


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    first_text_channel = guild.text_channels[0].id
    functions.json_write(guild_id=guild_id, owner_id=owner_id, welcome_channel=first_text_channel)
    owner = client.get_user(owner_id)
    me = client.get_user(242678412983009281)
    message = discord.Embed(
        title=f'Я был приглашен на твой сервер {guild.name}',
        description='Мои возможности:\n'
                    '-welcome_channel idКанала (без id будет выбран текущий канал) '
                    '- настроить канал для приветствий\n'
                    '-welcome_role @role_mention (без упоминания информация о текущих настройках) '
                    '- настроить роль для новых пользователей\n\n'
                    'Предыдущие команды может писать либо создатель сервера, '
                    'либо администраторы, назначенные создателем\n'
                    '-admin @user_mention - назначить администратора\n'
                    '-user @user_mention - забрать права администратора\n\n'
                    '-roles - список ролей пользователя\n'
                    '\nЧтобы бот имел возможность выдавать роли, ему нужно выдать '
                    'роль с правом выдачи других ролей и переместить ее выше остальных\n'
                    'Рекомендуется выдать боту роль с правами администратора',
        color=0x0a7cff
    )
    #message.set_footer(text=me.name, icon_url=me.avatar_url)
    await owner.send(embed=message)


@client.event
async def on_member_join(member):
    channel, role, _, _ = functions.get_guild_info(guild_id=member.guild.id)
    msg_channel = client.get_channel(channel)
    if role:
        user_role = discord.utils.get(member.guild.roles, id=role)
        try:
            await member.add_roles(user_role)
        except Exception as err:
            await msg_channel.send(f'Невозможно выдать роль {user_role.mention} участнику {member.mention}')
            print(err)
    message = discord.Embed(
        title='Новый пользователь!',
        description=f'Добро пожаловать, кожаный ублюдок {member.mention}',
        color=0x0a7cff
    )

    await msg_channel.send(embed=message)
