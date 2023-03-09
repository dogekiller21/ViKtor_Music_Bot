from discord import Embed

from bot.constants import CustomColors


class BotEmbeds:
    @staticmethod
    def error_embed(
        description: str,
        title: str | None = None,
        thumb_url: str | None = None,
        **kwargs
    ) -> Embed:
        embed = Embed(
            title=title,
            description=description,
            color=CustomColors.ERROR_COLOR,
            **kwargs
        )
        if thumb_url:
            embed.set_thumbnail(url=thumb_url)
        return embed

    @staticmethod
    def info_embed(description: str, title: str | None = None, **kwargs):
        return Embed(
            title=title,
            description=description,
            color=CustomColors.INFO_COLOR,
            **kwargs
        )
