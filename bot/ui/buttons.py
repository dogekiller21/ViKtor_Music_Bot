from discord import ButtonStyle, Interaction
from discord.ui import Button
from typing import TYPE_CHECKING

from bot.ui.config import PlayerEmojis
from db.db import get_settings, change_volume_option

if TYPE_CHECKING:
    from bot.storage import Queue, QueueStorage


class ShuffleButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji=PlayerEmojis.SHUFFLE_EMOJI,
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:shuffle",
            row=0,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        self.queue.shuffle_tracks()
        await self.queue.update_messages()
        await interaction.response.defer()


class PrevButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji=PlayerEmojis.PREV_EMOJI,
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
            emoji=PlayerEmojis.SKIP_EMOJI,
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
            emoji=PlayerEmojis.PAUSE_EMOJI,
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:play_pause",
            row=0,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        if interaction.guild.voice_client.is_playing():
            self.emoji = PlayerEmojis.PLAY_EMOJI
            interaction.guild.voice_client.pause()
        else:
            self.emoji = PlayerEmojis.PAUSE_EMOJI
            interaction.guild.voice_client.resume()
        await interaction.message.edit(view=self.view)
        await self.queue.update_messages()
        await interaction.response.defer()


class StopButton(Button):
    def __init__(self, storage: "QueueStorage", guild_id: int):
        super().__init__(
            emoji=PlayerEmojis.STOP_EMOJI,
            style=ButtonStyle.secondary,
            custom_id=f"{guild_id}:stop",
            row=0,
        )
        self.storage = storage

    async def callback(self, interaction: Interaction):
        await self.storage.del_queue(guild_id=interaction.guild_id)
        interaction.guild.voice_client.stop()
        await interaction.response.defer()


class VolUpButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji=PlayerEmojis.VOL_UP_EMOJI,
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:vol_up",
            row=1,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        current_volume_level = interaction.guild.voice_client.source.volume * 100
        current_volume_level += 10
        if current_volume_level > 100:
            current_volume_level = 100
        interaction.guild.voice_client.source.volume = current_volume_level / 100
        await change_volume_option(guild_id=interaction.guild_id, volume_level=current_volume_level)
        await self.queue.update_messages()
        await interaction.response.defer()


class VolDownButton(Button):
    def __init__(self, queue: "Queue"):
        super().__init__(
            emoji=PlayerEmojis.VOL_DOWN_EMOJI,
            style=ButtonStyle.secondary,
            custom_id=f"{queue.guild_id}:vol_down",
            row=1,
        )
        self.queue = queue

    async def callback(self, interaction: Interaction):
        current_volume_level = interaction.guild.voice_client.source.volume * 100
        current_volume_level -= 10
        if current_volume_level <= 0:
            current_volume_level = 1
        interaction.guild.voice_client.source.volume = current_volume_level / 100
        await change_volume_option(guild_id=interaction.guild_id, volume_level=current_volume_level)
        await self.queue.update_messages()
        await interaction.response.defer()
