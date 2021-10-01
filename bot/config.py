import os

from dotenv import load_dotenv


load_dotenv()


class TokenConfig:
    DC_TOKEN = os.getenv("DC_TOKEN")
    VK_ME_TOKEN = os.getenv("VK_ME_TOKEN")


class PathConfig:
    PLAYLISTS = "bot/playlists.json"
    CONFIG = "bot/config.json"
