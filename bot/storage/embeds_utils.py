from typing import TYPE_CHECKING
from discord import Embed

if TYPE_CHECKING:
    from bot.storage import Queue


class StorageEmbeds:
    @staticmethod
    def get_player_message(queue: "Queue") -> Embed | None:
        current_track = queue.get_current_track()
        if current_track is None:
            return
        current_track_name = f"{current_track.artist} - {current_track.title}"
        if len(current_track_name) >= 40:
            current_track_name = f"{current_track_name[:40]}..."
        current_guild = queue.client.get_guild(queue.guild_id)
        voice = current_guild.voice_client
        play_pause_status = "⏸ Paused" if voice.is_paused() else "▶ Playing"
        embed = Embed(
            title=f'🎧 Player in "{voice.channel.name}"',
            description=f"`📃 Tracks in queue: {len(queue)}`\n"
            f"`🔊 Volume: {voice.source.volume * 100}%`\n"
            f"`{play_pause_status}`\n",
        )

        embed.add_field(
            name="**Now playing**",
            value=f"{queue.current_index + 1}. **{current_track_name}** {current_track.duration}",
            inline=False,
        )
        embed.set_thumbnail(url=current_track.thumb_url)

        return embed
