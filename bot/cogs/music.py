from discord import Bot, ApplicationContext, option, AutocompleteContext, OptionChoice, PCMVolumeTransformer, \
    FFmpegPCMAudio, VoiceClient, VoiceProtocol, DiscordException, Embed, CheckFailure
from discord.ext import commands
from discord.commands import slash_command

from bot.checks import check_user_voice
from bot.constants import FFMPEG_OPTIONS
from vk_parsing.parsing import get_client, VkParsingClient


class Music(commands.Cog):
    def __init__(self, client: Bot):
        self.client = client
        # self.vk_parser: VkParsingClient = self.client.loop.run_until_complete(get_client())
        self.vk_parser: VkParsingClient = VkParsingClient()

    async def _search_track_autocomplete(self, ctx: AutocompleteContext) -> list[OptionChoice]:
        query = ctx.value.lower()
        if not query:
            return []
        results = await self.vk_parser.search_tracks_by_title(title=query)
        if not results:
            return []
        # print(f"{len(results)=}")
        choices = []
        for result in results:
            full_title = f"{result.artist} - {result.title}"
            if len(full_title) > 50:
                full_title = f"{full_title[:50 + 1]}..."
            choices.append(
                OptionChoice(
                    name=f"🎵 {full_title} [{result.duration}]",
                    value=result.vk_id
                )
            )

        # for i, choice in enumerate(choices):
        #     print(f"{i}. {choice.name}")
        return choices

    @slash_command(
        name="play",
        description="Search and play single track",
        checks=[check_user_voice]
    )
    @option(
        name="track",
        description="Type a track name to search",
        required=True,
        autocomplete=_search_track_autocomplete
    )
    async def play_single_track(self, ctx: ApplicationContext, track: str):
        vk_track = await self.vk_parser.get_track_by_id(track_id=track)
        source = PCMVolumeTransformer(
            FFmpegPCMAudio(vk_track.mp3_url, **FFMPEG_OPTIONS)
        )
        source.volume = .5
        ctx.voice_client.play(source=source, after=lambda e: print(e))
        await ctx.respond(vk_track.mp3_url)

    @slash_command(name="stop", description="Stop playing")
    async def stop_playing(self, ctx: ApplicationContext):
        ...

    async def _join_author_voice(self, ctx: ApplicationContext) -> VoiceClient | VoiceProtocol:
        channel = ctx.user.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        return ctx.voice_client

    @play_single_track.before_invoke
    async def ensure_self_voice(self, ctx: ApplicationContext):
        await self._join_author_voice(ctx=ctx)

    @play_single_track.error
    async def on_error_play_single_track(self, ctx: ApplicationContext, error: DiscordException):
        if isinstance(error, CheckFailure):
            embed = Embed(
                description="Connect to voice channel first"
            )
            await ctx.respond(embed=embed, ephemeral=True)


def setup(client: Bot):
    client.add_cog(Music(client=client))
