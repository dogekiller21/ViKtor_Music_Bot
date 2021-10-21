from typing import Union

import discord


class TracksStorage(dict):
    def __init__(self):
        super().__init__()
        self: dict[int, dict[str, Union[int, discord.Message]]]
