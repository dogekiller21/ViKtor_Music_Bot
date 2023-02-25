from discord import DiscordException


class NotInitializedException(Exception):
    ...


class IncorrectPlaylistUrlException(DiscordException):
    ...
