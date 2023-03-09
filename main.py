import logging
import os

import db
from config import TokenConfig

_log_format = "%(asctime)s:%(levelname)s:%(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=_log_format)

if __name__ == "__main__":
    from bot.handlers import client

    for filename in os.listdir("bot/cogs"):
        if filename.endswith(".py"):
            client.load_extension(f"bot.cogs.{filename[:-3]}")
    client.loop.run_until_complete(db.init())
    client.run(TokenConfig.DC_TOKEN)
