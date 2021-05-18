import json
from dataclasses import dataclass
from typing import Union, List, Optional

import discord
from discord import Forbidden, NotFound, HTTPException

from utils import embed_utils
from utils.custom_exceptions import EmptyQueue


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


def write_tracks(guild_id, track_list: list, index: Optional[int] = 0):
    info = get_from_file()

    info["guilds"][str(guild_id)] = {
        "tracks": track_list,
        "now_playing_index": index
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


def get_pages(guild_id: int, page: int) -> tuple:
    tracks_info = get_tracks(guild_id)

    tracks, now_playing = tracks_info.tracks, tracks_info.now_playing

    if (len(tracks) % 10) == 0:
        pages = int(len(tracks) / 10)
    else:
        pages = int((len(tracks) / 10)) + 1

    if page is None:
        if ((now_playing + 1) % 10) != 0:
            page = (now_playing + 1) // 10 + 1
        else:
            page = (now_playing + 1) // 10

    return page, pages


def get_queue_data():
    with open("data/queue-messages.json", "r", encoding="utf-8") as file:
        return json.load(file)


def save_queue_data(data):
    with open("data/queue-messages.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def add_queue_message(guild_id, message: discord.Message):
    data = get_queue_data()
    if str(guild_id) in data["data"]:
        data["data"][str(guild_id)].append(message.id)
    else:
        data["data"][str(guild_id)] = [message.id, ]

    save_queue_data(data)


def get_queue_messages(guild_id):
    data = get_queue_data()
    if str(guild_id) in data["data"]:
        return data["data"][str(guild_id)]


def clear_queue_info(guild_id):
    data = get_queue_data()
    try:
        del data["data"][str(guild_id)]
        save_queue_data(data)
    except KeyError:
        pass


def clear_all_queue_info():
    save_queue_data({
        "data": {}
    })


async def delete_queue_messages(ctx):
    messages = get_queue_messages(ctx.guild.id)
    for message_id in messages:
        try:
            message = await ctx.fetch_message(message_id)
            await message.delete()
        except (Forbidden, NotFound, HTTPException):
            pass


async def queue_message_update(ctx):
    try:
        queue_embed = embed_utils.create_queue_embed(ctx)
    except EmptyQueue:
        return
    queue_messages = get_queue_messages(ctx.guild.id)
    if queue_messages is not None:
        for message_id in reversed(queue_messages):
            message = await ctx.fetch_message(message_id)
            await message.edit(embed=queue_embed)
