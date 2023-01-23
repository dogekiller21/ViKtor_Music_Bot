from dotenv import load_dotenv
import os

load_dotenv()


class TokenConfig:
    DC_TOKEN = os.getenv("DC_TOKEN")
    VK_TOKEN = os.getenv("VK_TOKEN")
