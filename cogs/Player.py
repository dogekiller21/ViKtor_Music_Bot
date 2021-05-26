import asyncio
from random import shuffle
from typing import Optional

import discord
from discord import NotFound

from discord.ext import commands

import functions
import vk_parsing
from utils import embed_utils
from utils.custom_exceptions import NoTracksFound


class Player(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.tracks = {}
        self.queue_messages = {}
        self.player_messages = {}
        self.loop = self.client.loop

    async def nothing_is_playing_error(self, ctx: commands.Context):
        if ctx.author.bot:
            return
        embed = embed_utils.create_error_embed("Nothing is playing")
        await ctx.send(embed=embed, delete_after=5)

        await ctx.message.add_reaction("❌")

    def get_pages(self, guild_id, page: Optional[int] = None):
        tracks = self.tracks[guild_id]["tracks"]
        now_playing = self.tracks[guild_id]["index"]
        if (len(tracks) % 10) == 0:
            pages = int(len(tracks) / 10)
        else:
            pages = int((len(tracks) / 10)) + 1

        if page is None:
            if ((now_playing + 1) % 10) != 0:
                page = (now_playing + 1) // 10 + 1
            else:
                page = (now_playing + 1) // 10
        return page, pages

    def _get_duration(self, duration: int) -> str:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = (duration % 3600) % 60
        dur = f""
        if hours != 0:
            dur += f"{hours}:"
        dur += f"{minutes:02d}:{seconds:02d}"
        return dur

    def create_player_embed(self, ctx: commands.Context):
        length = len(self.tracks[ctx.guild.id]["tracks"])
        print(length)
        embed = embed_utils.create_music_embed(
            title=f"Player in {ctx.voice_client.channel.name}",
            description=f"{length} tracks in queue",
            image="https://avatanplus.ru/files/resources/original/567059bd72e8a151a6de8c1f.png"
        )

        now_playing = self.tracks[ctx.guild.id]["index"]
        tracks = self.tracks[ctx.guild.id]["tracks"]
        prev_index, next_index = now_playing - 1, now_playing + 1
        if prev_index >= 0:
            dur = self._get_duration(tracks[prev_index]["duration"])
            embed.add_field(name="Previous track",
                            value=f"**{prev_index + 1}. {tracks[prev_index]['name']}** {dur}\n",
                            inline=False)

        voice = ctx.voice_client
        title = "⟶ Paused ⟵" if voice.is_paused() else "⟶ Now playing ⟵"

        dur = self._get_duration(tracks[now_playing]["duration"])
        embed.add_field(
            name=title,
            value=f"**{now_playing + 1}. {tracks[now_playing]['name']}** {dur}",
            inline=False
        )

        if next_index < len(tracks):
            dur = self._get_duration(tracks[next_index]["duration"])
            embed.add_field(name="Next track",
                            value=f"\n**{next_index + 1}. {tracks[next_index]['name']}** {dur}",
                            inline=False)

        return embed

    def create_queue_embed(self, ctx: commands.Context, page: Optional[int] = None):
        voice = ctx.voice_client
        if voice.is_paused():
            paused = True
        else:
            paused = False
        page, pages = self.get_pages(ctx.guild.id, page)
        tracks = self.tracks[ctx.guild.id]["tracks"]
        now_playing = self.tracks[ctx.guild.id]["index"]
        loop_settings = functions.get_guild_smf(ctx.guild.id, "loop_queue")

        if page == 1:
            page_index = 0
        else:
            page_index = (page - 1) * 10

        tracks_to_str = []
        for i, track in enumerate(tracks[page_index::]):
            if i == 10:
                break

            dur = self._get_duration(track["duration"])
            track_index = i + page_index
            tracks_to_str.append(
                f"**{track_index + 1}. {track['name']}** {dur}"
            )
            if track_index == now_playing:
                if paused:
                    tracks_to_str[-1] += "\n↑ paused ↑"
                else:
                    tracks_to_str[-1] += "\n↑ now playing ↑"

        if loop_settings:
            loop_str = "Queue loop is enabled"
        else:
            loop_str = "Queue loop is disabled"

        if (len(tracks)) > 10:
            pages = f"Page: {page} / {pages} | {loop_str}"
        else:
            pages = f"{loop_str}"

        embed = embed_utils.create_music_embed(
            description="\n\n".join(tracks_to_str),
            footer=pages
        )
        return embed

    async def queue_message_update(self, ctx):
        if ctx.guild.id not in self.queue_messages:
            return
        page, _ = self.get_pages(ctx.guild.id)
        if page != self.queue_messages[ctx.guild.id]["page"]:
            return
        embed = self.create_queue_embed(ctx)

        try:
            await self.queue_messages[ctx.guild.id]["message"].edit(embed=embed)
        except NotFound:
            return

    async def player_message_update(self, ctx):
        try:
            embed = self.create_player_embed(ctx)
        except KeyError:
            return
        await self.player_messages[ctx.guild.id].edit(embed=embed)

    async def queue_index_overflow(
            self,
            ctx: commands.Context,
            voice_client: discord.VoiceClient,
            default: int
    ):

        is_looping = functions.get_guild_smf(ctx.guild.id, "loop_queue")
        if is_looping:
            new_index = default
        else:
            embed = embed_utils.create_info_embed(
                description="Queue loop is disabled in your guild\n"
                            "Deleting queue"
            )
            await ctx.send(embed=embed, delete_after=5)

            del self.tracks[ctx.guild.id]

            await self.delete_messages(ctx.guild.id)
            new_index = None

        voice_client.stop()
        return new_index

    async def _join(self, ctx: commands.Context):
        user_channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(user_channel)
        else:
            await user_channel.connect()

    def play_next(self, error, voice, ctx):
        if error is not None:
            print(error)
        try:
            tracks_info = self.tracks[ctx.guild.id]
        except KeyError:
            return

        tracks, now_playing = tracks_info["tracks"], tracks_info["index"]

        if (new_index := now_playing + 1) > len(tracks) - 1:
            args = {
                "ctx": ctx,
                "voice_client": voice,
                "default": 0
            }
            new_index = asyncio.run_coroutine_threadsafe(
                self.queue_index_overflow(**args),
                self.loop
            ).result()
        if new_index is None:
            return
        voice.stop()

        voice.play(discord.FFmpegPCMAudio(source=tracks[new_index]["url"]),
                   after=lambda err: self.play_next(err, voice, ctx))
        self.tracks[ctx.guild.id]["index"] = new_index

        asyncio.run_coroutine_threadsafe(self.player_message_update(ctx), self.loop)
        asyncio.run_coroutine_threadsafe(self.queue_message_update(ctx), self.loop)

    async def delete_messages(self, guild_id):
        try:
            await self.queue_messages[guild_id]["message"].delete(delay=2)
        except (NotFound, KeyError):
            pass
        try:
            await self.player_messages[guild_id].delete(delay=2)
        except (NotFound, KeyError):
            pass
        try:
            del self.queue_messages[guild_id]
        except KeyError:
            pass
        try:
            del self.player_messages[guild_id]
        except KeyError:
            pass

    @commands.command(name="player", aliases=["Player"])
    @commands.guild_only()
    async def player_command(self, ctx: commands.Context):
        voice = ctx.voice_client
        if ctx.guild.id not in self.tracks:
            return await self.nothing_is_playing_error(ctx)
        if voice is not None:
            embed = self.create_player_embed(ctx)
            player_message = await ctx.send(embed=embed)
            if ctx.guild.id in self.player_messages:
                await self.player_messages[ctx.guild.id].delete(delay=2)
            self.player_messages[ctx.guild.id] = player_message
            emoji_list = ["🔀", "⏪", "▶", "⏩", "⏹", "🔁", "📑"]
            for emoji in emoji_list:
                await player_message.add_reaction(emoji)

    @commands.command(name="play", aliases=["Play"])
    @commands.guild_only()
    async def play_command(self, ctx: commands.Context, *link: Optional[str]):

        if not ctx.author.voice:
            embed = embed_utils.create_error_embed("You have to be connected to voice channel")

            await ctx.send(embed=embed, delete_after=5)

            return await ctx.message.add_reaction("❌")

        if (len(link) > 0) and "vk.com/" not in link[0]:
            return await self.add_to_queue_command(ctx, *link, track=None)

        voice = ctx.voice_client

        if not voice and (len(link) == 0):
            embed = embed_utils.create_error_embed(
                message="Add link or name of the track to command"
            )
            await ctx.message.add_reaction("❌")
            return await ctx.send(embed=embed, delete_after=5)

        if not voice or not voice.is_connected():
            await self._join(ctx)
            voice = ctx.voice_client
        elif (len(link) == 0) and not (voice.is_playing() or voice.is_paused()):
            return await self.nothing_is_playing_error(ctx)

        elif (voice.is_playing() or voice.is_paused()) and (len(link) != 0):
            del self.tracks[ctx.guild.id]

            await self.delete_messages(ctx.guild.id)

            voice.stop()

        elif voice.is_paused():
            voice.resume()
            await self.player_message_update(ctx)
            return await self.queue_message_update(ctx)

        elif voice.is_playing():
            if len(link) == 0:
                return
            voice.stop()

        link = link[0]
        tracks = await vk_parsing.get_audio(link)
        self.tracks[ctx.guild.id] = {"tracks": tracks, "index": 0}

        await self.player_command(ctx)

        voice.play(discord.FFmpegPCMAudio(source=tracks[0]["url"]),
                   after=lambda x: self.play_next(x, voice, ctx))

    @commands.command(name="pause")
    @commands.guild_only()
    async def pause_command(self, ctx: commands.Context):
        voice = ctx.voice_client
        if not voice.is_playing():
            return await self.nothing_is_playing_error(ctx)
        voice.pause()
        await self.player_message_update(ctx)
        await self.queue_message_update(ctx)

    @commands.command(name="stop")
    @commands.guild_only()
    async def stop_command(self, ctx: commands.Context):
        voice = ctx.voice_client
        if voice is None or not (voice.is_playing() or voice.is_paused()):
            await self.nothing_is_playing_error(ctx)
        if voice.is_connected():
            del self.tracks[ctx.guild.id]
            await self.delete_messages(ctx.guild.id)

            voice.stop()

    @commands.command(name="queue")
    @commands.guild_only()
    async def queue_command(self, ctx: commands.Context, *, page: Optional[int] = None):
        if ctx.message.author != self.client.user:
            await ctx.message.add_reaction("📄")

        page, pages = self.get_pages(ctx.guild.id, page)

        if page > pages:
            embed = embed_utils.create_error_embed("No such page in your queue")
            await ctx.send(embed=embed, delete_after=5)

            return await ctx.message.add_reaction("❌")
        embed = self.create_queue_embed(ctx, page)
        queue_message = await ctx.send(embed=embed)
        if ctx.guild.id in self.queue_messages:
            await self.queue_messages[ctx.guild.id]["message"].delete(delay=2)

        self.queue_messages[ctx.guild.id] = {
            "message": queue_message,
            "page": page
        }
        emoji_list = ["⬅", "➡"]
        for emoji in emoji_list:
            await queue_message.add_reaction(emoji)

    @commands.command(name="shuffle", pass_context=True)
    @commands.guild_only()
    async def shuffle_command(self, ctx: commands.Context):
        voice = ctx.voice_client
        if voice is not None and (voice.is_playing() or voice.is_paused()):
            tracks = self.tracks[ctx.guild.id]["tracks"]
            if len(tracks) == 1:
                return
            shuffle(tracks)
            self.tracks[ctx.guild.id] = {"tracks": tracks, "index": - 1}
            self.queue_messages[ctx.guild.id]["page"] = 1
            voice.stop()

    @commands.command(name="skip")
    @commands.guild_only()
    async def skip_command(self, ctx: commands.Context, *, count: Optional[int] = 1):
        voice = ctx.voice_client
        if voice is None:
            return await self.nothing_is_playing_error(ctx)
        try:
            tracks_info = self.tracks[ctx.guild.id]
        except KeyError:
            return await self.nothing_is_playing_error(ctx)

        tracks, index = tracks_info["tracks"], tracks_info["index"]
        if (new_index := index + count) > len(tracks) - 1:
            new_index = await self.queue_index_overflow(
                ctx=ctx,
                voice_client=voice,
                default=0
            )
        if new_index is not None:
            self.tracks[ctx.guild.id]["index"] = new_index - 1
            voice.stop()

    @commands.command(name="prev")
    @commands.guild_only()
    async def prev_command(self, ctx: commands.Context, *, count: Optional[int] = 1):
        voice = ctx.voice_client
        if voice is None:
            await self.nothing_is_playing_error(ctx)

        else:
            if ctx.guild.id not in self.tracks:
                await self.nothing_is_playing_error(ctx)

            tracks, index = self.tracks[ctx.guild.id]["tracks"], self.tracks[ctx.guild.id]["index"]
            if (new_index := index - count) < 0:
                new_index = await self.queue_index_overflow(
                    ctx=ctx,
                    voice_client=voice,
                    default=len(tracks) - 1
                )
            if new_index is not None:
                self.tracks[ctx.guild.id]["index"] = new_index - 1
                voice.stop()

    @commands.command(name="add", aliases=["add_to_queue"])
    @commands.guild_only()
    async def add_to_queue_command(self, ctx: commands.Context, *name, track: Optional[list]):
        await ctx.message.add_reaction("🎧")

        if not ctx.author.voice:
            embed = embed_utils.create_error_embed(
                message="You have to be connected to voice channel"
            )
            await ctx.send(embed=embed, delete_after=5)

            return await ctx.message.add_reaction("❌")

        voice = ctx.voice_client
        if track is None:
            name = " ".join(name)
            try:
                track = await vk_parsing.get_single_audio(name)

            except NoTracksFound:
                embed = embed_utils.create_error_embed(
                    message=f"No tracks founded for you request **{name}**"
                )
                await ctx.send(embed=embed, delete_after=5)

                return await ctx.message.add_reaction("❌")

            except Exception as err:
                print(f"error: {err}")
                embed = embed_utils.create_error_embed(
                    message=f"Unknown error while processing request **{name}**"
                )
                await ctx.send(embed=embed, delete_after=5)

                return await ctx.message.add_reaction("❌")

        if ctx.guild.id not in self.tracks:
            self.tracks[ctx.guild.id] = {"tracks": [track], "index": 0}
        else:
            self.tracks[ctx.guild.id]["tracks"].append(track)

        if not voice or not voice.is_connected() or not (voice.is_paused() or voice.is_playing()):
            await self._join(ctx=ctx)
            voice = ctx.voice_client
            await self.player_command(ctx)

            return voice.play(discord.FFmpegPCMAudio(source=track["url"]),
                              after=lambda x: self.play_next(x, voice, ctx))

        embed = embed_utils.create_music_embed(
            title="Track added to queue",
            description=track["name"]
        )
        await ctx.send(embed=embed, delete_after=5)
        try:
            await self.queue_message_update(ctx)
            await self.player_message_update(ctx)
        except Exception as err:
            print(err)

    @commands.command(name="delete", aliases=["remove"], pass_context=True)
    @commands.guild_only()
    async def delete_command(self, ctx: commands.Context, index: int):
        await ctx.message.add_reaction("💔")
        voice = ctx.voice_client
        if voice is None:
            return
        tracks, now_playing = self.tracks[ctx.guild.id]["tracks"], self.tracks[ctx.guild.id]["index"]

        if (index <= 0) or (index > len(tracks)):
            embed = embed_utils.create_error_embed(
                message="Incorrect index passed"
            )
            await ctx.message.add_reaction("❌")
            return await ctx.send(embed=embed, delete_after=5)
        embed = embed_utils.create_music_embed(
            description=f"Deleting track: {tracks[index - 1]['name']}"
        )
        del tracks[index - 1]
        if index - 1 == now_playing:
            if len(tracks) == 1:
                del self.tracks[ctx.guild.id]
                del self.queue_messages[ctx.guild.id]
            else:
                self.tracks[ctx.guild.id]["index"] = now_playing - 1
            voice = ctx.voice_client
            voice.stop()

        await ctx.message.add_reaction("✔")
        await ctx.send(embed=embed, delete_after=5)

        await self.queue_message_update(ctx)
        await self.player_message_update(ctx)

    @commands.command(name="jump", pass_context=True)
    @commands.guild_only()
    async def jump_command(self, ctx: commands.Context, index: int):
        voice = ctx.voice_client
        if not voice or not voice.is_connected():
            return

        tracks_info = self.tracks[ctx.guild.id]
        tracks = tracks_info["tracks"]
        if (index > len(tracks)) or (index <= 0):
            embed = embed_utils.create_error_embed(
                message=f"Incorrect index passed. Max index is {len(tracks)}"
            )
            await ctx.send(embed=embed, delete_after=5)
            return await ctx.message.add_reaction("✔")
        self.tracks[ctx.guild.id]["index"] = index - 2
        voice.stop()

    @commands.command(name="loop", pass_context=True)
    @commands.guild_only()
    async def loop_command(self, ctx: commands.Context):
        is_looped = functions.get_guild_smf(ctx.guild.id, "loop_queue")
        functions.change_loop_option(ctx.guild.id, not is_looped)
        if ctx.message.author.bot:
            await self.queue_message_update(ctx)
            return
        if is_looped:
            embed = embed_utils.create_info_embed(
                description="Loop option set as False\n"
                            "Queue in your guild is not looped now"
            )
        else:
            embed = embed_utils.create_info_embed(
                description="Loop option set as True\n"
                            "Queue in your guilds is looped now"
            )
        await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="leave", pass_context=True)
    @commands.guild_only()
    async def leave_command(self, ctx: commands.Context):
        await ctx.message.add_reaction("🚪")

        voice = ctx.voice_client
        if voice and voice.is_connected():
            try:
                del self.tracks[ctx.guild.id]
            except KeyError:
                pass
            await self.delete_messages(ctx.guild.id)

            await voice.disconnect()
            await ctx.message.add_reaction("✔")
        else:
            embed = embed_utils.create_error_embed("Not connected to any voice channel")

            await ctx.send(embed=embed, delete_after=5)

            await ctx.message.add_reaction("❌")

    @commands.command(name="search")
    @commands.guild_only()
    async def search_command(self, ctx: commands.Context, *name):
        tracks = []
        name = " ".join(name)
        try:
            tracks = await vk_parsing.get_single_audio(name, 10)
        except NoTracksFound:
            embed = embed_utils.create_error_embed(
                f"No tracks founded for your request {name}"
            )
            return await ctx.send(embed=embed, delete_after=5)

        tracks_str_list = []
        for i, track in enumerate(tracks):
            duration = self._get_duration(track["duration"])
            tracks_str_list.append(f"**{i + 1}. {track['name']}** {duration}")
        description = "\n".join(tracks_str_list)
        embed = embed_utils.create_music_embed(
            description=description,
            footer="Type index of track to add it to queue"
        )
        message = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.message.author \
                   and m.channel == ctx.message.channel \
                   and m.content.isdigit() \
                   and int(m.content) <= len(tracks)

        try:
            msg = await self.client.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            pass
        else:
            track = tracks[int(msg.content) - 1]
            await self.add_to_queue_command(ctx, "", track=track)
        finally:
            await message.delete(delay=5)

    # Auto self deaf
    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState
                                    ):
        voice = member.guild.voice_client
        if member == self.client.user:
            if not after.deaf:
                await member.edit(deafen=True)
            if voice and not voice.is_connected() and after.channel is None:
                try:
                    del self.tracks[member.guild.id]
                except KeyError:
                    pass
        else:
            if before.channel is None:
                return
            members = before.channel.members
            if voice is None:
                return
            if before.channel == member.guild.voice_client.channel:
                if (len(members) == 1) and self.client.user in members:
                    await asyncio.sleep(15)

                    updated_members = voice.channel.members
                    if (len(updated_members) == 1) and self.client.user in updated_members:
                        try:
                            del self.tracks[member.guild.id]
                        except KeyError:
                            pass
                        await self.delete_messages(member.guild.id)
                        await voice.disconnect()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):

        client = self.client
        if reaction.message.author == user:
            return
        ctx = await client.get_context(reaction.message)
        if reaction.message.guild.id in self.player_messages:
            if reaction.message == self.player_messages[ctx.guild.id]:
                if reaction.emoji == "⏪":
                    return await self.prev_command(ctx)

                if reaction.emoji == "▶":
                    voice = ctx.voice_client
                    if voice:
                        if voice.is_playing():
                            return await self.pause_command(ctx)
                        if voice.is_paused():
                            return await self.play_command(ctx)

                if reaction.emoji == "⏩":
                    return await self.skip_command(ctx)

                if reaction.emoji == "⏹":
                    return await self.stop_command(ctx)

                if reaction.emoji == "🔁":
                    return await self.loop_command(ctx)

                if reaction.emoji == "🔀":
                    return await self.shuffle_command(ctx)

                if reaction.emoji == "📑":
                    return await self.queue_command(ctx)

                return

        if reaction.message.guild.id in self.queue_messages:

            if reaction.message == self.queue_messages[ctx.guild.id]["message"]:
                if reaction.emoji == "⬅":
                    page = self.queue_messages[ctx.guild.id]["page"]
                    if page <= 1:
                        return
                    _, pages = self.get_pages(ctx.guild.id, page)
                    embed = self.create_queue_embed(ctx, page - 1)
                    self.queue_messages[ctx.guild.id]["page"] = page - 1
                    return await self.queue_messages[ctx.guild.id]["message"].edit(embed=embed)
                if reaction.emoji == "➡":
                    page = self.queue_messages[ctx.guild.id]["page"]
                    _, pages = self.get_pages(ctx.guild.id, page)
                    if pages < 2 or page == pages:
                        return
                    embed = self.create_queue_embed(ctx, page + 1)
                    self.queue_messages[ctx.guild.id]["page"] = page + 1
                    await self.queue_messages[ctx.guild.id]["message"].edit(embed=embed)


def setup(client):
    client.add_cog(Player(client))
