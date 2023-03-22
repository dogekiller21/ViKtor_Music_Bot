from discord import DiscordException


class UserVoiceException(DiscordException):
    ...


class JoinVoiceTimeOut(DiscordException):
    ...
