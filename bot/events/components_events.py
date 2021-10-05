from discord_slash import ComponentContext, ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow

from bot.bot import client

player_buttons1 = [
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

player_buttons2 = [
    create_button(style=ButtonStyle.gray,
                  emoji="🔁",
                  custom_id="loop"),

    create_button(style=ButtonStyle.gray,
                  emoji="📑",
                  custom_id="queue"),
]
player_action_row1 = create_actionrow(*player_buttons1)
player_action_row2 = create_actionrow(*player_buttons2)

player_components = [player_action_row1, player_action_row2]

# TODO раскидать бота по файлам и перенести сюда @client.event \\ on_component(...)
