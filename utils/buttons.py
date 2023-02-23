import asyncio
import random

import discord
from discord import Interaction

from constants import PlayerEmojis


class BackButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.BACK_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:back",
            row=0,
        )

    async def callback(self, interaction):
        self.voice = interaction.guild.voice_client

        queue = self.storage.get_queue(interaction.guild.id)
        queue.switch_reverse_mode()
        self.voice.stop()
        await asyncio.sleep(0.2)
        queue.switch_reverse_mode()


class PauseButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.PAUSE_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:pause",
            row=0,
        )

    async def callback(self, interaction: Interaction):
        self.voice = interaction.guild.voice_client
        if self.voice.is_paused():
            self.voice.resume()
        else:
            self.voice.pause()

        await self.storage.update_message(interaction.guild.id, interaction.message)


class SkipButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.SKIP_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:skip",
            row=0,
        )

    async def callback(self, interaction):
        self.voice = interaction.guild.voice_client

        self.voice.stop()
        if self.voice is None:
            return


class RepeatButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.REPEAT_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:repeat_mode",
            row=0,
        )

    async def callback(self, interaction):
        self.voice = interaction.guild.voice_client

        queue = self.storage.get_queue(self.voice.guild.id)
        queue.switch_repeat_mode()

        await self.storage.update_message(interaction.guild.id)


class StopButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.STOP_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:stop",
            row=0,
        )

    async def callback(self, interaction):
        self.voice = interaction.guild.voice_client

        self.storage.delete_queue(self.voice.guild.id)
        self.voice.stop()


class VolumeDownButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.VOL_DOWN_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:volume_down",
            row=1,
        )

    async def callback(self, interaction):
        self.voice = interaction.guild.voice_client

        volume_level = self.voice.source.volume * 100
        if volume_level == 1:
            return

        volume_level -= 10
        if volume_level < 1:
            volume_level = 1

        self.voice.source.volume = volume_level / 100

        await self.storage.update_message(interaction.guild.id)

        self.storage.client.change_volume(interaction.guild.id, volume_level)


class VolumeUpButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.VOL_UP_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:volume_up",
            row=1,
        )

    async def callback(self, interaction):
        self.voice = interaction.guild.voice_client

        volume_level = self.voice.source.volume * 100
        if volume_level == 100:
            return

        volume_level += 10
        if volume_level > 100:
            volume_level = 100

        self.voice.source.volume = volume_level / 100

        await self.storage.update_message(interaction.guild.id)
        self.storage.client.change_volume(interaction.guild.id, volume_level)


class ShuffleButton(discord.ui.Button):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        super().__init__(
            emoji=PlayerEmojis.SHUFFLE_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"{voice.guild.id}:shuffle",
            row=2,
        )

    async def callback(self, interaction):
        queue = self.storage.get_queue(interaction.guild.id)
        queue.current_index = 0
        random.shuffle(queue.tracks)
        await self.storage.update_message(interaction.guild.id)
        self.voice.stop()
