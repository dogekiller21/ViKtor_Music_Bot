from discord_slash import ComponentContext, ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow

from bot.bot import client

_player_buttons1 = [
    create_button(style=ButtonStyle.gray,
                  emoji="🔀",
                  custom_id="shuffle"),

    create_button(style=ButtonStyle.gray,
                  emoji="⏪",
                  custom_id="previous"),

    create_button(style=ButtonStyle.gray,
                  emoji="▶",
                  custom_id="play_pause"),

    create_button(style=ButtonStyle.gray,
                  emoji="⏩",
                  custom_id="next"),

    create_button(style=ButtonStyle.gray,
                  emoji="⏹",
                  custom_id="stop"),

]

_player_buttons2 = [
    create_button(style=ButtonStyle.gray,
                  emoji="🔁",
                  custom_id="loop"),

    create_button(style=ButtonStyle.gray,
                  emoji="📑",
                  custom_id="queue"),
]
_player_action_row1 = create_actionrow(*_player_buttons1)
_player_action_row2 = create_actionrow(*_player_buttons2)

player_components = [_player_action_row1, _player_action_row2]


_queue_buttons = [
    create_button(style=ButtonStyle.gray,
                  emoji="⬅",
                  custom_id="queue_prev"),

    create_button(style=ButtonStyle.gray,
                  emoji="➡",
                  custom_id="queue_next")
]

queue_components = [create_actionrow(*_queue_buttons)]

# TODO раскидать бота по файлам и перенести сюда @client.event \\ on_component(...)
