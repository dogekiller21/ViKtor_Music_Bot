from discord import ApplicationCommandError


class IncorrectPlaylistUrlException(ApplicationCommandError):
    ...


class NoTracksParsedException(ApplicationCommandError):
    ...


class SingleTrackParsingApiError(ApplicationCommandError):
    ...


class PlaylistParsingApiError(ApplicationCommandError):
    ...
