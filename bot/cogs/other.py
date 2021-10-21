from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import CommandError
from discord_slash import cog_ext

from bot.utils import embed_utils
from .constants import CustomColors


class Other(commands.Cog):
    """Дополнительные команды"""

    def __init__(self, client):
        self.client = client
        self.normal_color = CustomColors.GREEN_COLOR
        self.error_color = CustomColors.BROWN_COLOR

    @cog_ext.cog_slash(
        name="help",
        description="Узнать все доступные команды",
        options=[{"name": "module_name", "description": "Имя модуля", "type": 3}],
    )
    async def help_command(self, ctx, module_name: Optional[str] = None):
        """Вызывает эту команду"""
        embed = embed_utils.create_info_embed(description="В разработке")
        await ctx.send(embed=embed)
        return
        if module_name is None:
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

        elif module_name is not None:
            for cog in self.client.cogs:
                if cog.lower() != module_name.lower():
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
                    description=f"Никогда не слышал о модуле `{module_name}`",
                    color=self.error_color,
                )
            embed.set_footer(
                text=ctx.author.display_name, icon_url=ctx.author.avatar_url
            )

        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Other(client))
