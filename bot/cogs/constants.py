from discord_slash.utils.manage_components import create_select_option

VK_URL_PREFIX = "vk.com/"

FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                  "options": "-vn"}

timeout_option = create_select_option(
    label="Время вышло",
    value="timed_out",
    emoji="⏱",  # ⌛
    default=True
)


class CustomColors:
    GREEN_COLOR = 0x5CC347
    BROWN_COLOR = 0xC27746
    ERROR_COLOR = 0xE74C3C
    MUSIC_COLOR = 0xFFA033
    INFO_COLOR = 0x3489EB
