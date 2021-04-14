import discord
from cfg import DC_TOKEN
from discord.ext import commands

prefix = '-'
intents = discord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix=prefix, intents=intents)

if __name__ == '__main__':
    import handlers

    handlers.client.run(DC_TOKEN)
