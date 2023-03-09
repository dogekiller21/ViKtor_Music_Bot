from typing import TYPE_CHECKING
from discord import Embed, ButtonStyle
from discord.ext.pages import Paginator, PaginatorButton, Page

from bot.constants import CustomColors

if TYPE_CHECKING:
    from bot.storage import Queue


class StorageEmbeds:

    @staticmethod
    def queue_embed(description: str | None = None, title: str | None = None, **kwargs):
        return Embed(
            title=title,
            description=description,
            color=CustomColors.INFO_COLOR,
            **kwargs
        )

    @staticmethod
    def get_player_embed(queue: "Queue") -> Embed | None:
        current_track = queue.get_current_track()
        if current_track is None:
            return
        current_guild = queue.client.get_guild(queue.guild_id)
        voice = current_guild.voice_client
        play_pause_status = "⏸ Paused" if voice.is_paused() else "▶ Playing"
        embed = Embed(
            title=f'🎧 Player in "{voice.channel.name}"',
            description=f"`📃 Tracks in queue: {len(queue)}`\n"
            f"`🔊 Volume: {voice.source.volume * 100}%`\n"
            f"`{play_pause_status}`\n",
        )
        previous_track = queue.get_previous_track()
        if previous_track is not None:
            embed.add_field(
                name="**Previous track**",
                value=f"**{queue.current_index - 1 + 1}. {previous_track.get_full_name()}** {previous_track.duration}",
                inline=False,
            )
        embed.add_field(
            name="**⇀Now playing↽**",
            value=f"**{queue.current_index + 1}. {current_track.get_full_name()}** {current_track.duration}",
            inline=False,
        )
        next_track = queue.get_next_track()
        if next_track is not None:
            embed.add_field(
                name="**Next track**",
                value=f"**{queue.current_index + 1 + 1}. {next_track.get_full_name()}** {next_track.duration}",
            )
        embed.set_thumbnail(url=current_track.thumb_url)

        return embed

    @staticmethod
    def get_queue_pages_and_page(queue: "Queue") -> tuple[list[Embed], int]:
        current_track = queue.get_current_track()
        pages = []
        page_tracks = []
        for i, track in enumerate(queue.tracks, start=1):
            track_info = f"**{i}. {track.get_full_name()}** {track.duration}"
            if track == current_track:
                track_info = f"**⇀Now playing↽**\n{track_info}"
            page_tracks.append(track_info)
            if len(page_tracks) == 10:
                pages.append(
                    StorageEmbeds.queue_embed(
                        description="\n\n".join(page_tracks)
                    )
                )
                page_tracks.clear()
        current_page = queue.current_index // 10
        return pages, current_page

    @staticmethod
    def get_queue_paginator(queue: "Queue") -> Paginator | None:
        if not queue.tracks:
            return
        page_buttons = [
            PaginatorButton(
                "first", emoji="⏪", style=ButtonStyle.green
            ),
            PaginatorButton("prev", emoji="⬅", style=ButtonStyle.green),
            PaginatorButton(
                "page_indicator", style=ButtonStyle.gray, disabled=True
            ),
            PaginatorButton("next", emoji="➡", style=ButtonStyle.green),
            PaginatorButton("last", emoji="⏩", style=ButtonStyle.green),
        ]
        pages, current_page = StorageEmbeds.get_queue_pages_and_page(queue=queue)

        paginator = Paginator(
            pages=pages,
            show_disabled=True,
            show_indicator=True,
            use_default_buttons=False,
            custom_buttons=page_buttons,
            timeout=None,
            author_check=False,
        )
        paginator.current_page = current_page
        return paginator
