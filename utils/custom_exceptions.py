from discord.ext.commands import CommandError


class NoTracksFound(Exception):
    pass


class EmptyQueue(Exception):
    pass


class NoVoiceClient(CommandError):
    pass


class IncorrectVoiceChannel(CommandError):
    pass


class ToManyPlaylists(Exception):
    pass
