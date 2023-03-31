from dotenv import load_dotenv
import os

load_dotenv()


class TokenConfig:
    DC_TOKEN = os.getenv("DC_TOKEN")
    VK_TOKEN = os.getenv("VK_TOKEN")


class DBConfig:
    HOST = os.getenv("POSTGRES_HOST")
    PORT = os.getenv("POSTGRES_PORT")
    USER = os.getenv("POSTGRES_USER")
    PASSWORD = os.getenv("POSTGRES_PASSWORD")
    DB_NAME = os.getenv("POSTGRES_DB")
