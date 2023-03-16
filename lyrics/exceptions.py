from discord import DiscordException


class SongNotFoundException(DiscordException):
    ...


class LyricsParsingError(DiscordException):
    ...
