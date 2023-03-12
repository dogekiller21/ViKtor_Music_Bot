import random

from discord import Bot, Message, ApplicationContext, Interaction, NotFound
from discord.ext.pages import Paginator

from bot.storage.embeds_utils import StorageEmbeds
from bot.ui.views import PlayerView
from bot.utils import delete_message
from vk_parsing.models import TrackInfo


class Queue:
    def __init__(self, guild_id: int, client: Bot, storage: "QueueStorage"):
        self.current_index = 0
        self.tracks: list[TrackInfo] = []
        self.guild_id = guild_id
        self.client = client
        self.player_message: Message | None = None
        self.queue_paginator: Paginator | None = None
        self.storage = storage

    def add_tracks(self, tracks: list[TrackInfo]) -> int:
        """
        Adds tracks to queue
        Return count of added tracks
        """
        self.tracks.extend(tracks)
        return len(tracks)

    def add_track(self, track: TrackInfo) -> None:
        self.tracks.append(track)

    def __len__(self):
        return len(self.tracks)

    def inc_index(self) -> int:
        self.current_index += 1
        if self.current_index >= len(self):
            self.current_index = 0
        return self.current_index

    def dec_index(self) -> int:
        self.current_index -= 2
        if self.current_index < -1:
            self.current_index = len(self) - 2
        return self.current_index

    def get_current_track(self) -> TrackInfo | None:
        if not self.tracks:
            return
        return self.tracks[self.current_index]

    def get_previous_track(self) -> TrackInfo | None:
        if not self.tracks:
            return
        previous_index = self.current_index - 1
        if previous_index >= 0:
            return self.tracks[previous_index]

    def get_next_track(self) -> TrackInfo | None:
        if not self.tracks:
            return
        next_index = self.current_index + 1
        if next_index < len(self):
            return self.tracks[next_index]

    async def send_player_message(self, ctx: ApplicationContext):
        embed = StorageEmbeds.get_player_embed(queue=self)
        if embed is None:
            print(f"Embed is none while sending player message")
            return
        if self.player_message is not None:
            await self.delete_player_message()
        interaction = await ctx.respond(
            embed=embed, view=PlayerView(queue=self, storage=self.storage)
        )
        if isinstance(interaction, Interaction):
            self.player_message = interaction.message
        else:
            self.player_message = interaction

    async def delete_player_message(self):
        if self.player_message is None:
            return
        await delete_message(self.player_message)

    async def update_player_message(self):
        if self.player_message is None:
            return
        embed = StorageEmbeds.get_player_embed(queue=self)
        if embed is None:
            await self.delete_player_message()
            self.player_message = None
            return
        try:
            await self.player_message.edit(embed=embed)
        except NotFound:
            self.player_message = None

    async def update_queue_message(self):
        if self.queue_paginator is None:
            return
        if not self.tracks:
            await self.delete_queue_message()
            self.queue_paginator = None
            return
        pages, current_page = StorageEmbeds.get_queue_pages_and_page(queue=self)
        try:
            self.queue_paginator.current_page = current_page
            # noinspection PyTypeChecker
            await self.queue_paginator.update(
                pages=pages,
                custom_buttons=self.queue_paginator.custom_buttons
            )
        except Exception as e:
            print(f"Exc while updating paginator: {e}")
            await self.delete_queue_message()

    async def update_messages(self):
        await self.update_player_message()
        await self.update_queue_message()

    async def delete_queue_message(self):
        if self.queue_paginator is None:
            return
        await delete_message(self.queue_paginator.message)

    async def send_queue_message(self, ctx: ApplicationContext):
        paginator = StorageEmbeds.get_queue_paginator(queue=self)
        if paginator is None:
            print(f"Paginator is none while sending queue message")
            return
        if self.queue_paginator is not None:
            await self.delete_queue_message()
        self.queue_paginator = paginator
        await paginator.respond(interaction=ctx.interaction)

    def shuffle_tracks(self):
        if len(self) == 1:
            return
        # TODO: сделать шафл последнего трека вместо этого
        if self.current_index >= len(self) - 2:
            sequence_to_shuffle = self.tracks[: self.current_index]
            start_index = 0
            end_index = self.current_index
        else:
            sequence_to_shuffle = self.tracks[self.current_index + 1 :]
            start_index = self.current_index + 1
            end_index = len(self) - 1
        random.shuffle(sequence_to_shuffle)
        self.tracks[start_index:end_index] = sequence_to_shuffle


class QueueStorage:
    def __init__(self, client: Bot):
        self._storage: dict[int, Queue] = {}
        self._client: Bot = client

    def get_queue(
        self, guild_id: int, create_if_not_exist: bool = True
    ) -> Queue | None:
        """
        Return queue for given guild
        Create new if there's none (if create_if_not_exist)
        """
        if guild_id not in self._storage:
            if not create_if_not_exist:
                return
            self._storage[guild_id] = Queue(
                guild_id=guild_id, client=self._client, storage=self
            )
        return self._storage.get(guild_id)

    async def del_queue(self, guild_id: int):
        """
        Deletes queue and player message for given guild
        """
        if (
            queue := self.get_queue(guild_id=guild_id, create_if_not_exist=False)
        ) is None:
            return
        await queue.delete_player_message()
        await queue.delete_queue_message()
        del self._storage[guild_id]
