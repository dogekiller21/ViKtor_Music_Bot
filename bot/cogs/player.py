import asyncio
from random import shuffle
from typing import Optional, Union

import discord
from discord import NotFound

from discord.ext import commands
from discord.ext.commands import Bot
from discord_slash import cog_ext, SlashContext, ComponentContext
from discord_slash.utils.manage_components import (
    create_select_option,
    create_select,
    create_actionrow,
    wait_for_component,
)

from bot import vk_parsing, functions
from .constants import VK_URL_PREFIX, FFMPEG_OPTIONS, TIMEOUT_OPTION
from .player_storage import QueueMessagesStorage, TracksStorage
from .player_storage.player import PlayerStorage
from ..events.components_events import player_components, queue_components
from ..utils import playlists_utils, embed_utils, player_msg_utils
from ..utils.checks import check_user_voice, check_self_voice
from ..utils.custom_exceptions import (
    NoGuildPlaylists,
    PlaylistNotFound,
)


class Player(commands.Cog):
    """Команды, связанные с проигрыванием музыки"""

    def __init__(self, client: Bot):
        self.client = client
        self.tracks = TracksStorage()
        self.queue_messages = QueueMessagesStorage(tracks=self.tracks)
        self.player_messages = PlayerStorage(queue_messages=self.queue_messages, client=self.client)
        self.loop = self.client.loop

    async def nothing_is_playing_error(self, ctx: commands.Context):
        if ctx.author.bot:
            return
        embed = embed_utils.create_error_embed("Ничего не играет")
        await ctx.send(embed=embed, delete_after=5)

    async def queue_index_overflow(
            self, ctx: commands.Context, voice_client: discord.VoiceClient, default: int
    ) -> Optional[int]:
        """
        Invoke if index of next track to play is out of queue range
        """
        is_looping = functions.get_guild_data(ctx.guild, "loop_queue")
        if is_looping:
            return default

        embed = embed_utils.create_info_embed(
            description="Зацикливание очереди выключено в вашей гильдии\n"
                        "Удаляю очередь"
        )
        await ctx.send(embed=embed, delete_after=5)

        del self.tracks[ctx.guild.id]

        await self.player_messages.delete_messages(ctx.guild.id, delay=7)

        await self._stop(voice_client)

    async def _stop(self, voice, force: bool = True) -> None:
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
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(user_channel)
        else:
            await user_channel.connect()
        return ctx.voice_client

    def play_next(self, error, voice, ctx):
        """
        Callable for invoking after track stops
        """
        if error is not None:
            print(f"next play error: {error}")  # TODO логгирование

        tracks_info = self.tracks.get(ctx.guild.id)
        if tracks_info is None:
            return
        tracks, now_playing = tracks_info["tracks"], tracks_info["index"]

        if (new_index := now_playing + 1) > len(tracks) - 1:
            args = {"ctx": ctx, "voice_client": voice, "default": 0}
            new_index = asyncio.run_coroutine_threadsafe(
                self.queue_index_overflow(**args), self.loop
            ).result()
        if new_index is None:
            return
        source = asyncio.run_coroutine_threadsafe(
            discord.FFmpegOpusAudio.from_probe(
                source=tracks[new_index]["url"], **FFMPEG_OPTIONS
            ),
            self.loop,
        ).result()
        voice.play(
            source=source,
            after=lambda err: self.play_next(err, voice, ctx),
        )
        self.tracks[ctx.guild.id]["index"] = new_index

        asyncio.run_coroutine_threadsafe(self.player_messages.update_messages(ctx), self.loop)

    @cog_ext.cog_slash(
        name="player",
        description="Вызов плеера для текущей гильдии",
    )
    async def player_command(self, ctx: Union[SlashContext, commands.Context]) -> None:
        """Вызов плеера для текущей гильдии"""
        if ctx.guild.id not in self.tracks:
            await self.nothing_is_playing_error(ctx)
            return
        embed = self.player_messages.create_player_embed(ctx)
        player_message = await ctx.send(embed=embed, components=player_components)
        if ctx.guild.id in self.player_messages:
            await self.player_messages[ctx.guild.id].delete(delay=2)
        self.player_messages[ctx.guild.id] = player_message

    @cog_ext.cog_slash(
        name="playlist",
        description="Просмотреть плейлисты или начать играть один из них",
        options=[{"name": "playlist_name", "description": "Имя плейлиста", "type": 3}],
    )
    async def playlist_command(
            self, ctx: SlashContext, playlist_name: Optional[str] = None
    ) -> None:
        playlists = playlists_utils.get_single_guild_playlist(ctx.guild.id)
        if playlists is None:
            embed = embed_utils.create_error_embed(
                message="В вашей гильдии еще нет плейлистов\n"
                        "Используйте команду `/save` для сохранения очереди в плейлист"
            )
            await ctx.send(embed=embed)
            return
        if playlist_name is None:
            embed = playlists_utils.get_playlists_message(ctx)
            await ctx.send(embed=embed)
            return
        if playlist_name not in playlists:
            embed = embed_utils.create_error_embed(
                message=f"Не найдено плейлиста с названием {playlist_name}"
            )
            await ctx.send(embed=embed)
            return

        await ctx.defer()
        tracks = playlists[playlist_name]["tracks"]
        id_list = []
        for track in tracks:
            id_list.append(track["id"])
        new_tracks = await vk_parsing.get_tracks_by_id(id_list)
        await self._add_tracks_to_queue(ctx=ctx, tracks=new_tracks)

    @cog_ext.cog_subcommand(
        base="play",
        name="link",
        description="Проигрывание плейлиста по ссылке",
        options=[
            {
                "name": "link",
                "description": "Ссылка на плейлист",
                "required": True,
                "type": 3,
            }
        ],
    )
    async def play_link_command(self, ctx: SlashContext, link: str):
        if VK_URL_PREFIX not in link:
            embed = embed_utils.create_error_embed("Некорректная ссылка")
            await ctx.send(embed=embed)
            return
        tracks = await vk_parsing.get_audio(link, requester=ctx.author.id)
        await self._add_tracks_to_queue(ctx=ctx, tracks=tracks)

    async def _select_options_parser(
            self, ctx: SlashContext, select: dict, msg_content: str, timeout: int = 60
    ):
        """
        Возвращает номер выбранного пользователем элемента в селекте
        :return: int
        """
        component = create_actionrow(select)

        message = await ctx.send(content=msg_content, components=[component])
        try:
            component_ctx: ComponentContext = await wait_for_component(
                self.client, components=component, timeout=timeout
            )
        except asyncio.TimeoutError:
            select["options"].append(TIMEOUT_OPTION)
        else:

            selected_value = int(component_ctx.selected_options[0])

            select["options"][selected_value]["default"] = True
            return selected_value
        finally:
            select["disabled"] = True
            new_component = create_actionrow(select)
            try:
                await message.edit(components=[new_component])
            except NotFound:
                pass

    @cog_ext.cog_subcommand(
        base="play",
        name="request",
        description="Проигрывание трека",
        options=[
            {
                "name": "request",
                "description": "Название трека",
                "required": True,
                "type": 3,
            }
        ],
    )
    async def play_request_command(self, ctx: SlashContext, request: str):
        tracks = await player_msg_utils.get_tracks_by_name(ctx=ctx, name=request, count=25)
        if tracks is None:
            return

        tracks_options = []
        for i, track in enumerate(tracks):
            duration = player_msg_utils.get_duration(track["duration"])
            name = f"{track['name']}"
            if len(name) > 50:
                name = f"{name[:50]} ..."
            tracks_options.append(
                create_select_option(
                    label=f"{name}",
                    description=f"{name} ({duration})",
                    value=str(i),
                    emoji="🎵",
                )
            )

        tracks_select = create_select(
            options=tracks_options,
            placeholder="Выберите трек для добавления в очередь",
            min_values=1,
        )
        content = "Выберите трек для добавления в очередь"
        selected_value = await self._select_options_parser(ctx, tracks_select, content)
        if selected_value is None:
            return
        selected_track = tracks[selected_value]
        await self._add_tracks_to_queue(ctx, tracks=[selected_track])

    @cog_ext.cog_subcommand(
        base="play",
        name="playlist",
        description="Поиск плейлиста для проигрывания",
        options=[
            {
                "name": "playlist_name",
                "description": "Имя плейлиста",
                "required": True,
                "type": 3,
            }
        ],
    )
    async def play_playlist_command(self, ctx: SlashContext, playlist_name):
        playlists = await vk_parsing.get_playlists_by_name(playlist_name)
        if playlists is None:
            return
        playlists_options = []
        for i, playlist in enumerate(playlists):
            playlists_options.append(
                create_select_option(
                    label=playlist["title"],
                    description=playlist["description"],
                    value=str(i),
                    emoji="🎶",
                )
            )

        playlist_select = create_select(
            options=playlists_options,
            placeholder="Выберите плейлист для добавления в очередь",
            min_values=1,
        )

        content = "Выберите плейлист для добавления в очередь"
        selected_value = await self._select_options_parser(
            ctx, playlist_select, content
        )
        if selected_value is None:
            return
        selected_playlist = playlists[selected_value]
        tracks = await vk_parsing.get_playlist_tracks(selected_playlist)
        await self._add_tracks_to_queue(ctx, tracks)

    @cog_ext.cog_subcommand(
        base="play",
        name="user_saved",
        description="Проигрывание сохраненных треков пользователя",
        options=[
            {
                "name": "user_link",
                "description": "Ссылка на пользователя",
                "required": True,
                "type": 3,
            }
        ],
    )
    async def play_user_saved_command(self, ctx, user_link: str):
        if "vk.com/" not in user_link:
            embed = embed_utils.create_error_embed("Некорректная ссылка")
            await ctx.send(embed=embed)
            return
        await ctx.defer()
        user = user_link.split("vk.com/")[1]
        tracks = await vk_parsing.get_user_saved_tracks(user, requester=ctx.author.id)
        if tracks is None:
            embed = embed_utils.create_error_embed(
                "Некорректный пользователь\n"
                "Либо у данного пользователя закрыта страница / аудиозаписи"
            )
            await ctx.send(embed=embed)
            return
        await self._add_tracks_to_queue(ctx, tracks)

    @cog_ext.cog_slash(
        name="pause",
        description="Приостановить проигрывание"
    )
    async def pause_command(self, ctx) -> None:
        """Приостановить проигрывание"""
        voice = ctx.voice_client
        if not voice.is_playing():
            return
        voice.pause()
        await self.player_messages.update_messages(ctx)
        if not isinstance(ctx, ComponentContext):
            embed = embed_utils.create_music_embed(description="Пауза")
            await ctx.send(embed=embed, delete_after=3)

    @cog_ext.cog_slash(
        name="resume",
        description="Снять с паузы"
    )
    async def resume_command(self, ctx):
        voice = ctx.voice_client
        if voice.is_paused():
            voice.resume()
        await self.player_messages.update_messages(ctx)
        if not isinstance(ctx, ComponentContext):
            embed = embed_utils.create_music_embed(description="Продолжаем слушать")
            await ctx.send(embed=embed, delete_after=3)

    @cog_ext.cog_slash(
        name="stop",
        description="Полностью останавить проигрывание"
    )
    async def stop_command(self, ctx) -> None:
        """Полностью останавливает проигрывание треков в гильдии, очищает очередь.
        Если бот не будет проигрывать ничего в течении 2х минут, он обидится и уйдет"""
        voice = ctx.voice_client
        if not isinstance(ctx, ComponentContext):
            embed = embed_utils.create_music_embed(
                description="Заканчиваю прослушивание"
            )
            await ctx.send(embed=embed, delete_after=5)
        if voice.is_connected():
            del self.tracks[ctx.guild.id]
            await self.player_messages.delete_messages(ctx.guild.id)
            await self._stop(voice)

    @cog_ext.cog_slash(
        name="queue",
        description="Просмотреть все треки в очереди",
        options=[{"name": "page", "description": "Страница очереди", "type": 4}],
    )
    async def queue_command(self, ctx: SlashContext, page: Optional[int] = None):
        """Вызвать сообщение с текущей очередью проигрывания.
        Есть возможность в ручную выбирать страницы, если добавить к команде номер
        Если номер страницы не был выбран, страница будет выбрана как текущая для проигрываемого трека"""

        page, pages = self.queue_messages.get_page_counter(ctx.guild.id, page)

        if page > pages:
            embed = embed_utils.create_error_embed("Нет такой страницы")
            await ctx.send(embed=embed, delete_after=5)
            return
        embed = self.queue_messages.create_queue_embed(ctx, page)
        queue_message = await ctx.send(embed=embed, components=queue_components)
        if ctx.guild.id in self.queue_messages:
            await self.queue_messages[ctx.guild.id]["message"].delete(delay=2)

        self.queue_messages[ctx.guild.id] = {"message": queue_message, "page": page}

    @cog_ext.cog_slash(
        name="shuffle",
        description="Перемешать очередь"
    )
    async def shuffle_command(self, ctx):
        """Перемешать треки в очереди"""
        voice = ctx.voice_client
        if not (voice.is_playing() or voice.is_paused()):
            return
        tracks = self.tracks[ctx.guild.id]["tracks"]
        if len(tracks) == 1:
            if not isinstance(ctx, ComponentContext):
                embed = embed_utils.create_music_embed(
                    description="Зачем перемешивать очередь из одного трека?🤔"
                )
                await ctx.send(embed=embed, hidden=True)
            return
        shuffle(tracks)
        self.tracks[ctx.guild.id] = {"tracks": tracks, "index": -1}
        if self.queue_messages.get(ctx.guild.id) is not None:
            self.queue_messages[ctx.guild.id]["page"] = 1

        await self._stop(voice, force=False)
        if not isinstance(ctx, ComponentContext):
            embed = embed_utils.create_music_embed(description="Очередь перемешана")
            await ctx.send(embed=embed, delete_after=5)

    async def _skipped_tracks_msg(self, ctx, track, index):
        if isinstance(ctx, ComponentContext):
            return
        requester = self.client.get_user(track["requester"])
        description = f"Трек пропущен: **{index + 1}. {track['name']}**"
        if requester is not None:
            description += f" ({requester.mention})"
        embed = embed_utils.create_music_embed(description=description)
        await ctx.send(embed=embed, delete_after=3)

    @cog_ext.cog_slash(
        name="next",
        description="Пропустить трек",
        options=[
            {
                "name": "count",
                "description": "Количество пропускаемых треков",
                "type": 4,  # int
            }
        ],
    )
    async def next_command(self, ctx, count: Optional[int] = 1) -> None:
        """Пропустить один или несколько треков.
        Чтобы пропустить несколько треков, необходимо добавить число к команде"""
        voice = ctx.voice_client
        if ctx.guild.id not in self.tracks:
            return

        tracks, index = (
            self.tracks[ctx.guild.id]["tracks"],
            self.tracks[ctx.guild.id]["index"],
        )
        if (new_index := index + count) > len(tracks) - 1:
            new_index = await self.queue_index_overflow(
                ctx=ctx, voice_client=voice, default=0
            )
        if new_index is not None:
            self.tracks[ctx.guild.id]["index"] = new_index - 1
            await self._stop(voice, force=False)

        await self._skipped_tracks_msg(ctx, tracks[index], index)

    @cog_ext.cog_slash(
        name="prev",
        description="Вернуться на один трек назад",
        options=[
            {
                "name": "count",
                "description": "Количество пропускаемых треков",
                "type": 4,
            }
        ],
    )
    async def prev_command(self, ctx, count: Optional[int] = 1) -> None:
        """Вернуться на один или несколько треков назад.
        Про количество смотрите в команде **next**"""
        if ctx.guild.id not in self.tracks:
            return
        voice = ctx.voice_client

        tracks, index = (
            self.tracks[ctx.guild.id]["tracks"],
            self.tracks[ctx.guild.id]["index"],
        )
        if (new_index := index - count) < 0:
            new_index = await self.queue_index_overflow(
                ctx=ctx, voice_client=voice, default=len(tracks) - 1
            )
        if new_index is not None:
            self.tracks[ctx.guild.id]["index"] = new_index - 1
            await self._stop(voice, force=False)

        await self._skipped_tracks_msg(ctx, tracks[index], index)

    async def _add_tracks_to_queue(
            self, ctx: Union[commands.Context, SlashContext], tracks: list[dict]
    ) -> None:
        """
        Добавляем треки в очередь. Если там было пусто, запускаем первый
        """
        voice = ctx.voice_client
        if not voice or not voice.is_connected():
            voice = await self._join(ctx)
        if ctx.guild.id not in self.tracks:
            self.tracks[ctx.guild.id] = {"tracks": tracks, "index": 0}
            source = await discord.FFmpegOpusAudio.from_probe(
                tracks[0]["url"], **FFMPEG_OPTIONS
            )
            voice.play(
                source=source, after=lambda errors: self.play_next(errors, voice, ctx)
            )
            await self.player_command.invoke(ctx)
            return

        self.tracks[ctx.guild.id]["tracks"].extend(tracks)
        if len(tracks) == 1:
            embed = embed_utils.create_music_embed(
                title="Трек добавлен в очередь", description=tracks[0]["name"]
            )
        else:
            embed = embed_utils.create_music_embed(
                description=f"Треков добавлено в очередь: **{len(tracks)}**"
            )
        await ctx.send(embed=embed, delete_after=5)
        await self.player_messages.update_messages(ctx)

    @cog_ext.cog_slash(
        name="delete",
        description="Удалить трек из очереди",
        options=[
            {
                "name": "index",
                "description": "Индекс трека",
                "required": True,
                "type": 4,
            }
        ],
    )
    async def delete_command(self, ctx, index: int):
        """Удалить из очереди трек под номером, который вы скажете боту"""
        if not await check_self_voice(ctx):
            return
        voice = ctx.voice_client
        tracks, now_playing = (
            self.tracks[ctx.guild.id]["tracks"],
            self.tracks[ctx.guild.id]["index"],
        )

        if (index <= 0) or (index > len(tracks)):
            embed = embed_utils.create_error_embed(message="Некорректный индекс")
            await ctx.send(embed=embed, delete_after=5)
            return
        embed = embed_utils.create_music_embed(
            description=f"Удаляю трек: **{tracks[index - 1]['name']}**"
        )
        if index - 1 == now_playing:
            if len(tracks) == 1:
                await self.player_messages.delete_messages(ctx.guild.id)
            else:
                self.tracks[ctx.guild.id]["index"] = now_playing - 1
            await self._stop(voice, force=False)

        if index - 1 < now_playing:
            self.tracks[ctx.guild.id]["index"] = now_playing - 1
        del tracks[index - 1]
        await ctx.send(embed=embed, delete_after=5)

        await self.player_messages.update_messages(ctx)

    @cog_ext.cog_slash(
        name="jump",
        description="Перепрыгнуть на определенный трек",
        options=[
            {
                "name": "index",
                "description": "Индекс трека",
                "required": True,
                "type": 4,
            }
        ],
    )
    async def jump_command(self, ctx, index: int):
        """Перепрыгнуть на определенный трек под номером, который вы скажете боту в команде"""
        if not await check_self_voice(ctx):
            return
        voice = ctx.voice_client

        tracks_info = self.tracks[ctx.guild.id]
        tracks = tracks_info["tracks"]
        if (index > len(tracks)) or (index <= 0):
            embed = embed_utils.create_error_embed(
                message=f"Некорректный индекс. Максимальный - {len(tracks)}"
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        self.tracks[ctx.guild.id]["index"] = index - 2
        await self._stop(voice, force=False)
        if not isinstance(ctx, ComponentContext):
            embed = embed_utils.create_music_embed(
                title="Перепрыгиваю на трек",
                description=f"**{index}. {tracks[index - 1]['name']}**",
            )
            await ctx.send(embed=embed, delete_after=5)

    @cog_ext.cog_slash(
        name="loop", description="Изменить настройки зацикливания очереди"
    )
    async def loop_command(self, ctx: SlashContext):
        """Изменить настройки зацикливания очереди"""
        is_looped = functions.get_guild_data(ctx.guild, "loop_queue")
        functions.change_loop_option(ctx.guild.id, not is_looped)
        if isinstance(ctx, ComponentContext):
            await self.player_messages.player_message_update(ctx)
            return
        cliche = "Зацикливание очереди {} для вашей гильдии"
        if is_looped:
            embed = embed_utils.create_info_embed(
                description=cliche.format("отключено")
            )
        else:
            embed = embed_utils.create_info_embed(description=cliche.format("включено"))
        await ctx.send(embed=embed, delete_after=5)

    @cog_ext.cog_slash(name="leave", description="Выгнать бота из голосового канала")
    async def leave_command(self, ctx):
        """Прогнать бота из голосового канала(останавливает прослушивание и очищает очередь)"""
        voice = ctx.voice_client
        if voice.is_connected():
            current_tracks_data = self.tracks.get(ctx.guild.id)
            if current_tracks_data is not None:
                del self.tracks[ctx.guild.id]

            await self.player_messages.delete_messages(ctx.guild.id)

            await voice.disconnect()
            embed = embed_utils.create_info_embed(description="Ухожу")
            await ctx.send(embed=embed, delete_after=3)

    @cog_ext.cog_slash(
        name="save",
        description="Сохранить плейлист",
        options=[
            {"name": "playlist_name", "description": "Имя нового плейлиста", "type": 3}
        ],
    )
    async def save_playlist_command(
            self, ctx: SlashContext, playlist_name: Optional[str] = None
    ):
        """Сохранить текущий плейлист"""
        if ctx.guild.id not in self.tracks:
            embed = embed_utils.create_error_embed(message="Нет треков в очереди")
            await ctx.send(embed=embed)
            return
        await ctx.defer()
        playlist = self.tracks[ctx.guild.id]["tracks"]
        if playlist_name is not None:
            playlist_name = playlist_name.strip()

        playlist_name = playlists_utils.save_new_playlist(
            ctx.guild.id, playlist, name=playlist_name
        )
        if playlist_name is None:
            embed = embed_utils.create_error_embed(
                message="В вашей гильдии сохранено слишком много плейлистов\n"
                        "Максимальное кол-во на данный момент: `10`"
            )
            return await ctx.send(embed=embed)

        embed = embed_utils.create_music_embed(
            title="Плейлист сохранен", description=f"Название: `{playlist_name}`"
        )
        return await ctx.send(embed=embed)

    async def _check_for_playlist(self, _callable, args, after, ctx):
        playlist_name = args[1]
        try:
            _callable(*args)
        except NoGuildPlaylists:
            embed = embed_utils.create_error_embed(
                message="В вашей гильдии еще нет плейлистов\n"
                        "Используйте команду `/save` для сохранения очереди в плейлист"
            )
            await ctx.send(embed=embed)
        except PlaylistNotFound:
            embed = embed_utils.create_error_embed(
                message=f"Не найдено плейлиста по запросу: `{playlist_name}`"
            )
            await ctx.send(embed=embed)
        else:
            await after()

    @cog_ext.cog_slash(
        name="rename",
        description="Переименовать плейлист",
        options=[
            {
                "name": "old_name",
                "description": "Текущее название плейлиста",
                "required": True,
                "type": 3,
            },
            {
                "name": "new_name",
                "description": "Новое название плейлиста",
                "required": True,
                "type": 3,
            },
        ],
    )
    async def rename_playlist_command(
            self, ctx: SlashContext, old_name: str, new_name: str
    ):
        """Переименовать плейлист."""
        await ctx.defer()
        old_name = old_name.strip()
        new_name = new_name.strip()

        async def after():
            _embed = embed_utils.create_music_embed(
                description=f"Название плейлиста `{old_name}` изменено на `{new_name}`"
            )
            await ctx.send(embed=_embed)

        await self._check_for_playlist(
            playlists_utils.rename_playlist,
            [ctx.guild.id, old_name, new_name],
            after,
            ctx,
        )

    @cog_ext.cog_slash(
        name="delete_playlist",
        description="Удалить плейлист",
        options=[
            {
                "name": "playlist_name",
                "description": "Имя плейлиста",
                "required": True,
                "type": 3,
            }
        ],
    )
    async def delete_playlist_command(self, ctx: SlashContext, playlist_name: str):
        """Удалить плейлист, имя которого вы укажите после этой команды"""
        await ctx.defer()
        playlist_name = playlist_name.strip()

        async def after():
            _embed = embed_utils.create_music_embed(
                description=f"Плейлист с названием **{playlist_name}** удален"
            )
            await ctx.send(embed=_embed)

        await self._check_for_playlist(
            playlists_utils.delete_playlist, [ctx.guild.id, playlist_name], after, ctx
        )

    async def _leaving(self, voice: discord.VoiceClient, guild_id):
        """
        Clear info and leave from voice channel
        """
        if guild_id in self.tracks:
            del self.tracks[guild_id]

        await self.player_messages.delete_messages(guild_id)
        await voice.disconnect()

    player_command.add_check(check_self_voice)
    pause_command.add_check(check_self_voice)
    resume_command.add_check(check_self_voice)
    stop_command.add_check(check_self_voice)
    shuffle_command.add_check(check_self_voice)
    prev_command.add_check(check_self_voice)
    next_command.add_check(check_self_voice)
    queue_command.add_check(check_self_voice)
    jump_command.add_check(check_self_voice)
    leave_command.add_check(check_self_voice)

    play_playlist_command.add_check(check_user_voice)
    play_link_command.add_check(check_user_voice)
    play_request_command.add_check(check_user_voice)
    play_user_saved_command.add_check(check_user_voice)

    # Auto self deaf
    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState,
    ):
        voice = member.guild.voice_client
        if member == self.client.user:
            if not member.guild_permissions.deafen_members:
                return
            if not after.deaf:
                await member.edit(deafen=True)
            if after.mute:
                await member.edit(mute=False)
            if voice and not voice.is_connected() and after.channel is None:
                if member.guild.id in self.tracks:
                    del self.tracks[member.guild.id]
                    await self._stop(voice, force=True)
                return

        if before.channel is None or voice is None:
            return
        members = before.channel.members
        if before.channel == member.guild.voice_client.channel:
            if (len(members) == 1) and self.client.user in members:
                await asyncio.sleep(15)

                updated_members = voice.channel.members
                if (len(updated_members) == 1) and self.client.user in updated_members:
                    return await self._leaving(voice, member.guild.id)

    @commands.Cog.listener()
    async def on_component(self, ctx: ComponentContext):
        await ctx.defer(ignore=True)

        # PLAYER COMPONENTS
        if ctx.custom_id == "shuffle":
            await self.shuffle_command.invoke(ctx)
            return
        if ctx.custom_id == "previous":
            await self.prev_command.invoke(ctx)
            return
        if ctx.custom_id == "play_pause":
            voice = ctx.voice_client
            if voice is not None:
                if voice.is_playing():
                    await self.pause_command.invoke(ctx)
                elif voice.is_paused():
                    await self.resume_command.invoke(ctx)
            return
        if ctx.custom_id == "next":
            await self.next_command.invoke(ctx)
            return
        if ctx.custom_id == "stop":
            await self.stop_command.invoke(ctx)
            return
        if ctx.custom_id == "loop":
            await self.loop_command.invoke(ctx)
            return
        if ctx.custom_id == "queue":
            await self.queue_command.invoke(ctx)
            return

        # QUEUE COMPONENTS
        if ctx.custom_id == "queue_prev":
            page, pages = self.queue_messages.get_page_counter(ctx.guild.id)
            if page <= 1:
                return
            embed = self.queue_messages.create_queue_embed(ctx, page - 1)
            self.queue_messages[ctx.guild.id]["page"] = page - 1
            await self.queue_messages[ctx.guild.id]["message"].edit(embed=embed)
            return
        if ctx.custom_id == "queue_next":
            page, pages = self.queue_messages.get_page_counter(ctx.guild.id)
            if pages < 2 or page == pages:
                return
            embed = self.queue_messages.create_queue_embed(ctx, page + 1)
            self.queue_messages[ctx.guild.id]["page"] = page + 1
            await self.queue_messages[ctx.guild.id]["message"].edit(embed=embed)
            return


def setup(client):
    client.add_cog(Player(client))
