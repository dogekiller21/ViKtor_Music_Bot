from typing import Union, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Bot

from bot.cogs.constants import DEFAULT_ICON_URL
from bot.cogs.player_storage import QueueMessagesStorage
from bot.utils import embed_utils, player_msg_utils


class PlayerStorage(dict):
    def __init__(self, queue_messages: QueueMessagesStorage, client: Bot):
        super().__init__()
        self: dict[int, dict[str, Union[int, discord.Message]]]
        self.queue_messages = queue_messages
        self.tracks = self.queue_messages.tracks
        self.client = client

    def check_player_msg(self, guild_id: int) -> bool:
        return guild_id in self.tracks and guild_id in self

    def get_requester(self, track: dict):
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

    def create_player_embed(self, ctx: commands.Context) -> Optional[discord.Embed]:
        current_tracks = self.tracks.get(ctx.guild.id)
        if current_tracks is None:
            return
        length = len(current_tracks["tracks"])

        now_playing = current_tracks["index"]
        tracks = current_tracks["tracks"]
        prev_index, next_index = now_playing - 1, now_playing + 1

        embed = embed_utils.create_music_embed(
            title=f'Плеер в канале "{ctx.voice_client.channel.name}"',
            description=f"`Треков в очереди: {length}`\n"
            f"{player_msg_utils.get_loop_str_min(ctx.guild)}",
        )
        requester = self.get_requester(tracks[now_playing])
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
        if not self.check_player_msg(ctx.guild.id):
            return

        embed = self.create_player_embed(ctx)
        if embed is None:
            return
        try:
            await self[ctx.guild.id].edit(embed=embed)
        except discord.NotFound:
            del self[ctx.guild.id]

    async def delete_messages(self, guild_id, delay: int = 2):
        """
        Delete queue and player messages for guild
        """
        current_queue_message = self.queue_messages.get(guild_id)
        current_player_message = self.get(guild_id)
        for messages_container, message in [
            (self.queue_messages, current_queue_message),
            (self, current_player_message),
        ]:
            if message is None:
                continue
            if isinstance(message, dict):
                message = message["message"]
            del messages_container[guild_id]
            await message.delete(delay=delay)

    async def update_messages(self, ctx) -> None:
        await self.player_message_update(ctx=ctx)
        await self.queue_messages.queue_message_update(ctx=ctx)
