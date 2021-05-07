import json
from typing import Union


def get_tracks(guild_id) -> Union[dict, None]:
    with open("tracks.json", "r", encoding="utf-8") as file:
        info = json.load(file)["guilds"]
        guild_id = str(guild_id)

        if guild_id in info:
            tracks = info[guild_id]["tracks"]
            not_playing = info[guild_id]["now_playing_index"]
            return {
                "tracks": tracks,
                "now_playing": not_playing
            }
        else:
            return


def write_tracks(guild_id, track_list: list):
    with open("tracks.json", "r", encoding="utf-8") as file:
        info = json.load(file)
        guild_id = str(guild_id)

        info["guilds"][guild_id] = {
            "tracks": track_list,
            "now_playing_index": 0
        }

    with open("tracks.json", "w", encoding="utf-8") as file:
        json.dump(info, file, indent=2, ensure_ascii=False)


def add_track(guild_id, track: dict):
    with open("tracks.json", "r", encoding="utf-8") as file:
        info = json.load(file)
        if str(guild_id) in info["guilds"]:
            guild_info = info["guilds"][str(guild_id)]
        else:
            info["guilds"][str(guild_id)] = {
                "tracks": [],
                "now_playing_index": 0
            }
            guild_info = info["guilds"][str(guild_id)]

        guild_info["tracks"].append(track)

    with open("tracks.json", "w", encoding="utf-8") as file:
        json.dump(info, file, indent=2, ensure_ascii=False)


def delete_info(guild_id):
    with open("tracks.json", "r", encoding="utf-8") as file:
        info = json.load(file)
        try:
            del info["guilds"][str(guild_id)]
        except KeyError:
            pass
    with open("tracks.json", "w", encoding="utf-8") as file:
        json.dump(info, file, indent=2, ensure_ascii=False)


def change_index(guild_id, index: int):
    with open("tracks.json", "r", encoding="utf-8") as file:
        info = json.load(file)
        info["guilds"][str(guild_id)]["now_playing_index"] = index

    with open("tracks.json", "w", encoding="utf-8") as file:
        json.dump(info, file, ensure_ascii=False, indent=2)


def clear_info():
    with open("tracks.json", "w", encoding="utf-8") as file:
        info = {
            "guilds": {}
        }
        json.dump(info, file, ensure_ascii=False, indent=2)
