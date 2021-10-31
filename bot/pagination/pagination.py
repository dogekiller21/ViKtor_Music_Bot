import asyncio

import discord
from discord_slash import ButtonStyle, ComponentContext
from discord_slash.error import IncorrectFormat
from discord_slash.utils.manage_components import create_actionrow, create_button, wait_for_component


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
                 timeout: int = 60,
                 client):
        if target_embeds is None and target_callable is None:
            raise IncorrectFormat("You must have target callable or target embeds")
        if target_embeds is not None and target_callable is not None:
            raise IncorrectFormat("You can only have callable or embeds as targets")
        if target_embeds is not None and max_page is None:
            raise IncorrectFormat("You must specify max pages with callable")

        self._max_page = max_page or (len(target_embeds) if target_embeds else 0)
        if start_page > self._max_page:
            raise IncorrectFormat(f"Start page index can't be grater than max page index ({self._max_page})")

        self.default_content = default_content or ""
        self.default_components = default_components or []

        self.embeds = target_embeds

        self.coro = target_callable
        self._coro_kwargs = target_callable_kwargs or {}

        self._current_page = start_page or 0
        self.timeout = timeout

        self.client = client

        self._buttons = create_actionrow(
            create_button(style=ButtonStyle.gray, emoji="⬅", custom_id="page_back"),
            create_button(style=ButtonStyle.gray, label="_empty", custom_id="_pages", disabled=True),
            create_button(style=ButtonStyle.gray, emoji="➡", custom_id="page_next")
        )

        self._target_message = None
        self._components = [*self.default_components, self._buttons]

    @property
    def message(self):
        return self._target_message

    @property
    def max_page(self):
        return self._max_page

    @max_page.setter
    def max_page(self, value):
        if self.embeds is not None:
            raise IncorrectFormat("You can't edit max page value with embed list")
        if value < 0:
            value = 0
        self._max_page = value

    async def send(self, ctx):

        self._buttons["components"][1]["label"] = f"Стр {self._current_page + 1}/{self._max_page}"

        if self.embeds is not None:
            embed = self.embeds[self._current_page]
        else:
            embed = await self.coro(self._current_page, **self._coro_kwargs)
        self._target_message = await ctx.send(content=self.default_content,
                                              embed=embed,
                                              components=self._components)
        while True:
            if self._target_message is None:
                return
            try:
                component_ctx: ComponentContext = await wait_for_component(
                    client=self.client,
                    messages=self._target_message,
                    components=self._buttons,
                    timeout=self.timeout
                )
                if component_ctx.custom_id == "page_back":
                    self._current_page -= 1
                elif component_ctx.custom_id == "page_next":
                    self._current_page += 1
                if self._current_page == self._max_page:
                    self._current_page = 0
                elif self._current_page < 0:
                    self._current_page = self._max_page - 1

                await self.update()

            except asyncio.TimeoutError:
                if self._target_message is None:
                    break
                continue
                # self._buttons["components"][0]["disabled"] = True,
                # self._buttons["components"][2]["disabled"] = True
                # await self._target_message.edit(components=self._components)
                # break

    async def delete(self, delay=None):
        await self._target_message.delete(delay=delay)
        self._target_message = None

    async def update(self):
        if self.embeds is not None:
            embed = self.embeds[self._current_page]
        else:
            embed = await self.coro(self._current_page, **self._coro_kwargs)

        self._buttons["components"][1]["label"] = f"Стр {self._current_page + 1}/{self._max_page}"

        await self._target_message.edit(embed=embed, components=self._components)
