import copy
import json
import datetime

from utils.custom_exceptions import ToManyPlaylists


def get_playlists():
    with open("playlists.json", "r", encoding="utf-8") as file:
        return json.load(file)


def save_playlists(data):
    with open("playlists.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_new_playlist(guild_id, playlist: list):
    playlist_1 = copy.deepcopy(playlist)
    [item.pop("requester", 0) for item in playlist_1]

    playlists = get_playlists()

    guild_id = str(guild_id)
    guild_playlists = playlists[guild_id] if guild_id in playlists else {}

    length = len(guild_playlists)
    if length >= 10:
        raise ToManyPlaylists
    name = f"Playlist {length + 1}"

    date = datetime.date.today()
    guild_playlists[name] = {"tracks": playlist_1,
                             "date": date.toordinal()}
    playlists[guild_id] = guild_playlists

    save_playlists(playlists)
    return name


def get_single_guild_playlist(guild_id):
    playlists = get_playlists()
    try:
        return playlists[str(guild_id)]
    except KeyError:
        return
