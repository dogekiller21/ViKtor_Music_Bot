import random
from enum import Enum
from typing import Optional, Union

import discord
from discord_slash.error import SlashCommandError
from discord_slash.model import SlashMessage

from bot.cogs.constants import DEFAULT_ICON_URL
from bot.pagination.pagination import EmbedPagination
from bot.utils import player_msg_utils, embed_utils, message_utils


class IncorrectDeleteIndex(SlashCommandError):
    pass


class QueueIsEmpty(SlashCommandError):
    pass


class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2


class Queue:
    def __init__(self, guild_id: int):
        self._guild_id = guild_id
        self._tracks: list[dict] = []
        self._repeat_mode = RepeatMode.NONE
        self.current_index = 0

        self.message: Optional[EmbedPagination] = None

    def __bool__(self):
        return bool(self._tracks)

    def __len__(self):
        return len(self._tracks)

    @property
    def tracks(self):
        return self._tracks

    @property
    def guild_id(self):
        return self._guild_id

    @property
    def repeat_mode(self):
        return self._repeat_mode

    def edit_repeat_mode(self):
        current_mode = self._repeat_mode.value
        current_mode += 1
        if current_mode > 2:
            current_mode = 0
        self._repeat_mode = RepeatMode(current_mode)
        return self._repeat_mode

    def add_tracks(self, tracks: Union[dict, list[dict]]):
        if isinstance(tracks, dict):
            self._tracks.append(tracks)
        else:
            self._tracks.extend(tracks)

    def shuffle_tracks(self):
        random.shuffle(self._tracks)
        self.current_index = 0

    def get_next_track(self, offset=1):
        if self._repeat_mode == RepeatMode.ONE:
            return self._tracks[self.current_index]
        self.current_index += offset
        if self.current_index >= len(self):
            if self._repeat_mode == RepeatMode.NONE:
                self._tracks.clear()
                return
            if self._repeat_mode == RepeatMode.ALL:
                self.current_index = 0

        return self._tracks[self.current_index]

    def get_prev_track(self, offset=1):
        if self._repeat_mode == RepeatMode.ONE:
            return self._tracks[self.current_index]
        self.current_index -= offset
        if self.current_index < 0:
            if self._repeat_mode == RepeatMode.NONE:
                return
            if self._repeat_mode == RepeatMode.ALL:
                self.current_index = len(self)

        return self._tracks[self.current_index]

    def delete_from_queue(self, index: int):
        if index < 1 or index > len(self):
            raise IncorrectDeleteIndex
        del self._tracks[index]

    def create_queue_embed(
        self, ctx, page: Optional[int] = None
    ) -> Optional[discord.Embed]:

        voice = ctx.voice_client
        paused = voice.is_paused()

        page_index = 0
        if page != 1:
            page_index = (page - 1) * 10

        tracks_to_str = []
        for i, track in enumerate(self._tracks[page_index: page_index + 10]):

            duration = player_msg_utils.get_duration(track["duration"])
            track_index = i + page_index
            tracks_to_str.append(f"**{track_index + 1}. {track['name']}** {duration}")
            if track_index != self.current_index:
                continue

            if paused:
                tracks_to_str[-1] += "\n↑ приостановлен ↑"
            else:
                tracks_to_str[-1] += "\n↑ сейчас играет ↑"

        embed = embed_utils.create_music_embed(description="\n\n".join(tracks_to_str))

        return embed

    def get_pages_counter(self) -> int:
        tracks_value = len(self)
        pages = tracks_value // 10
        if tracks_value % 10 != 0:
            pages += 1

        return pages

    def get_starting_page(self) -> int:
        now_playing = self.current_index
        _now_playing = now_playing + 1
        page = _now_playing // 10
        if (_now_playing % 10) != 0:
            page += 1
        return page - 1

    async def _pagination_func(self, index, ctx):
        pages = self.get_pages_counter()

        embed = self.create_queue_embed(ctx, index + 1)
        self.message.max_page = pages
        return embed

    async def send_message(self, ctx, page=None):
        if page is None:
            page = self.get_starting_page()
        pages = self.get_pages_counter()

        if page > pages:
            await message_utils.send_error_message(ctx, description="Нет такой страницы")
            return

        if self.message is not None:
            await self.message.delete(delay=2)

        pagination = EmbedPagination(target_callable=self._pagination_func, target_callable_kwargs={"ctx": ctx},
                                     start_page=page, max_page=pages, infinite=True, guild_id=ctx.guild.id, client=ctx.bot)
        self.message = pagination

        await pagination.send(ctx)

    async def message_update(self) -> None:
        if not self.message:
            return
        await self.message.update()


