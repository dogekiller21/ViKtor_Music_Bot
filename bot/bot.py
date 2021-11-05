import discord
from discord_slash import SlashCommand

from bot.storage.player_storage import BotStorage
from .config import TokenConfig
from discord.ext import commands

import os


intents = discord.Intents.all()
client = commands.Bot(
    command_prefix="", intents=intents, self_bot=True, help_command=None
)
slash = SlashCommand(client, sync_commands=True, delete_from_unused_guilds=True)
bot_storage = BotStorage(client)


def run():
    from bot.events import client

    cogs_path = "bot{delimiter}cogs"

    for filename in os.listdir(cogs_path.format(delimiter="/")):
        if filename in ["__init__.py", "constants.py"]:
            continue
        if filename.endswith(".py"):
            client.load_extension(f"{cogs_path.format(delimiter='.')}.{filename[:-3]}")

    client.run(TokenConfig.DC_TOKEN)
