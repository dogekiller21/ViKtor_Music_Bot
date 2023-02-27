from discord import Bot, Message, ApplicationContext, Interaction, NotFound

from bot.storage.embeds_utils import StorageEmbeds
from bot.utils import delete_message
from vk_parsing.models import TrackInfo


class Queue:
    def __init__(self, guild_id: int, client: Bot):
        self.current_index = 0
        self.tracks: list[TrackInfo] = []
        self.guild_id = guild_id
        self.client = client
        self.player_message: Message | None = None

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
        if self.current_index >= len(self.tracks):
            self.current_index = 0
        return self.current_index

    def get_current_track(self) -> TrackInfo | None:
        if not self.tracks:
            return
        return self.tracks[self.current_index]

    async def send_player_message(self, ctx: ApplicationContext):
        embed = StorageEmbeds.get_player_message(queue=self)
        if embed is None:
            print(f"Embed is none while sending player message")
            return
        if self.player_message is not None:
            await self.update_message()
            return
        interaction = await ctx.respond(embed=embed)
        if isinstance(interaction, Interaction):
            self.player_message = interaction.message
        else:
            self.player_message = interaction

    async def delete_player_message(self):
        await delete_message(self.player_message)

    async def update_message(self):
        if self.player_message is None:
            return
        embed = StorageEmbeds.get_player_message(queue=self)
        if embed is None:
            await self.delete_player_message()
            self.player_message = None
        try:
            await self.player_message.edit(embed=embed)
        except NotFound:
            self.player_message = None


class QueueStorage:
    def __init__(self, client: Bot):
        self._storage = {}
        self._client = client

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
            self._storage[guild_id] = Queue(guild_id=guild_id, client=self._client)
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
        del self._storage[guild_id]
