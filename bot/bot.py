import json

import discord

from . import functions
from .config import TokenConfig, PathConfig
from discord.ext import commands

import os

DEFAULT_PREFIX = "-"


def get_prefix(_, message: discord.Message):
    with open(PathConfig.PREFIXES, "r") as file:
        try:
            return json.load(file)[str(message.guild.id)]
        except KeyError:
            return DEFAULT_PREFIX


intents = discord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix=get_prefix, intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    first_text_channel = guild.text_channels[0].id
    functions.save_new_guild(
        guild_id=guild_id, owner_id=owner_id, welcome_channel=first_text_channel
    )


def run():
    cogs_path = "bot{delimiter}cogs"

    client.remove_command("help")
    for filename in os.listdir(cogs_path.format(delimiter="/")):
        if filename == "__init__.py":
            continue
        if filename.endswith(".py"):
            client.load_extension(f"{cogs_path.format(delimiter='.')}.{filename[:-3]}")

    client.run(TokenConfig.DC_TOKEN)
