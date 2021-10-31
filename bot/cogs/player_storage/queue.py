from typing import Optional, Union

import discord

from .tracks import TracksStorage
from ...utils import player_msg_utils, embed_utils


class QueueMessagesStorage(dict):
    def __init__(self, tracks: TracksStorage):
        self: dict[int, dict[str, Union[int, discord.Message]]]
        super().__init__()
        self.tracks = tracks

    def get_starting_page(self, guild_id: int) -> int:
        now_playing = self.tracks[guild_id]["index"]
        _now_playing = now_playing + 1
        page = _now_playing // 10
        if (_now_playing % 10) != 0:
            page += 1
        return page - 1

    def get_pages_counter(
        self, guild_id: int
    ) -> int:
        tracks = self.tracks[guild_id]["tracks"]
        tracks_value = len(tracks)
        pages = tracks_value // 10
        if tracks_value % 10 != 0:
            pages += 1

        return pages

    def create_queue_embed(
        self, ctx, page: Optional[int] = None
    ) -> Optional[discord.Embed]:
        if ctx.guild.id not in self.tracks:
            return None
        voice = ctx.voice_client

        paused = voice.is_paused()

        tracks = self.tracks[ctx.guild.id]["tracks"]
        now_playing = self.tracks[ctx.guild.id]["index"]

        page_index = 0
        if page != 1:
            page_index = (page - 1) * 10

        tracks_to_str = []
        for i, track in enumerate(tracks[page_index: page_index + 10]):

            duration = player_msg_utils.get_duration(track["duration"])
            track_index = i + page_index
            tracks_to_str.append(f"**{track_index + 1}. {track['name']}** {duration}")
            if track_index != now_playing:
                continue

            if paused:
                tracks_to_str[-1] += "\n↑ приостановлен ↑"
            else:
                tracks_to_str[-1] += "\n↑ сейчас играет ↑"

        embed = embed_utils.create_music_embed(description="\n\n".join(tracks_to_str))

        return embed

    def check_queue_msg(self, guild_id: int) -> bool:
        return guild_id in self.tracks and guild_id in self

    async def queue_message_update(self, ctx) -> None:
        """
        Update queue and player messages
        """
        if not self.check_queue_msg(ctx.guild.id):
            return
        await self[ctx.guild.id].update()
