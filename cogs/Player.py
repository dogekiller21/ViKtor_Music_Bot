import asyncio
import datetime
import traceback
from random import shuffle
from typing import Optional

import discord
from discord import NotFound

from discord.ext import commands

import functions
import vk_parsing
from utils import embed_utils, playlists_utils
from utils.custom_exceptions import NoTracksFound, EmptyQueue, NoVoiceClient, IncorrectVoiceChannel, ToManyPlaylists, \
    NoGuildPlaylists, PlaylistNotFound


class Player(commands.Cog):
    """Команды, связанные с проигрыванием музыки
    """

    def __init__(self, client):
        self.client = client
        self.tracks = {}
        self.queue_messages = {}
        self.player_messages = {}
        self.loop = self.client.loop

    async def nothing_is_playing_error(self, ctx: commands.Context):
        if ctx.author.bot:
            return
        embed = embed_utils.create_error_embed("Ничего не играет")
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

    def get_requester(self, track: dict):
        if ("requester" not in track) or track["requester"] is None:
            return
        user = self.client.get_user(track["requester"])
        if user is not None:
            return {"text": user.display_name,
                    "icon_url": user.avatar_url}
        return {"text": "Неизвестный пользователь",
                "icon_url": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png"}

    def create_player_embed(self, ctx: commands.Context):
        length = len(self.tracks[ctx.guild.id]["tracks"])

        now_playing = self.tracks[ctx.guild.id]["index"]
        tracks = self.tracks[ctx.guild.id]["tracks"]
        prev_index, next_index = now_playing - 1, now_playing + 1

        embed = embed_utils.create_music_embed(
            title=f"Плеер в канале \"{ctx.voice_client.channel.name}\"",
            description=f"`Треков в очереди: {length}`\n"
                        f"{self._get_loop_str_min(ctx.guild.id)}"
        )
        requester = self.get_requester(tracks[now_playing])
        if requester is not None:
            embed.set_footer(**requester)
        if prev_index >= 0:
            dur = self._get_duration(tracks[prev_index]["duration"])
            embed.add_field(name="Предыдущий трек",
                            value=f"**{prev_index + 1}. {tracks[prev_index]['name']}** {dur}\n",
                            inline=False)

        voice = ctx.voice_client
        title = "⟶ Приостановлен ⟵" if voice.is_paused() else "⟶ Сейчас играет ⟵"

        dur = self._get_duration(tracks[now_playing]["duration"])
        embed.add_field(
            name=title,
            value=f"**{now_playing + 1}. {tracks[now_playing]['name']}** {dur}",
            inline=False
        )

        if next_index < len(tracks):
            dur = self._get_duration(tracks[next_index]["duration"])
            embed.add_field(name="Следующий трек",
                            value=f"\n**{next_index + 1}. {tracks[next_index]['name']}** {dur}",
                            inline=False)

        embed.set_thumbnail(url=tracks[now_playing]["thumb"])
        return embed

    # Loop settings in string format for embed footer
    def _get_loop_str(self, guild_id):
        loop_settings = functions.get_guild_smf(guild_id, "loop_queue")
        cliche = "Зацикливание очереди **{}**"
        if loop_settings:
            return cliche.format("включено")
        return cliche.format("выключено")

    def _get_loop_str_min(self, guild_id):
        loop_settings = functions.get_guild_smf(guild_id, "loop_queue")
        cliche = "Зацикливание **{}**"
        if loop_settings:
            return cliche.format("вкл")
        return cliche.format("выкл")

    # Queue embed
    def create_queue_embed(self, ctx: commands.Context, page: Optional[int] = None):
        if ctx.guild.id not in self.tracks:
            raise EmptyQueue
        voice = ctx.voice_client
        if voice.is_paused():
            paused = True
        else:
            paused = False
        page, pages = self.get_pages(ctx.guild.id, page)
        tracks = self.tracks[ctx.guild.id]["tracks"]
        now_playing = self.tracks[ctx.guild.id]["index"]

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
                    tracks_to_str[-1] += "\n↑ приостановлен ↑"
                else:
                    tracks_to_str[-1] += "\n↑ сейчас играет ↑"

        if (len(tracks)) > 10:
            pages = f"Страница: {page} / {pages}"
        else:
            pages = None

        embed = embed_utils.create_music_embed(
            description="\n\n".join(tracks_to_str),
            footer=pages
        )
        return embed

    async def queue_message_update(self, ctx):
        """
        Update queue and player messages
        """
        if ctx.guild.id not in self.tracks:
            return
        if ctx.guild.id not in self.queue_messages:
            return
        page, _ = self.get_pages(ctx.guild.id)
        if page != (now_page := self.queue_messages[ctx.guild.id]["page"]):
            now_page = None
        try:
            embed = self.create_queue_embed(ctx, page=now_page)
        except EmptyQueue:
            return

        try:
            await self.queue_messages[ctx.guild.id]["message"].edit(embed=embed)
        except NotFound:
            return

    async def player_message_update(self, ctx):
        if ctx.guild.id not in self.tracks:
            return
        if ctx.guild.id not in self.player_messages:
            return
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
        """
        Invoke if index of next track to play is out of queue range

        :return: Union[int, None]
        """
        is_looping = functions.get_guild_smf(ctx.guild.id, "loop_queue")
        if is_looping:
            return default

        embed = embed_utils.create_info_embed(
            description="Зацикливание очереди выключено в вашей гильдии\n"
                        "Удаляю очередь"
        )
        await ctx.send(embed=embed, delete_after=5)

        del self.tracks[ctx.guild.id]

        await self.delete_messages(ctx.guild.id)

        await self._stop(voice_client)

    async def _stop(self, voice: discord.VoiceClient, force=True):
        """
        ...VoiceClient.stop() with leave timer

        :param voice: discord.VoiceClient
        :param force: bool
        """
        voice.stop()
        if not force:
            return
        await asyncio.sleep(120)
        if voice.guild.id not in self.tracks:
            await self._leaving(voice, voice.guild.id)

    async def _join(self, ctx: commands.Context):
        """
        Func for joining user's channel
        """
        user_channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(user_channel)
        else:
            await user_channel.connect()

    def play_next(self, error, voice, ctx):
        """
        Callable for invoking after track stops
        """
        if error is not None:
            print(f"next play error: {error}")
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
        voice.play(discord.FFmpegPCMAudio(source=tracks[new_index]["url"]),
                   after=lambda err: self.play_next(err, voice, ctx))
        self.tracks[ctx.guild.id]["index"] = new_index

        asyncio.run_coroutine_threadsafe(self.player_message_update(ctx), self.loop)
        asyncio.run_coroutine_threadsafe(self.queue_message_update(ctx), self.loop)

    async def delete_messages(self, guild_id):
        """
        Delete queue and player messages for guild
        """
        try:
            await self.queue_messages[guild_id]["message"].delete(delay=2)
            del self.queue_messages[guild_id]
        except (NotFound, KeyError):
            pass
        try:
            await self.player_messages[guild_id].delete(delay=2)
            del self.player_messages[guild_id]
        except (NotFound, KeyError):
            pass

    @commands.command(name="player")
    @commands.guild_only()
    async def player_command(self, ctx: commands.Context):
        """Вызов плеера для текущей гильдии"""
        if ctx.guild.id not in self.tracks:
            await self.nothing_is_playing_error(ctx)
            return
        embed = self.create_player_embed(ctx)
        player_message = await ctx.send(embed=embed)
        if ctx.guild.id in self.player_messages:
            await self.player_messages[ctx.guild.id].delete(delay=2)
        self.player_messages[ctx.guild.id] = player_message
        emoji_list = ["🔀", "⏪", "▶", "⏩", "⏹", "🔁", "📑"]
        for emoji in emoji_list:
            await player_message.add_reaction(emoji)

    def _get_playlists_message(self, ctx):
        playlists = playlists_utils.get_single_guild_playlist(ctx.guild.id)
        desc = f"`Всего плейлистов: {len(playlists)}`"
        embed = embed_utils.create_music_embed(
            # title=f"Плейлисты в вашей гильдии \"{ctx.guild.name}\"",
            title="Доступные плейлисты",
            description=desc
        )
        for key in playlists:
            playlist = playlists[key]
            date = datetime.date.fromordinal(playlist["date"])
            date = date.strftime("%d-%m-%Y")
            embed.add_field(
                name=f"{key}",
                value=f"`Треков: {len(playlist['tracks'])}`\n"
                      f"`Дата создания: {date}`",
                inline=False
            )
        embed.set_footer(text="Используйте эту команду с названием плейлиста для проигрывания")
        return embed

    @commands.command(name="playlist")
    @commands.guild_only()
    async def playlist_command(self, ctx: commands.Context, *name):
        playlists = playlists_utils.get_single_guild_playlist(ctx.guild.id)
        if playlists is None:
            embed = embed_utils.create_error_embed(
                message="В вашей гильдии еще нет плейлистов\n"
                        "Используйте команду `save` для сохранения очереди в плейлист"
            )
            await ctx.send(embed=embed)
            return
        if len(name) == 0:
            embed = self._get_playlists_message(ctx)
            await ctx.send(embed=embed)
            return
        name = " ".join(name)
        if name not in playlists:
            embed = embed_utils.create_error_embed(
                message=f"Не найдено плейлиста с названием {name}"
            )
            await ctx.send(embed=embed)
            return

        voice = ctx.voice_client
        if voice is None:
            await self._join(ctx)
            voice = ctx.voice_client
        if voice.is_playing() or voice.is_paused():
            del self.tracks[ctx.guild.id]

            await self.delete_messages(ctx.guild.id)

            await self._stop(voice, force=False)
        tracks = playlists[name]["tracks"]
        id_list = []
        for track in tracks:
            id_list.append(track["id"])
        new_tracks = await vk_parsing.get_tracks_by_id(id_list)
        self.tracks[ctx.guild.id] = {"tracks": new_tracks, "index": 0}

        voice.play(discord.FFmpegPCMAudio(source=new_tracks[0]["url"]),
                   after=lambda x: self.play_next(x, voice, ctx))
        await self.player_command(ctx)

    @commands.command(name="play", aliases=["p"])
    @commands.guild_only()
    async def play_command(self, ctx: commands.Context, *link: Optional[str]):
        """Команда для проигрывания треков и плейлистов
        Если команда написана без аргументов после, бот попытается востановить проигрывание"""

        if (len(link) > 0) and "vk.com/" not in link[0]:
            await self.add_to_queue_command(ctx, *link, track=None)
            return

        voice = ctx.voice_client

        if not voice and (len(link) == 0):
            embed = embed_utils.create_error_embed(
                message="Добавьте ссылку или имя трека к команде"
            )
            await ctx.message.add_reaction("❌")
            await ctx.send(embed=embed, delete_after=5)
            return

        if not voice or not voice.is_connected():
            await self._join(ctx)
            voice = ctx.voice_client
        elif (len(link) == 0) and not (voice.is_playing() or voice.is_paused()):
            await self.nothing_is_playing_error(ctx)
            return

        elif (voice.is_playing() or voice.is_paused()) and (len(link) != 0):
            del self.tracks[ctx.guild.id]

            await self.delete_messages(ctx.guild.id)

            await self._stop(voice, force=False)

        elif voice.is_paused():
            voice.resume()
            await self.player_message_update(ctx)
            await self.queue_message_update(ctx)
            return

        elif voice.is_playing():
            if len(link) == 0:
                return
            await self._stop(voice, force=False)

        link = link[0]
        tracks = await vk_parsing.get_audio(link, requester=ctx.author.id)
        self.tracks[ctx.guild.id] = {"tracks": tracks, "index": 0}

        voice.play(discord.FFmpegPCMAudio(source=tracks[0]["url"]),
                   after=lambda x: self.play_next(x, voice, ctx))

        await self.player_command(ctx)

    @commands.command(name="pause")
    @commands.guild_only()
    async def pause_command(self, ctx: commands.Context):
        """Приостановить проигрывание"""
        voice = ctx.voice_client
        if not voice.is_playing():
            return
        voice.pause()
        await self.player_message_update(ctx)
        await self.queue_message_update(ctx)

    @commands.command(name="stop")
    @commands.guild_only()
    async def stop_command(self, ctx: commands.Context):
        """Полностью останавливает проигрывание треков в гильдии, очищает очередь.
        Если бот не будет проигрывать ничего в течении 2х минут, он обидится и уйдет"""
        if (voice := ctx.voice_client) is None:
            return

        if not (voice.is_playing() or voice.is_paused()):
            raise NoVoiceClient
        if voice.is_connected():
            del self.tracks[ctx.guild.id]
            await self.delete_messages(ctx.guild.id)

            await self._stop(voice)

    @commands.command(name="queue")
    @commands.guild_only()
    async def queue_command(self, ctx: commands.Context, *, page: Optional[int] = None):
        """Вызвать сообщение с текущей очередью проигрывания.
        Есть возможность в ручную выбирать страницы, если добавить к команде номер
        Если номер страницы не был выбран, страница будет выбрана как текущая для проигрываемого трека"""
        if ctx.message.author != self.client.user:
            await ctx.message.add_reaction("📄")

        page, pages = self.get_pages(ctx.guild.id, page)

        if page > pages:
            embed = embed_utils.create_error_embed("Нет такой страницы")
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
        """Перемешать треки в очереди"""
        voice = ctx.voice_client
        if voice.is_playing() or voice.is_paused():
            tracks = self.tracks[ctx.guild.id]["tracks"]
            if len(tracks) == 1:
                return
            shuffle(tracks)
            self.tracks[ctx.guild.id] = {"tracks": tracks, "index": - 1}
            try:
                self.queue_messages[ctx.guild.id]["page"] = 1
            except KeyError:
                pass
            await self._stop(voice, force=False)

    @commands.command(name="skip", aliases=["sk"])
    @commands.guild_only()
    async def skip_command(self, ctx: commands.Context, *, count: Optional[int] = 1):
        """Пропустить один или несколько треков.
        Чтобы пропустить несколько треков необходимо добавить число к команде"""
        voice = ctx.voice_client

        if ctx.guild.id not in self.tracks:
            return

        tracks_info = self.tracks[ctx.guild.id]

        tracks, index = tracks_info["tracks"], tracks_info["index"]
        if (new_index := index + count) > len(tracks) - 1:
            new_index = await self.queue_index_overflow(
                ctx=ctx,
                voice_client=voice,
                default=0
            )
        if new_index is not None:
            self.tracks[ctx.guild.id]["index"] = new_index - 1
            await self._stop(voice, force=False)

    @commands.command(name="prev", aliases=["pr"],
                      help="Вернуться к прошлому треку")
    @commands.guild_only()
    async def prev_command(self, ctx: commands.Context, *, count: Optional[int] = 1):
        """Вернуться на один или несколько треков назад.
        Про количество смотрите в команде **skip**"""
        voice = ctx.voice_client

        if ctx.guild.id not in self.tracks:
            return

        tracks, index = self.tracks[ctx.guild.id]["tracks"], self.tracks[ctx.guild.id]["index"]
        if (new_index := index - count) < 0:
            new_index = await self.queue_index_overflow(
                ctx=ctx,
                voice_client=voice,
                default=len(tracks) - 1
            )
        if new_index is not None:
            self.tracks[ctx.guild.id]["index"] = new_index - 1
            await self._stop(voice, force=False)

    @commands.command(name="add", aliases=["add_to_queue"])
    @commands.guild_only()
    async def add_to_queue_command(self, ctx: commands.Context, *name, track: Optional[list]):
        """Добавить первый трек из поиска ВКонтакте в плейлист.
        Работает точно также, как и команда **play** с переданным туда именем трека"""
        await ctx.message.add_reaction("🎧")

        voice = ctx.voice_client
        if track is None:
            name = " ".join(name)
            try:
                track = await vk_parsing.get_single_audio(requester=ctx.author.id, name=name)

            except NoTracksFound:
                embed = embed_utils.create_error_embed(
                    message=f"Не найдено треков по вашему запросу: **{name}**"
                )
                await ctx.send(embed=embed, delete_after=5)

                return await ctx.message.add_reaction("❌")

            except Exception as err:
                print(f"error: {err}")
                embed = embed_utils.create_error_embed(
                    message=f"Неизвестная ошибка во время обработки запроса **({name})**"
                )
                await ctx.send(embed=embed, delete_after=5)

                return await ctx.message.add_reaction("❌")

        if ctx.guild.id not in self.tracks:
            self.tracks[ctx.guild.id] = {"tracks": [track], "index": 0}
        else:
            self.tracks[ctx.guild.id]["tracks"].append(track)

        if not voice or not (voice.is_paused() or voice.is_playing()):
            await self._join(ctx=ctx)
            voice = ctx.voice_client

            voice.play(discord.FFmpegPCMAudio(source=track["url"]),
                       after=lambda x: self.play_next(x, voice, ctx))
            await self.player_command(ctx)
            return

        embed = embed_utils.create_music_embed(
            title="Трек добавлен в очередь",
            description=track["name"]
        )
        await ctx.send(embed=embed, delete_after=5)
        try:
            await self.queue_message_update(ctx)
            await self.player_message_update(ctx)
        except Exception as err:
            print(err)

    @commands.command(name="delete", aliases=["remove", "d"], pass_context=True)
    @commands.guild_only()
    async def delete_command(self, ctx: commands.Context, index: int):
        """Удалить трек под номером, который вы скажете боту, из очереди"""
        await ctx.message.add_reaction("💔")
        voice = ctx.voice_client
        tracks, now_playing = self.tracks[ctx.guild.id]["tracks"], self.tracks[ctx.guild.id]["index"]

        if (index <= 0) or (index > len(tracks)):
            embed = embed_utils.create_error_embed(
                message="Некорректный индекс"
            )
            await ctx.message.add_reaction("❌")
            await ctx.send(embed=embed, delete_after=5)
            return
        embed = embed_utils.create_music_embed(
            description=f"Удаляю трек: **{tracks[index - 1]['name']}**"
        )
        queue_len = len(tracks)
        del tracks[index - 1]
        await ctx.message.add_reaction("✔")
        await ctx.send(embed=embed, delete_after=5)
        if index - 1 == now_playing:
            if queue_len == 1:
                await self.delete_messages(ctx.guild.id)
            else:
                self.tracks[ctx.guild.id]["index"] = now_playing - 1
            await self._stop(voice, force=False)
            return

        await self.queue_message_update(ctx)
        await self.player_message_update(ctx)

    @commands.command(name="jump", aliases=["j"], pass_context=True)
    @commands.guild_only()
    async def jump_command(self, ctx: commands.Context, index: int):
        """Перепрыгнуть на определенный трек под номером, который вы скажете боту в команде"""
        voice = ctx.voice_client

        tracks_info = self.tracks[ctx.guild.id]
        tracks = tracks_info["tracks"]
        if (index > len(tracks)) or (index <= 0):
            embed = embed_utils.create_error_embed(
                message=f"Некорректный индекс. Максимальный - {len(tracks)}"
            )
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.add_reaction("✔")
            return
        self.tracks[ctx.guild.id]["index"] = index - 2
        await self._stop(voice, force=False)

    @commands.command(name="loop", pass_context=True)
    @commands.guild_only()
    async def loop_command(self, ctx: commands.Context):
        """Изменить настройки зацикливания очереди"""
        is_looped = functions.get_guild_smf(ctx.guild.id, "loop_queue")
        functions.change_loop_option(ctx.guild.id, not is_looped)
        if ctx.message.author.bot:
            await self.player_message_update(ctx)
            return
        cliche = "Зацикливание очереди {} для вашей гильдии"
        if is_looped:
            embed = embed_utils.create_info_embed(
                description=cliche.format("отключено")
            )
        else:
            embed = embed_utils.create_info_embed(
                description=cliche.format("включено")
            )
        await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="leave", pass_context=True)
    @commands.guild_only()
    async def leave_command(self, ctx: commands.Context):
        """Прогнать бота (останавливает прослушивание и очищает очередь)"""
        await ctx.message.add_reaction("🚪")

        voice = ctx.voice_client
        if voice.is_connected():
            try:
                del self.tracks[ctx.guild.id]
            except KeyError:
                pass
            await self.delete_messages(ctx.guild.id)

            await voice.disconnect()
            await ctx.message.add_reaction("✔")

    @commands.command(name="search", aliases=["s"])
    @commands.guild_only()
    async def search_command(self, ctx: commands.Context, *name):
        """Найти трек. Бот любезно предложит выбрать вам из 10ти(максимум) найденных треков один для проигрывания"""
        tracks = []
        name = " ".join(name)
        try:
            tracks = await vk_parsing.get_single_audio(requester=ctx.author.id, name=name, count=10)
        except NoTracksFound:
            embed = embed_utils.create_error_embed(
                f"Не найдено треков по вашему запросу: **{name}**"
            )
            return await ctx.send(embed=embed, delete_after=5)

        tracks_str_list = []
        for i, track in enumerate(tracks):
            duration = self._get_duration(track["duration"])
            tracks_str_list.append(f"**{i + 1}. {track['name']}** {duration}")
        description = "\n".join(tracks_str_list)
        before_command = "!"
        if ctx.prefix == before_command:
            before_command = "&"
        embed = embed_utils.create_music_embed(
            description=description,
            footer=f"Напишите индекс трека для добавление в очередь\n"
                   f"{before_command}c для отмены"
        )
        message = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.message.author \
                   and m.channel == ctx.message.channel \
                   and ((m.content.isdigit() and int(m.content) <= len(tracks)) or
                        m.content == f"{before_command}c")

        try:
            msg = await self.client.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            pass
        else:
            if msg.content == f"{before_command}c":
                await ctx.send(embed=embed_utils.create_info_embed(
                    description="Отменяем"), delete_after=5)
                return
            track = tracks[int(msg.content) - 1]
            await self.add_to_queue_command(ctx, "", track=track)
        finally:
            await message.delete(delay=5)

    @commands.command(name="save")
    @commands.guild_only()
    async def save_playlist_command(self, ctx: commands.Context, *name):
        """Сохранить текущий плейлист"""
        if ctx.guild.id not in self.tracks:
            embed = embed_utils.create_error_embed(
                message="Нет треков в очереди"
            )
            await ctx.send(embed=embed)
            return
        playlist = self.tracks[ctx.guild.id]["tracks"]
        if len(name) == 0:
            name = None
        else:
            name = " ".join(name).strip()
        try:
            playlist_name = playlists_utils.save_new_playlist(ctx.guild.id, playlist, name)
            embed = embed_utils.create_music_embed(
                title="Плейлист сохранен",
                description=f"Название: `{playlist_name}`"
            )
            await ctx.send(embed=embed)
        except ToManyPlaylists:
            embed = embed_utils.create_error_embed(
                message="В вашей гильдии сохранено слишком много плейлистов\n"
                        "Максимальное кол-во: `10`"
            )
            await ctx.send(embed=embed)

    async def _check_for_playlist(self, _callable, args, after, ctx):
        playlist_name = args[1]
        try:
            _callable(*args)
        except NoGuildPlaylists:
            embed = embed_utils.create_error_embed(
                message="В вашей гильдии еще нет плейлистов\n"
                        "Используйте команду `save` для сохранения очереди в плейлист"
            )
            await ctx.send(embed=embed)
        except PlaylistNotFound:
            embed = embed_utils.create_error_embed(
                message=f"Не найдено плейлиста по запросу: `{playlist_name}`"
            )
            await ctx.send(embed=embed)
        else:
            await after()

    @commands.command(name="rename")
    @commands.guild_only()
    async def rename_playlist_command(self, ctx: commands.Context, *names):
        """Переименовать плейлист.
        Новое и старое название плейлистов должны быть разделены /
        Пример: **-rename old_playlist_name / new_playlist_name**"""
        if (len(names) == 0) or "/" not in names:
            embed = embed_utils.create_error_embed(
                message="Старое и новое названия плейлиста должны быть разделены символом `/`"
            )
            await ctx.send(embed=embed)
            return
        old_name, new_name = " ".join(names).split("/")
        old_name = old_name.strip()
        new_name = new_name.strip()

        async def after():
            _embed = embed_utils.create_music_embed(
                description=f"Название плейлиста `{old_name}` изменено на `{new_name}`"
            )
            await ctx.send(embed=_embed)
        await self._check_for_playlist(playlists_utils.rename_playlist,
                                       [ctx.guild.id, old_name, new_name],
                                       after, ctx)

    @commands.command(name="del_playlist")
    @commands.guild_only()
    async def delete_playlist_command(self, ctx: commands.Context, *playlist_name):
        if len(playlist_name) == 0:
            embed = embed_utils.create_error_embed(
                message="Добавьте название плейлиста к этой команде для удаления"
            )
            await ctx.send(embed=embed)
            return
        playlist_name = " ".join(playlist_name).strip()

        async def after():
            _embed = embed_utils.create_music_embed(
                description=f"Плейлист с названием **{playlist_name}** удален"
            )
            await ctx.send(embed=_embed)

        await self._check_for_playlist(
            playlists_utils.delete_playlist,
            [ctx.guild.id, playlist_name],
            after, ctx
        )

    async def _leaving(self, voice: discord.VoiceClient, guild_id):
        """
        Clear info and leave from voice channel
        """
        try:
            del self.tracks[guild_id]
        except KeyError:
            pass
        await self.delete_messages(guild_id)
        await voice.disconnect()

    @player_command.before_invoke
    @pause_command.before_invoke
    @queue_command.before_invoke
    @jump_command.before_invoke
    @leave_command.before_invoke
    async def _check_voice(self, ctx: commands.Context):
        voice = ctx.voice_client
        if voice is None:
            raise NoVoiceClient

    @play_command.before_invoke
    @add_to_queue_command.before_invoke
    @search_command.before_invoke
    @playlist_command.before_invoke
    async def _check_member_voice(self, ctx: commands.Context):
        if ctx.voice_client is not None:
            return
        if not ctx.author.voice:
            raise IncorrectVoiceChannel

    async def cog_command_error(self, ctx: commands.Context, error):
        voice_client_needed = ["player", "pause", "queue", "jump", "leave"]
        member_voice_needed = ["play", "add", "search", "playlist"]
        if ctx.command.name in voice_client_needed:
            if isinstance(error, NoVoiceClient):
                embed = embed_utils.create_error_embed(
                    message="Ничего не играет :(\n"
                            "Используйте команду `play` или `search`"
                )
                await ctx.send(embed=embed)
                return
        if ctx.command.name in member_voice_needed:
            if isinstance(error, IncorrectVoiceChannel):
                embed = embed_utils.create_error_embed(
                    message="Вы должны быть подключены к голосовому каналу"
                )
                await ctx.send(embed=embed)
                return
        traceback.print_exc()

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
            if after.mute:
                await member.edit(mute=False)
            if voice and not voice.is_connected() and after.channel is None:
                try:
                    del self.tracks[member.guild.id]
                    await self._stop(voice, force=True)
                except KeyError:
                    pass
                finally:
                    return

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
                    return await self._leaving(voice, member.guild.id)

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
