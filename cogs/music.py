import asyncio

import discord
from discord import SlashCommandGroup
from discord.commands import slash_command
from discord.ext import commands

from bot_storage.storage import BotStorage, Queue
from constants import VK_URL_PREFIX, FFMPEG_OPTIONS
from exceptions.custrom_exceptions import (
    UserVoiceException,
    SelfVoiceException,
    IncorrectLinkException,
)
from utils.commands_utils import join_channel
from utils.embed_utils import Embeds
from utils.views import Dropdown, DropdownView
from vk_parsing.main import get_request, find_tracks_by_name


class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.storage = BotStorage(self.client)

    @slash_command(name="player", description="Get player for current playlist")
    async def player_command(self, ctx):
        await self.storage.send_message(ctx)

    @slash_command(name="stop", description="Stop listening")
    async def stop_command(self, ctx):
        self.storage.delete_queue(ctx.guild.id)

        voice = ctx.voice_client
        voice.stop()
        embed = Embeds.info_embed(
            title="Stop playing", description=f"Playing stopped in {voice.channel.name}"
        )
        await ctx.respond(embed=embed)

    @slash_command(name="join", description="Bot join your voice channel")
    async def join_command(self, ctx):
        voice = await join_channel(ctx)

        embed = Embeds.info_embed(description=f"Connected to channel {voice.channel}")
        await ctx.respond(embed=embed)

    @slash_command(name="leave", description="Make bot leave voice channel")
    async def leave_command(self, ctx):
        voice = ctx.voice_client

        if voice.is_connected():
            await voice.disconnect(force=False)
        embed = Embeds.info_embed(description=f"Left from channel **{voice.channel}**")

        await ctx.respond(embed=embed, ephemeral=True)

    def _play_next(self, errors, ctx):
        queue: Queue = self.storage.get_queue(ctx.guild.id)
        if queue is None:
            return
        voice = ctx.voice_client
        if voice is None:
            return
        next_track = queue.get_next_track()
        if next_track is None:
            self.storage.delete_queue(ctx.guild.id)
            return

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(next_track["url"], **FFMPEG_OPTIONS)
        )

        source.volume = self.client.get_volume(ctx.guild.id) / 100

        voice.play(source=source, after=lambda e: self._play_next(e, ctx))

        asyncio.run_coroutine_threadsafe(
            self.storage.update_message(ctx.guild.id), self.client.loop
        )

    async def add_tracks(self, ctx, tracks):
        if not isinstance(tracks, list):
            tracks = [tracks]
        tracks = [track for track in tracks if track["url"]]
        if self.storage.get_queue(ctx.guild.id) is None:

            new_queue = self.storage.add_queue(ctx.guild.id)
            new_queue.add_tracks(tracks)

            track_to_play = tracks if isinstance(tracks, dict) else tracks[0]

            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(track_to_play["url"], **FFMPEG_OPTIONS)
            )
            source.volume = self.client.get_volume(ctx.guild.id) / 100

            voice = ctx.voice_client
            voice.play(source=source, after=lambda e: self._play_next(e, ctx))
            await self.player_command(ctx)

        else:
            self.storage.add_tracks(ctx.guild.id, tracks)
            if isinstance(tracks, list):
                embed = Embeds.music_embed(
                    description=f"Added {len(tracks)} tracks to queue"
                )
            else:
                embed = Embeds.music_embed(
                    title="Track added to queue", description=f"**{tracks['name']}**"
                )
            await ctx.respond(embed=embed)

    play_group = SlashCommandGroup("play", "Play commands")

    @play_group.command(name="playlist", description="Play tracks from VK playlist")
    async def playlist_command(
        self, ctx, link: discord.Option(str, "Playlist link", required=True)
    ):
        if VK_URL_PREFIX not in link:
            raise IncorrectLinkException

        if (
            ctx.voice_client is None
            or ctx.voice_client.channel != ctx.author.voice.channel
        ):
            await join_channel(ctx)

        await ctx.defer()
        try:
            parsed_items = await get_request(link)
        except IndexError:  # temp = link.split("audio_playlist")[1]
            embed = Embeds.error_embed(description="Incorrect link")
            await ctx.respond(embed=embed)
        else:
            await self.add_tracks(ctx, parsed_items)

    @play_group.command(name="search", description="Find track by name")
    async def search_command(
        self, ctx, query: discord.Option(str, "Search query", required=True)
    ):
        if (
            ctx.voice_client is None
            or ctx.voice_client.channel != ctx.author.voice.channel
        ):
            await join_channel(ctx)

        await ctx.defer()
        try:
            tracks = await find_tracks_by_name(query)
        except Exception as error:
            print(f"search command error: {error}")
            embed = Embeds.error_embed(
                description=f"Error occurred while parsing your request: {query}"
            )
            return await ctx.respond(embed=embed)

        if tracks is None:
            embed = Embeds.error_embed(
                title="Tracks can't be found",
                description=f"Can't find tracks with request: **{query}**",
            )
            return await ctx.respond(embed=embed)

        options = []
        for i, track in enumerate(tracks):
            options.append(
                discord.SelectOption(
                    label=f"{track['name']}",
                    description=f"{track['name']}",
                    value=str(i),
                )
            )

        dropdown = Dropdown(options)
        dropdown_view = DropdownView(dropdown)
        await dropdown_view.send(ctx)

        await dropdown_view.wait()
        value = int(dropdown.values[0])
        await self.add_tracks(ctx, tracks[value])

    @slash_command(name="pause", description="Pause current queue")
    async def pause_command(self, ctx):
        voice = ctx.voice_client
        voice.pause()

        await ctx.respond(embed=Embeds.music_embed(description="Playing paused"))

    @slash_command(name="resume", description="Resume playing")
    async def resume_command(self, ctx):
        voice = ctx.voice_client
        voice.resume()

        await ctx.respond(embed=Embeds.music_embed(description="Continuing playing"))

    @slash_command(name="volume", description="Edit music volume")
    async def volume_command(
        self,
        ctx,
        level: discord.Option(
            int,
            description="Volume level (1 - 100)",
            required=True,
            min_value=1,
            max_value=100,
        ),
    ):
        ctx.voice_client.source.volume = level / 100

        embed = Embeds.music_embed(
            title="Volume level changed",
            description=f"Volume level changed to {level / 100} **({level}%)**",
        )
        await ctx.respond(embed=embed)
        self.client.change_volume(ctx.guild.id, level)

    @slash_command(
        name="repeat",
        description="Switch repeat mode (None -> One -> All -> None -> ...)",
    )
    async def repeat_command(self, ctx):
        queue = self.storage.get_queue(ctx.guild.id)
        queue.switch_repeat_mode()

        embed = Embeds.music_embed(
            title="Repeat mode switched",
            description=f"Repeat mode switched to **{queue.repeat_mode}**",
        )

        await ctx.respond(embed=embed)

    @slash_command(name="skip", description="Skip current track")
    async def skip_command(self, ctx):
        queue = self.storage.get_queue(ctx.guild.id)
        embed = Embeds.music_embed(
            title="Track skipped", description=f"{queue.current_track['name']}"
        )

        voice = ctx.voice_client
        voice.stop()
        next_track = queue.next_track
        if next_track is None:
            embed.add_field(name="Playing stopped", value="Removing queue")
        else:
            embed.add_field(name="Now playing", value=f"{next_track['name']}")

        await ctx.respond(embed=embed)

    @slash_command(name="back", description="Play previous track")
    async def back_command(self, ctx):
        queue = self.storage.get_queue(ctx.guild.id)

        queue.switch_reverse_mode()
        voice = ctx.voice_client
        voice.stop()
        next_track = queue.next_track
        if next_track is None:
            embed = Embeds.info_embed(description="Stop playing")
        else:
            embed = Embeds.music_embed(
                title="Now playing", description=next_track["name"]
            )
        await ctx.respond(embed=embed)
        queue.switch_reverse_mode()

    @slash_command(name="reverse", description="Switch reverse play mode")
    async def reverse_command(self, ctx):
        queue = self.storage.get_queue(ctx.guild.id)
        queue.switch_reverse_mode()

        embed = Embeds.info_embed(description="Reverse mode switched")
        await ctx.respond(embed=embed)

    @playlist_command.before_invoke
    @join_command.before_invoke
    @search_command.before_invoke
    async def ensure_author_voice(self, ctx):
        if not ctx.author.voice:
            raise UserVoiceException

    @leave_command.before_invoke
    @player_command.before_invoke
    @skip_command.before_invoke
    @pause_command.before_invoke
    @stop_command.before_invoke
    async def ensure_self_voice(self, ctx):
        if ctx.voice_client is None:
            raise SelfVoiceException

    @playlist_command.after_invoke
    @search_command.after_invoke
    @pause_command.after_invoke
    @resume_command.after_invoke
    @repeat_command.after_invoke
    @reverse_command.after_invoke
    async def update_player_message(self, ctx):
        await self.storage.update_message(ctx.guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member != self.client.user:
            return
        voice = member.guild.voice_client

        guild_id = member.guild.id
        print("voice state updated")
        if voice and not voice.is_connected() and after.channel is None:
            print("disconnected")
            if self.storage.get_queue(guild_id) is None:
                self.storage.delete_queue(member.guild.id)
                voice.stop()


def setup(bot):
    bot.add_cog(MusicBot(bot))
