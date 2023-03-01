from discord import ApplicationCommandError


class IncorrectPlaylistUrlException(ApplicationCommandError):
    ...


class NoTracksParsedException(ApplicationCommandError):
    ...
