import json
from dataclasses import dataclass
from typing import Union, List


@dataclass
class SingleTrackInfo:
    url: str
    name: str
    duration: int


@dataclass
class AllTracksInfo:
    tracks: List[SingleTrackInfo]
    now_playing: int


def get_from_file():
    with open("tracks.json", "r", encoding="utf-8") as file:
        return json.load(file)


def write_to_file(data):
    with open("tracks.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_tracks(guild_id) -> Union[AllTracksInfo, None]:
    info = get_from_file()["guilds"]
    guild_id = str(guild_id)

    if guild_id in info:
        tracks = info[guild_id]["tracks"]
        now_playing = info[guild_id]["now_playing_index"]
        tracks = [SingleTrackInfo(**track) for track in tracks]
        all_tracks = AllTracksInfo(tracks, now_playing)

        return all_tracks
    else:
        return


def write_tracks(guild_id, track_list: list):
    info = get_from_file()

    guild_id = str(guild_id)

    info["guilds"][guild_id] = {
        "tracks": track_list,
        "now_playing_index": 0
    }

    write_to_file(info)


def add_track(guild_id, track: dict):
    info = get_from_file()

    if str(guild_id) in info["guilds"]:
        guild_info = info["guilds"][str(guild_id)]
    else:
        info["guilds"][str(guild_id)] = {
            "tracks": [],
            "now_playing_index": 0
        }
        guild_info = info["guilds"][str(guild_id)]

    guild_info["tracks"].append(track)

    write_to_file(info)


def delete_info(guild_id):
    info = get_from_file()

    try:
        del info["guilds"][str(guild_id)]
    except KeyError:
        pass

    write_to_file(info)


def delete_single_track(guild_id, index: int):
    info = get_from_file()

    try:
        del info["guilds"][str(guild_id)]["tracks"][index - 1]

    except IndexError:
        pass

    write_to_file(info)


def change_index(guild_id, index: int):
    info = get_from_file()
    info["guilds"][str(guild_id)]["now_playing_index"] = index

    write_to_file(info)


def clear_info():
    info = {
        "guilds": {}
    }

    write_to_file(info)
