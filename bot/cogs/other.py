import discord
from discord.ext import commands
from discord.ext.commands import CommandError

from bot.utils import embed_utils
from .constants import GREEN_COLOR, TURQUOISE_COLOR, BROWN_COLOR


class Other(commands.Cog):
    """Дополнительные команды"""

    def __init__(self, client):
        self.client = client
        self.normal_color = GREEN_COLOR
        self.error_color = BROWN_COLOR
        self.bug_color = TURQUOISE_COLOR

    @commands.command(name="help")
    async def help_command(self, ctx, *data):
        """Вызывает эту команду"""
        embed = embed_utils.create_info_embed(
            description="В разработке"
        )
        await ctx.send(embed=embed)

        if not data:
            embed = discord.Embed(
                title="Команды и модули",
                description=f"Используйте /help <модуль>, чтобы получить подробную информацию\n",
                color=self.normal_color,
            )

            cogs_desc = ""
            for cog in self.client.cogs:
                passed = 0
                _cog = self.client.get_cog(cog)
                for command in _cog.get_commands():
                    try:
                        await command.can_run(ctx)
                        passed += 1
                    except CommandError:
                        continue
                if passed != 0:
                    cogs_desc += f"`{cog}` {self.client.cogs[cog].__doc__}\n"

            embed.add_field(name="Модули", value=cogs_desc, inline=False)

            commands_desc = ""
            for command in self.client.walk_commands():
                if not command.cog_name and not command.hidden:
                    commands_desc += f"{command.name} - {command.help}\n"

            if commands_desc:
                embed.add_field(
                    name="Не относящиеся к модулю", value=commands_desc, inline=False
                )

        elif len(data) == 1:
            for cog in self.client.cogs:
                if cog.lower() != data[0].lower():
                    continue

                embed = discord.Embed(
                    title=f"Команды в модуле {cog}", color=self.normal_color
                )

                for command in self.client.get_cog(cog).get_commands():
                    if command.hidden:
                        continue
                    try:
                        await command.can_run(ctx)
                        embed.add_field(
                            name=f"`/{command.name}`",
                            value=command.help,
                            inline=False,
                        )
                    except CommandError:
                        continue
                if not embed.fields:
                    embed.add_field(
                        name=":(",
                        value="Нет команд, которые вы можете использовать",
                    )

                break

            else:
                embed = discord.Embed(
                    title="Что это?",
                    description=f"Никогда не слышал о модуле `{data[0]}`",
                    color=self.error_color,
                )
            embed.set_footer(
                text=ctx.author.display_name, icon_url=ctx.author.avatar_url
            )

        elif len(data) > 1:
            embed = discord.Embed(
                title="Многовато",
                description="Пожалуйста, вводите только один модуль за раз",
                color=self.error_color,
            )

        else:
            embed = discord.Embed(
                title="",
                description="Кажется, вы обнаружили баг.\n"
                "Пожалуйста, сообщите об этом мне dogekiller21#6067",
                color=self.bug_color,
            )

        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Other(client))
