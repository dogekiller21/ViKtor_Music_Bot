import asyncio
from typing import Optional, Union

import discord
from discord import NotFound

from discord.ext import commands
from discord.ext.commands import Bot
from discord_slash import cog_ext, SlashContext, ComponentContext, ContextMenuType, MenuContext
from discord_slash.utils.manage_components import (
    create_select_option,
    create_select,
    create_actionrow,
    wait_for_component
)

from bot import vk_parsing
from .constants import VK_URL_PREFIX, FFMPEG_OPTIONS, TIMEOUT_OPTION, CANCEL_OPTION, BotEmoji, GENIUS_LOGO_URL
from bot.storage.player_storage import BotStorage, Queue, IncorrectDeleteIndex, RepeatMode
from ..bot import bot_storage
from ..events.components_events import player_components, CANCEL_BUTTON
from ..utils import playlists_utils, embed_utils, player_msg_utils, message_utils
from ..utils.checks import check_user_voice, check_self_voice
from ..utils.custom_exceptions import (
    NoGuildPlaylists,
    PlaylistNotFound,
)
from ..lyrics import get_lyrics


class Player(commands.Cog):
    """Команды, связанные с проигрыванием музыки"""

    def __init__(self, client: Bot):
        self.client = client
        self._waiting_for_leave = dict()
        self.loop = self.client.loop
        self.storage: BotStorage = bot_storage

    async def _stop(self, voice, force: bool = True) -> None:
        """
        ...VoiceClient.stop() with leave timer

        :param voice: discord.VoiceClient
        :param force: bool
        """
        voice.stop()
        if not force:
            return
        try:
            self._waiting_for_leave[voice.guild.id] = True
            await self.client.wait_for("_bot_playing_music", timeout=120)
        except asyncio.TimeoutError:
            await self._leaving(voice, voice.guild.id)
        finally:
            del self._waiting_for_leave[voice.guild.id]

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

    def play_next(self, error, ctx):
        """
        Callable for invoking after track stops
        """
        if error is not None:
            print(f"next play error: {error}")  # TODO логгирование

        queue = self.storage.queues.get(ctx.guild.id)
        if queue is None:
            asyncio.run_coroutine_threadsafe(self.storage.delete_messages(ctx.guild.id), self.loop)
            return

        next_track = queue.get_next_track()
        if next_track is None:
            asyncio.run_coroutine_threadsafe(self.storage.delete_messages(ctx.guild.id), self.loop)
            asyncio.run_coroutine_threadsafe(self._stop(ctx.voice_client), self.loop)
            return

        source = asyncio.run_coroutine_threadsafe(
            discord.FFmpegOpusAudio.from_probe(
                source=next_track["url"], **FFMPEG_OPTIONS
            ),
            self.loop
        ).result()
        voice = ctx.voice_client
        voice.play(source=source,
                   after=lambda err: self.play_next(err, ctx))

        asyncio.run_coroutine_threadsafe(self.storage.update_messages(ctx), self.loop)

    @cog_ext.cog_slash(
        name="lyrics",
        description="Получить слова на сейчас играющий трек"
    )
    async def lyrics_command(self, ctx: SlashContext) -> None:
        queue = self.storage.queues[ctx.guild.id]
        track_name = queue.tracks[queue.current_index]["name"]
        await ctx.defer()
        lyrics = await self.loop.run_in_executor(None, get_lyrics, track_name)
        if lyrics is None:
            await ctx.send(
                embed=embed_utils.create_error_embed(title="Слова не найдены",
                                                     message=f"Слова для трека **{track_name}** не найдены")
            )
            return
        embed = embed_utils.create_music_embed(title=f"Слова для трека {track_name}",
                                               description=lyrics,
                                               footer="Genius Lyrics",
                                               footer_img=GENIUS_LOGO_URL)

        await ctx.send(
            embed=embed
        )

    @cog_ext.cog_slash(
        name="player",
        description="Вызов плеера для текущей гильдии",
    )
    async def player_command(self, ctx: Union[SlashContext, commands.Context]) -> None:
        """Вызов плеера для текущей гильдии"""
        embed = self.storage.player_storage.create_player_embed(ctx)
        player_message = await ctx.send(embed=embed, components=player_components)
        current_message = self.storage.player_storage.messages.get(ctx.guild.id)
        if current_message is not None:
            await current_message.delete(delay=2)
        self.storage.player_storage.messages[ctx.guild.id] = player_message

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
            await message_utils.send_error_message(
                ctx,
                description="В вашей гильдии еще нет плейлистов\n"
                            "Используйте команду `/save` для сохранения очереди в плейлист"
            )
            return
        if playlist_name is None:
            embed = playlists_utils.get_playlists_message(ctx)
            await ctx.send(embed=embed)
            return
        if playlist_name not in playlists:
            await message_utils.send_error_message(
                ctx,
                description=f"Не найдено плейлиста с названием {playlist_name}"
            )
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
            await message_utils.send_error_message(ctx, description="Некорректная ссылка")
            return
        await ctx.defer()
        tracks = await vk_parsing.get_audio(link, requester=ctx.author.id)
        await self._add_tracks_to_queue(ctx=ctx, tracks=tracks)

    async def _select_options_parser(
            self, ctx: SlashContext, select: dict, msg_filler: str, timeout: int = 60
    ):
        """
        Возвращает номер выбранного пользователем элемента в селекте
        :return: int
        """
        embed = embed_utils.create_music_embed(title=f"Выберите {msg_filler} для добавления в очередь",
                                               description=f"Выбирать должен {ctx.author.mention}")
        component = create_actionrow(select)
        message = await ctx.send(embed=embed, components=[component, CANCEL_BUTTON])

        def check(_ctx: ComponentContext):
            return _ctx.author_id == ctx.author.id

        try:
            component_ctx: ComponentContext = await wait_for_component(
                self.client, messages=message, components=[component, CANCEL_BUTTON],
                timeout=timeout, check=check
            )
        except asyncio.TimeoutError:
            select["options"][-1] = TIMEOUT_OPTION
        else:
            if component_ctx.custom_id == "cancel_select":
                select["options"][-1] = CANCEL_OPTION
                return
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
        tracks = await player_msg_utils.get_tracks_or_playlists_by_name(ctx=ctx, name=request, count=25)
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
                    emoji=BotEmoji.SINGLE_TRACK_EMOJI,
                )
            )

        tracks_select = create_select(
            options=tracks_options,
            placeholder="Выберите трек для добавления в очередь",
            min_values=1,
        )

        selected_value = await self._select_options_parser(ctx, tracks_select, "трек")
        if selected_value is None:
            return
        selected_track = tracks[selected_value]
        await self._add_tracks_to_queue(ctx, tracks=[selected_track])

    @cog_ext.cog_context_menu(
        name="Найти трек",
        target=ContextMenuType.MESSAGE
    )
    async def find_track_context_menu(self, ctx: MenuContext):
        content = ctx.target_message.content.strip()
        if not content and ctx.target_message.embeds:
            content = ctx.target_message.embeds[0].title or ctx.target_message.embeds[0].description
        await self.play_request_command.invoke(ctx, content)

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
        playlists = await player_msg_utils.get_tracks_or_playlists_by_name(ctx=ctx, name=playlist_name, count=25,
                                                                           is_tracks=False)
        if playlists is None:
            return
        playlists_options = []
        for i, playlist in enumerate(playlists):
            playlists_options.append(
                create_select_option(
                    label=playlist["title"],
                    description=playlist["description"],
                    value=str(i),
                    emoji=BotEmoji.PLAYLIST_EMOJI,
                )
            )

        playlist_select = create_select(
            options=playlists_options,
            placeholder="Выберите плейлист для добавления в очередь",
            min_values=1,
        )
        selected_value = await self._select_options_parser(ctx, playlist_select, "плейлист")
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
            await message_utils.send_error_message(ctx, description="Некорректная ссылка")
            return
        await ctx.defer()
        user = user_link.split("vk.com/")[1]
        tracks = await vk_parsing.get_user_saved_tracks(user, requester=ctx.author.id)
        if tracks is None:
            await message_utils.send_error_message(
                ctx,
                description="Некорректный пользователь\n"
                            "Либо у данного пользователя закрыта страница / аудиозаписи"
            )
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
        await self.storage.update_messages(ctx)
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
        await self.storage.update_messages(ctx)
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
            await self.storage.delete_messages(ctx.guild.id)
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

        await self.storage.queues[ctx.guild.id].send_message(ctx, page)

    @commands.Cog.listener(name="on_pagination_stop")
    async def on_pagination_stop(self, guild_id):
        queue = self.storage.queues.get(guild_id)
        if queue is None:
            return
        queue.message = None

    @cog_ext.cog_slash(
        name="shuffle",
        description="Перемешать очередь"
    )
    async def shuffle_command(self, ctx):
        """Перемешать треки в очереди"""
        voice = ctx.voice_client
        if not (voice.is_playing() or voice.is_paused()):
            return
        # tracks = self.tracks[ctx.guild.id]["tracks"]
        queue = self.storage.queues[ctx.guild.id]
        if len(queue) == 1:
            if not isinstance(ctx, ComponentContext):
                embed = embed_utils.create_music_embed(
                    description="Зачем перемешивать очередь из одного трека?🤔"
                )
                await ctx.send(embed=embed, hidden=True)
            return
        # shuffle(tracks)
        # self.tracks[ctx.guild.id] = {"tracks": tracks, "index": -1}
        queue.shuffle_tracks()
        if ctx.guild.id in self.storage.queues and queue.message is not None:
            queue.message.current_page = 0

        await self._stop(voice, force=False)
        if not isinstance(ctx, ComponentContext):
            embed = embed_utils.create_music_embed(description="Очередь перемешана")
            await ctx.send(embed=embed, delete_after=5)

    async def _skipped_tracks_msg(self, ctx, track):
        if isinstance(ctx, ComponentContext):
            return
        # track = self.tracks[ctx.guild.id]["tracks"][index]
        index = self.storage.queues[ctx.guild.id].tracks.index(track)
        track_name = track["name"]
        requester = self.client.get_user(track["requester"])
        description = f"Трек пропущен: **{index + 1}. {track_name}**"
        if requester is not None:
            description += f" ({requester.mention})"
        embed = embed_utils.create_music_embed(description=description)
        await ctx.send(embed=embed, delete_after=3)

    async def _change_voice_source(self, ctx, track):
        voice = ctx.voice_client
        new_source = await discord.FFmpegOpusAudio.from_probe(
            track["url"], **FFMPEG_OPTIONS
        )
        voice.source = new_source
        await self.storage.update_messages(ctx)

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
        queue = self.storage.queues[ctx.guild.id]
        index = queue.current_index
        track = queue.get_next_track(count)
        if track is not None:
            await self._change_voice_source(ctx, track)
        await self._skipped_tracks_msg(ctx, index)

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

        queue = self.storage.queues[ctx.guild.id]
        index = queue.current_index
        track = queue.get_prev_track(count)
        if track is not None:
            await self._change_voice_source(ctx, track)

        await self._skipped_tracks_msg(ctx, index)

    async def _add_tracks_to_queue(
            self, ctx: Union[commands.Context, SlashContext], tracks: list[dict]
    ) -> None:
        """
        Добавляем треки в очередь. Если там было пусто, запускаем первый
        """
        if ctx.guild.id in self._waiting_for_leave:
            self.client.dispatch("_bot_playing_music")

        voice = ctx.voice_client
        if not voice or not voice.is_connected():
            voice = await self._join(ctx)
        if ctx.guild.id not in self.storage.queues:
            self.storage.queues[ctx.guild.id] = Queue(ctx.guild.id)
            self.storage.queues[ctx.guild.id].add_tracks(tracks)
            source = await discord.FFmpegOpusAudio.from_probe(
                tracks[0]["url"], **FFMPEG_OPTIONS
            )
            voice.play(
                source=source, after=lambda errors: self.play_next(errors, ctx)
            )
            await self.player_command.invoke(ctx)
            return
        self.storage.queues[ctx.guild.id].add_tracks(tracks)
        if len(tracks) == 1:
            embed = embed_utils.create_music_embed(
                title="Трек добавлен в очередь", description=tracks[0]["name"]
            )
        else:
            embed = embed_utils.create_music_embed(
                description=f"Треков добавлено в очередь: **{len(tracks)}**"
            )
        await ctx.send(embed=embed, delete_after=5)
        await self.storage.update_messages(ctx)

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

        voice = ctx.voice_client
        queue = self.storage.queues[ctx.guild.id]
        tracks = queue.tracks
        current_index = queue.current_index
        try:
            queue.delete_from_queue(index)
        except IncorrectDeleteIndex:
            await message_utils.send_error_message(ctx, description="Некорректный индекс")
            return

        duration = player_msg_utils.get_duration(tracks[index - 1]["duration"])
        embed = embed_utils.create_music_embed(
            title="Трек удален из очереди",
            description=f"**{tracks[index - 1]['name']}** ({duration})"
        )
        if index - 1 == current_index:
            if len(queue) == 1:
                await self.storage.delete_messages(ctx.guild.id)
            else:
                queue.current_index = current_index - 1
            await self._stop(voice, force=False)

        if index - 1 < current_index:
            queue.current_index = current_index - 1
        await ctx.send(embed=embed, delete_after=5)

        await self.storage.update_messages(ctx)

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

        voice = ctx.voice_client

        queue = self.storage.queues[ctx.guild.id]
        tracks = queue.tracks
        if (index > len(queue)) or (index <= 0):
            await message_utils.send_error_message(
                ctx,
                description=f"Некорректный индекс. Максимальный: `{len(tracks)}`"
            )
            return
        queue.current_index = index - 2
        await self._stop(voice, force=False)

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
        repeat_mode = self.storage.queues[ctx.guild.id].edit_repeat_mode()
        if isinstance(ctx, ComponentContext):
            await self.storage.update_messages(ctx)
            return
        cliche = "Настройка зацикливания очереди изменена на: "
        if repeat_mode == RepeatMode.NONE:
            description = cliche.format("Зацикливание выключено")

        elif repeat_mode == RepeatMode.ONE:
            description = cliche.format("Зацикливание одного трека")
        else:
            description = cliche.format("Зацикливание всей очереди")
        embed = embed_utils.create_info_embed(description=description)
        await ctx.send(embed=embed, delete_after=5)

    @cog_ext.cog_slash(name="leave", description="Выгнать бота из голосового канала")
    async def leave_command(self, ctx):
        """Прогнать бота из голосового канала(останавливает прослушивание и очищает очередь)"""
        voice = ctx.voice_client
        if voice.is_connected():
            queue = self.storage.queues.get(ctx.guild.id)
            if queue is not None:
                del queue

            await self.storage.delete_messages(ctx.guild.id)

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
        if ctx.guild.id not in self.storage.queues:
            await message_utils.send_error_message(ctx, description="Нет треков в очереди")
            return
        await ctx.defer()
        playlist = self.storage.queues[ctx.guild.id].tracks
        if playlist_name is not None:
            playlist_name = playlist_name.strip()

        playlist_name = playlists_utils.save_new_playlist(
            ctx.guild.id, playlist, name=playlist_name
        )
        if playlist_name is None:
            await message_utils.send_error_message(
                ctx,
                description="В вашей гильдии сохранено слишком много плейлистов\n"
                            "Максимальное кол-во на данный момент: `10`"
            )
            return

        embed = embed_utils.create_music_embed(
            title="Плейлист сохранен", description=f"Название: `{playlist_name}`"
        )
        return await ctx.send(embed=embed)

    async def _check_for_playlist(self, _callable, args, after, ctx):
        playlist_name = args[1]
        try:
            _callable(*args)
        except NoGuildPlaylists:
            await message_utils.send_error_message(
                ctx,
                description="В вашей гильдии еще нет плейлистов\n"
                            "Используйте команду `/save` для сохранения очереди в плейлист"
            )
        except PlaylistNotFound:
            await message_utils.send_error_message(
                ctx,
                description=f"Не найдено плейлиста по запросу: `{playlist_name}`"
            )
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
        queue = self.storage.queues.get(guild_id)
        if queue is not None:
            del queue
        await self.storage.delete_messages(guild_id)
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
    delete_command.add_check(check_self_voice)
    lyrics_command.add_check(check_self_voice)

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

            if voice and not voice.is_connected() and after.channel is None:
                if member.guild.id in self.storage.queues:
                    self.storage.del_queue(member.guild.id)
                    await self._stop(voice, force=True)
                return
            if not member.guild_permissions.deafen_members:
                return
            if not after.deaf:
                await member.edit(deafen=True)
            if after.mute:
                await member.edit(mute=False)

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


def setup(client):
    client.add_cog(Player(client))
