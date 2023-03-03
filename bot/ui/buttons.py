from discord import ButtonStyle, Interaction
from discord.ui import Button
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.storage import Queue, QueueStorage


class ShuffleButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji="🔀",
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:shuffle",
            row=0,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        self.queue.shuffle_tracks()
        await self.queue.update_message()
        # interaction.guild.voice_client.stop()
        await interaction.response.defer()


class PrevButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji="⏪",
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:prev",
            row=0,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        self.queue.dec_index()
        interaction.guild.voice_client.stop()
        await interaction.response.defer()


class SkipButton(Button):
    def __init__(self, guild_id: int):
        super().__init__(
            emoji="⏩",
            style=ButtonStyle.secondary,
            custom_id=f"{guild_id}:skip",
            row=0,
        )

    async def callback(self, interaction: Interaction):
        interaction.guild.voice_client.stop()
        await interaction.response.defer()


class PlayPauseButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji="⏸️",
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:play_pause",
            row=0,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        if interaction.guild.voice_client.is_playing():
            self.emoji = "▶️"
            interaction.guild.voice_client.pause()
        else:
            self.emoji = "⏸"
            interaction.guild.voice_client.resume()
        await interaction.message.edit(view=self.view)
        await self.queue.update_message()
        await interaction.response.defer()


class StopButton(Button):
    def __init__(self, storage: "QueueStorage", guild_id: int):
        super().__init__(
            emoji="⏹",
            style=ButtonStyle.secondary,
            custom_id=f"{guild_id}:stop",
            row=0,
        )
        self.storage = storage

    async def callback(self, interaction: Interaction):
        await self.storage.del_queue(guild_id=interaction.guild_id)
        interaction.guild.voice_client.stop()
        await interaction.response.defer()
