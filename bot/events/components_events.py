from discord_slash import ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow

player_components = [
    create_actionrow(create_button(style=ButtonStyle.gray, emoji="🔀", custom_id="shuffle"),
                     create_button(style=ButtonStyle.gray, emoji="⏪", custom_id="previous"),
                     create_button(style=ButtonStyle.gray, emoji="▶", custom_id="play_pause"),
                     create_button(style=ButtonStyle.gray, emoji="⏩", custom_id="next"),
                     create_button(style=ButtonStyle.gray, emoji="⏹", custom_id="stop")),
    create_actionrow(create_button(style=ButtonStyle.gray, emoji="🔁", custom_id="loop"),
                     create_button(style=ButtonStyle.gray, emoji="📑", custom_id="queue"))
]

queue_components = [create_actionrow(
    create_button(style=ButtonStyle.gray, emoji="⬅", custom_id="queue_prev"),
    create_button(style=ButtonStyle.gray, emoji="➡", custom_id="queue_next"),
)]

# TODO раскидать бота по файлам и перенести сюда @client.event \\ on_component(...)
