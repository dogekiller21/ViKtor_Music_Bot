import asyncio
import logging

from discord import (
    Bot,
    ApplicationContext,
    option,
    AutocompleteContext,
    OptionChoice,
    CheckFailure,
    Guild,
    SlashCommandGroup,
    ApplicationCommandError,
)
from discord.ext import commands
from discord.commands import slash_command
from vkwave.api.methods._error import APIError

from bot.checks import check_user_voice, check_self_voice
from bot.embeds import BotEmbeds
from bot.storage import QueueStorage
from bot.utils import get_source, join_author_voice, check_guild
from db.db import get_settings
from db.models import Settings
from vk_parsing.exceptions import IncorrectPlaylistUrlException
from vk_parsing.models import TrackInfo
from vk_parsing.parsing import get_client, VkParsingClient


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, client: Bot):
        self.client = client
        # self.vk_parser: VkParsingClient = self.client.loop.run_until_complete(get_client())
        self.vk_parser: VkParsingClient = VkParsingClient()
        self.storage = QueueStorage(client=self.client)

    async def cog_before_invoke(self, ctx: ApplicationContext):
        await check_guild(guild=ctx.guild)

    async def _search_track_autocomplete(
        self, ctx: AutocompleteContext
    ) -> list[OptionChoice]:
        query = ctx.value.lower()
        if not query:
            return []
        results = await self.vk_parser.search_tracks_by_title(title=query)
        if not results:
            return []
        choices = []
        for result in results:
            full_title = f"{result.artist} - {result.title}"
            if len(full_title) > 50:
                full_title = f"{full_title[:50 + 1]}..."
            choices.append(
                OptionChoice(
                    name=f"🎵 {full_title} [{result.duration}]", value=result.vk_id
                )
            )
        return choices

    def _after(self, error: Exception, guild: Guild):
        if error:
            print(f"Error while playing in {guild.name}: {error}")
        if guild.voice_client is None:
            logging.info(f"Voice client in {guild.name} is None, skipping _after")
            return
        queue = self.storage.get_queue(guild_id=guild.id, create_if_not_exist=False)
        if queue is None:
            logging.info(f"End of queue for guild {guild.name}")
            return
        queue.inc_index()
        current_track = queue.get_current_track()
        if current_track is None:
            logging.info(f"End of queue for guild {guild.name}")
            asyncio.run_coroutine_threadsafe(
                coro=self.storage.del_queue(guild_id=guild.id),
                loop=guild.voice_client.client.loop,
            )
            return
        # TODO: переделать чтоб это лежало в классе Queue
        db_settings: Settings = asyncio.run_coroutine_threadsafe(
            coro=get_settings(guild_id=guild.id),
            loop=guild.voice_client.client.loop
        ).result()
        guild.voice_client.play(
            source=get_source(track_url=current_track.mp3_url, volume_level=db_settings.volume_option / 100),
            after=lambda err: self._after(error=err, guild=guild),
        )
        asyncio.run_coroutine_threadsafe(
            coro=queue.update_messages(), loop=guild.voice_client.client.loop
        )

    async def _add_tracks_and_send_message(
        self, ctx: ApplicationContext, tracks: list[TrackInfo]
    ):
        queue = self.storage.get_queue(guild_id=ctx.guild_id)
        added_tracks_count = queue.add_tracks(tracks=tracks)
        db_settings = await get_settings(guild_id=ctx.guild_id)
        if not ctx.voice_client.source:
            ctx.voice_client.play(
                source=get_source(track_url=tracks[0].mp3_url, volume_level=db_settings.volume_option / 100),
                after=lambda err: self._after(error=err, guild=ctx.guild),
            )
            await queue.send_player_message(ctx=ctx)
            return
        await queue.update_messages()
        await ctx.respond(
            embed=BotEmbeds.info_embed(
                description=f"Added {added_tracks_count} track{'s' if added_tracks_count > 1 else ''}\n"
                f"**{f'{tracks[0].get_full_name()}' if added_tracks_count > 1 else ''}**"
            )
        )

    play_group = SlashCommandGroup("play", "Play commands")

    @play_group.command(
        name="track",
        description="Search and play single track",
        checks=[check_user_voice],
    )
    @option(
        name="track_name",
        description="Type a track name to search",
        required=True,
        autocomplete=_search_track_autocomplete,
    )
    async def play_single_track(self, ctx: ApplicationContext, track_name: str):
        await ctx.defer()  # без этого ctx.respond возвращает Interaction с пустым .message
        #                    await ctx.respond(..., wait=True) может решить это (вроде)
        vk_track = await self.vk_parser.get_track_by_id(track_id=track_name)
        await self._add_tracks_and_send_message(ctx=ctx, tracks=[vk_track])

    @play_group.command(
        name="playlist",
        description="Play vk album or playlist",
        checks=[check_user_voice],
    )
    @option(
        name="playlist_link",
        description="A link to a playlist or album",
        required=True,
    )
    async def play_playlist(self, ctx: ApplicationContext, playlist_link: str):
        await ctx.defer()
        playlist_tracks = await self.vk_parser.get_playlist_tracks(url=playlist_link)
        await self._add_tracks_and_send_message(ctx=ctx, tracks=playlist_tracks)

    @slash_command(name="stop", description="Stop playing", checks=[check_self_voice])
    async def stop_playing(self, ctx: ApplicationContext):
        await self.storage.del_queue(guild_id=ctx.guild_id)
        ctx.voice_client.stop()
        await ctx.respond(
            embed=BotEmbeds.info_embed(description="Thanks for listening <3")
        )

    @slash_command(
        name="leave",
        description="Leave channel, remove tracks from queue if any",
        checks=[check_self_voice]
    )
    async def leave_channel(self, ctx: ApplicationContext):
        await self.storage.del_queue(guild_id=ctx.guild_id)
        await ctx.voice_client.disconnect(force=True)
        await ctx.respond(
            embed=BotEmbeds.info_embed(description="Bye!")
        )

    @slash_command(
        name="queue",
        description="Get queue list for current playlist",
        checks=[check_self_voice]
    )
    async def queue_command(self, ctx: ApplicationContext):
        queue = self.storage.get_queue(guild_id=ctx.guild_id)
        await queue.send_queue_message(ctx=ctx)

    @play_single_track.before_invoke
    @play_playlist.before_invoke
    async def ensure_self_voice_and_join(self, ctx: ApplicationContext):
        await join_author_voice(ctx=ctx)

    @play_single_track.error
    async def on_error_play_single_track(
        self, ctx: ApplicationContext, error: ApplicationCommandError | APIError
    ):
        if isinstance(error, CheckFailure):
            await ctx.respond(
                embed=BotEmbeds.error_embed(
                    description="Connect to voice channel first"
                ),
                ephemeral=True,
            )
            return
        if isinstance(error, APIError):
            await ctx.respond(
                embed=BotEmbeds.error_embed(
                    description=f"Error occurred while getting song url, try again later"
                ),
                ephemeral=True,
            )
            return

    @play_playlist.error
    async def on_error_play_playlist(
        self, ctx: ApplicationContext, error: ApplicationCommandError
    ):
        if isinstance(error, CheckFailure):
            await ctx.respond(
                embed=BotEmbeds.error_embed(
                    description="Connect to voice channel to play playlists"
                ),
                ephemeral=True,
            )
            return
        if isinstance(error, IncorrectPlaylistUrlException):
            await ctx.respond(
                embed=BotEmbeds.error_embed(description="Incorrect link passed"),
                ephemeral=True,
            )
            return
        if isinstance(error, IncorrectPlaylistUrlException):
            await ctx.respond(
                embed=BotEmbeds.error_embed(description="No tracks in playlist"),
                ephemeral=True,
            )
            return

    @stop_playing.error
    @leave_channel.error
    @queue_command.error
    async def on_error_no_self_voice(
        self, ctx: ApplicationContext, error: ApplicationCommandError
    ):
        if isinstance(error, CheckFailure):
            await ctx.respond(
                embed=BotEmbeds.error_embed(description="Nothing is playing"),
                ephemeral=True,
            )


def setup(client: Bot):
    client.add_cog(MusicCog(client=client))
