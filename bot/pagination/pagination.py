import asyncio
import traceback
from typing import Union

import discord
from discord import NotFound
from discord_slash import ButtonStyle, ComponentContext
from discord_slash.error import IncorrectFormat
from discord_slash.utils.manage_components import create_actionrow, create_button, wait_for_component

DEFAULT_PAGINATION_BUTTONS = create_actionrow(
    create_button(style=ButtonStyle.gray, emoji="⬅", custom_id="page_back"),
    create_button(style=ButtonStyle.gray, label="_empty", custom_id="_pages", disabled=True),
    create_button(style=ButtonStyle.gray, emoji="➡", custom_id="page_next")
)


class CancelPagination(Exception):
    pass


class EmbedPagination:
    def __init__(self,
                 *,
                 default_content: str = None,
                 default_components: list[dict] = None,
                 target_embeds: list[discord.Embed] = None,
                 target_callable=None,
                 target_callable_kwargs: dict = None,
                 start_page: int = None,
                 max_page: int = None,
                 timeout: int = None,
                 infinite: bool = True,
                 numeration_list: list[str] = None,
                 guild_id: int,
                 client: discord.Client):
        if target_embeds is None and target_callable is None:
            raise IncorrectFormat("You must have target callable or target embeds")
        if target_embeds is not None and target_callable is not None:
            raise IncorrectFormat("You can only have callable OR embeds as targets")
        if target_callable is not None and max_page is None:
            raise IncorrectFormat("You must specify max pages with callable")

        self._max_page = max_page or (len(target_embeds) if target_embeds else 0)

        if start_page > self._max_page:
            raise IncorrectFormat(f"Start page index can't be grater than max page index ({self._max_page})")

        self.default_content = default_content or ""
        self.default_components = default_components or []

        self._embeds = target_embeds

        self.coro = target_callable
        self._coro_kwargs = target_callable_kwargs or {}

        self._current_page = start_page or 0
        self.timeout = timeout

        self._infinite = infinite
        self._numeration = numeration_list
        self._guild_id = guild_id

        self.client = client

        self._buttons = DEFAULT_PAGINATION_BUTTONS

        self._target_message = None
        self._components = [*self.default_components, self._buttons]

        self._is_running = False

    def __len__(self) -> int:
        """Returns max number of pages"""
        return self._max_page

    @property
    def loop(self):
        """Returns client's event loop"""
        return self.client.loop

    @property
    def current_page(self):
        """Returns current page"""
        return self._current_page

    @current_page.setter
    def current_page(self, page):
        self._current_page = page
        self.update()

    @property
    def is_running(self):
        return self._is_running

    @property
    def message(self):
        """Returns message with pagination"""
        return self._target_message

    @property
    def max_page(self):
        """Returns max number of pages"""
        return self._max_page

    @max_page.setter
    def max_page(self, value):
        """Sets max number of pages (can't be user if embeds is provided)"""
        if self._embeds is not None:
            raise IncorrectFormat("You can't edit max page value with embed list")
        if value < 0:
            value = 0
        self._max_page = value

    @property
    def embeds(self):
        """Returns embeds list (None if function provided)"""
        return self._embeds

    @embeds.setter
    def embeds(self, embeds_list: list[discord.Embed]):
        """Sets embeds list (can't be used if function provided)"""
        if self.coro is not None:
            raise IncorrectFormat("You can't edit embeds list with function provided")
        self._embeds = embeds_list
        self._max_page = len(embeds_list)

    def add_embeds(self, embeds: Union[list[discord.Embed], discord.Embed]):
        if isinstance(embeds, list):
            self._embeds.extend(embeds)
        else:
            self._embeds.append(embeds)
        self._max_page = len(self._embeds)
        return self

    def _set_numeration(self):
        if self._numeration is None:
            numeration = f"Стр {self._current_page + 1}/{self._max_page}"
        else:
            if self._current_page >= len(self._numeration):
                numeration = "###"
            else:
                numeration = self._numeration[self._current_page]
        self._buttons["components"][1]["label"] = numeration

    async def send(self, ctx):
        self._set_numeration()

        if self._embeds is not None:
            embed = self._embeds[self._current_page]
        else:
            try:
                embed = await self.coro(self._current_page, **self._coro_kwargs)
            except Exception as error:
                embed = discord.Embed(title="Произошла ошибка в обработке страницы\n"
                                            "Попробуйте еще раз")
                traceback.print_tb(error)
        self._target_message = await ctx.send(content=self.default_content,
                                              embed=embed,
                                              components=self._components)
        self._is_running = True
        while not self.client.is_closed() and self._is_running:
            try:
                message_delete = self.client.wait_for("raw_message_delete",
                                                      check=lambda p: p.message_id == self._target_message.id)
                component_invoke = wait_for_component(
                    client=self.client,
                    messages=self._target_message,
                    components=self._buttons
                )
                done, pending = await asyncio.wait(
                    [message_delete, component_invoke],
                    timeout=self.timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                if len(done) == 0:
                    # Timed Out
                    raise CancelPagination

                if not isinstance(result := done.pop().result(), ComponentContext):
                    self._infinite = False
                    raise CancelPagination

                if result.custom_id == "page_back":
                    self._current_page -= 1
                elif result.custom_id == "page_next":
                    self._current_page += 1
                if self._current_page == self._max_page:
                    self._current_page = 0
                elif self._current_page < 0:
                    self._current_page = self._max_page - 1

                await self.update()

            except CancelPagination:
                if self._infinite:
                    continue
                self._is_running = False
                self._buttons["components"][0]["disabled"] = True
                self._buttons["components"][2]["disabled"] = True
                try:
                    await self._target_message.edit(components=self._components)
                except discord.HTTPException:
                    pass
                finally:
                    self.client.dispatch("pagination_stop", self._guild_id)
                    break

    async def delete(self, delay=None):
        try:
            await self._target_message.delete(delay=delay)
        except NotFound:
            pass
        finally:
            self._is_running = False

    async def update(self):
        if self._embeds is not None:
            embed = self._embeds[self._current_page]
        else:
            embed = await self.coro(self._current_page, **self._coro_kwargs)

        self._set_numeration()

        await self._target_message.edit(embed=embed, components=self._components)
