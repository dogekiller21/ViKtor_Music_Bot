import discord

from utils.buttons import (
    PauseButton,
    SkipButton,
    RepeatButton,
    VolumeUpButton,
    VolumeDownButton,
    StopButton,
    BackButton,
    ShuffleButton,
)


class PlayerView(discord.ui.View):
    def __init__(self, voice, storage):
        self.voice = voice
        self.storage = storage
        items = (
            BackButton(voice=voice, storage=storage),
            PauseButton(voice=voice, storage=storage),
            SkipButton(voice=voice, storage=storage),
            RepeatButton(voice=voice, storage=storage),
            VolumeDownButton(voice=voice, storage=storage),
            VolumeUpButton(voice=voice, storage=storage),
            StopButton(voice=voice, storage=storage),
            ShuffleButton(voice=voice, storage=storage),
        )
        super().__init__(*items, timeout=None)

    async def interaction_check(self, interaction):
        if interaction.guild.voice_client is None:
            return False
        return True


class Dropdown(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Choose track to play",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def disable(self, message):
        self.disabled = True
        self.view.stop()
        self.placeholder = self.options[int(self.values[0])].label
        await message.edit(view=self.view)

    async def callback(self, interaction: discord.Interaction):
        message = interaction.message
        await self.disable(message)


class DropdownView(discord.ui.View):
    def __init__(self, dropdown):
        self.item = dropdown
        self.user_id = None
        self.message = None
        super().__init__(dropdown, timeout=10)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    async def send(self, ctx):
        self.message = await ctx.respond(view=self)
        self.user_id = ctx.user.id

    async def on_timeout(self):
        await self.item.disable(self.message)
