from typing import Optional

from bot.utils import embed_utils


async def send_error_message(ctx, title: Optional[str] = None, description: Optional[str] = None):
    if title is None and description is None:
        raise ValueError("Can't send message with empty embed")
    embed = embed_utils.create_error_embed(title=title, message=description)
    await ctx.send(embed=embed, hidden=True)
