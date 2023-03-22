from typing import TYPE_CHECKING
from discord.ui import View
from bot.ui.buttons import (
    SkipButton,
    StopButton,
    PlayPauseButton,
    PrevButton,
    ShuffleButton,
    VolUpButton,
    VolDownButton,
)

if TYPE_CHECKING:
    from bot.storage import Queue, QueueStorage


class PlayerView(View):
    def __init__(self, queue: "Queue", storage: "QueueStorage"):
        # self.queue = queue
        # self.storage = storage
        items = (
            ShuffleButton(queue=queue),
            PrevButton(queue=queue),
            PlayPauseButton(queue=queue),
            SkipButton(guild_id=queue.guild_id),
            StopButton(guild_id=queue.guild_id, storage=storage),
            VolUpButton(queue=queue),
            VolDownButton(queue=queue),
        )

        super().__init__(*items, timeout=None)

    async def interaction_check(self, interaction):
        if interaction.guild.voice_client is None:
            return False
        return True
