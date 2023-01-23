
class CustomColors:
    ERROR_COLOR = 0xE74C3C
    MUSIC_COLOR = 0x7532a8
    INFO_COLOR = 0xffaf5e


DEBUG_GUILDS = []

VK_URL_PREFIX = "vk.com/"

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

REPEAT_MODES_STR = {
    0: "None",
    1: "One",
    2: "All"
}

REPEAT_MODES_EMOJIS = {
    0: "🔁",
    1: "🔂",
    2: "🔁",
}


class PlayerEmojis:
    BACK_EMOJI = "⏪"
    PAUSE_EMOJI = "⏯"
    SKIP_EMOJI = "⏩"
    REPEAT_EMOJI = "🔂"
    VOL_UP_EMOJI = "🔊"
    VOL_DOWN_EMOJI = "🔉"
    STOP_EMOJI = "⏹"
