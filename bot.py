import json

import discord

import functions
from cfg import DC_TOKEN
from discord.ext import commands

import os

DEFAULT_PREFIX = "-"


def get_prefix(bot: discord.Client, message: discord.Message):
    with open("prefixes.json", "r") as file:
        try:
            return json.load(file)[str(message.guild.id)]
        except KeyError:
            return DEFAULT_PREFIX


intents = discord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix=get_prefix, intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_guild_join(guild):
    guild_id = guild.id
    owner_id = guild.owner_id
    first_text_channel = guild.text_channels[0].id
    functions.save_new_guild(guild_id=guild_id, owner_id=owner_id, welcome_channel=first_text_channel)


if __name__ == '__main__':
    client.remove_command("help")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            client.load_extension(f"cogs.{filename[:-3]}")

    client.run(DC_TOKEN)