class PlayerStorage:
    def __init__(self, client: discord.Client, queues: dict[int, Queue]):
        self.client = client
        self.queues = queues
        self.messages: dict[int, SlashMessage] = dict()

    def _get_requester(self, track: dict):
        requester = track.get("requester")
        if requester is None:
            return
        user = self.client.get_user(requester)
        if user is not None:
            return {"text": user.display_name, "icon_url": user.avatar_url}
        return {
            "text": "Неизвестный пользователь",
            "icon_url": DEFAULT_ICON_URL,
        }

    def _get_repeat_mode_str(self, guild_id):
        queue = self.queues[guild_id]
        repeat_mode = queue.repeat_mode
        if repeat_mode.value == 0:
            return "выкл"
        if repeat_mode.value == 1:
            return "один трек"
        if repeat_mode.value == 2:
            return "вся очередь"

    def create_player_embed(self, ctx) -> Optional[discord.Embed]:
        if ctx.guild.id not in self.queues:
            return
        queue = self.queues[ctx.guild.id]
        length = len(queue)
        tracks = queue.tracks

        now_playing = queue.current_index
        prev_index, next_index = now_playing - 1, now_playing + 1

        embed = embed_utils.create_music_embed(
            title=f'Плеер в канале "{ctx.voice_client.channel.name}"',
            description=f"`Треков в очереди: {length}`\n"
            f"Зацикливание: {self._get_repeat_mode_str(ctx.guild.id)}",
        )
        requester = self._get_requester(tracks[now_playing])
        if requester is not None:
            embed.set_footer(**requester)
        if prev_index >= 0:
            duration = player_msg_utils.get_duration(tracks[prev_index]["duration"])
            embed.add_field(
                name="Предыдущий трек",
                value=f"**{prev_index + 1}. {tracks[prev_index]['name']}** {duration}\n",
                inline=False,
            )

        voice = ctx.voice_client
        title = "⟶ Приостановлен ⟵" if voice.is_paused() else "⟶ Сейчас играет ⟵"

        duration = player_msg_utils.get_duration(tracks[now_playing]["duration"])
        embed.add_field(
            name=title,
            value=f"**{now_playing + 1}. {tracks[now_playing]['name']}** {duration}",
            inline=False,
        )

        if next_index < len(tracks):
            duration = player_msg_utils.get_duration(tracks[next_index]["duration"])
            embed.add_field(
                name="Следующий трек",
                value=f"\n**{next_index + 1}. {tracks[next_index]['name']}** {duration}",
                inline=False,
            )

        embed.set_thumbnail(url=tracks[now_playing]["thumb"])
        return embed

    async def player_message_update(self, ctx) -> None:
        if ctx.guild.id not in self.messages:
            return

        embed = self.create_player_embed(ctx)
        if embed is None:
            return
        try:
            await self.messages[ctx.guild.id].edit(embed=embed)
        except discord.NotFound:
            del self.messages[ctx.guild.id]


class BotStorage:
    def __init__(self, client: discord.Client):
        self.client = client
        self.queues: dict[int, Queue] = dict()
        self.player_storage: PlayerStorage = PlayerStorage(client, self.queues)

    async def update_messages(self, ctx):
        await self.queues[ctx.guild.id].message_update()
        await self.player_storage.player_message_update(ctx=ctx)

    async def delete_messages(self, guild_id, delay: int = 2):
        """
        Delete queue and player messages for guild
        """
        queue = self.queues.get(guild_id)
        queue_message = queue.message if queue is not None else None

        player_message = self.player_storage.messages.get(guild_id)
        for messages_container, message in [
            (self.queues, queue_message),
            (self.player_storage.messages, player_message),
        ]:
            if message is None:
                continue
            del messages_container[guild_id]
            await message.delete(delay=delay)
