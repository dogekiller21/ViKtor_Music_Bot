import discord
from discord_slash import SlashCommand

from . import functions
from .config import TokenConfig
from discord.ext import commands

import os


intents = discord.Intents.all()
client = commands.Bot(command_prefix="", intents=intents, self_bot=True, help_command=False)
slash = SlashCommand(client, sync_commands=True, delete_from_unused_guilds=True)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    functions.save_new_guild(
        guild_id=guild_id, owner_id=owner_id
    )


def run():
    cogs_path = "bot{delimiter}cogs"

    for filename in os.listdir(cogs_path.format(delimiter="/")):
        if filename in ["__init__.py", "constants.py"]:
            continue
        if filename.endswith(".py"):
            client.load_extension(f"{cogs_path.format(delimiter='.')}.{filename[:-3]}")

    client.run(TokenConfig.DC_TOKEN)
