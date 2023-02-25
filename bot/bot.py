import discord

from bot.constants import DEBUG_GUILDS

intents = discord.Intents.all()

client = discord.Bot(
    debug_guilds=DEBUG_GUILDS, intents=intents, auto_sync_commands=True
)
