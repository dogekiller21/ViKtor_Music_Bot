import discord

from constants import CustomColors


class Embeds:
    @staticmethod
    def music_embed(title: str = "", description: str = "", url: str = ""):
        return discord.Embed(color=CustomColors.MUSIC_COLOR, title=title, description=description,
                             url=url)

    @staticmethod
    def info_embed(title: str = "", description: str = ""):
        return discord.Embed(color=CustomColors.INFO_COLOR, title=title, description=description)

    @staticmethod
    def error_embed(title: str = "", description: str = ""):
        return discord.Embed(color=CustomColors.ERROR_COLOR, title=title, description=description)
