import asyncio
from typing import Union

from cfg import VK_ME_TOKEN
from vkwave.api import API

from vkwave.client import AIOHTTPClient

from utils.custom_exceptions import NoTracksFound

client = AIOHTTPClient()
api = API(clients=client, tokens=VK_ME_TOKEN, api_version="5.90")


def optimize_link(link: str) -> dict:
    access_key = None
    if link.startswith("https://vk.com/music/album/"):
        temp = link.split("/album/")[1]
        owner_id, playlist_id, access_key = temp.split("_")
    elif link.startswith("https://vk.com/music/playlist/"):
        temp = link.split("/playlist/")[1]
        if len(temp := temp.split("_")) > 2:
            owner_id, playlist_id, access_key = temp
        else:
            owner_id, playlist_id = temp
    else:
        temp = link.split("audio_playlist")[1]
        owner_id, temp2 = temp.split("_")
        if len(temp2.split("%")) > 1:
            playlist_id, access_key = temp2.split("%")
        else:
            playlist_id = temp2
    if access_key is not None:
        return {
            "owner_id": int(owner_id),
            "playlist_id": int(playlist_id),
            "access_key": access_key
        }
    else:
        return {
            "owner_id": int(owner_id),
            "playlist_id": int(playlist_id)
        }


def get_thumb(track_info: dict):
    if "album" not in track_info or "thumb" not in track_info["album"]:
        return "https://cdn.discordapp.com/attachments/248145752352620546/876452830049894451/MHUm5Vaje2M.png"
    return track_info["album"]["thumb"]["photo_270"]


def get_track_info(item, requester):
    image = get_thumb(item)
    name = f"{item['title']} - {item['artist']}"
    item["url"] = item["url"].split("?extra")[0]
    track_id = f"{item['owner_id']}_{item['id']}"
    return {
        "url": item["url"],
        "name": name,
        "duration": item["duration"],
        "thumb": image,
        "requester": requester,
        "id": track_id
    }


async def get_audio(url: str, requester) -> list:
    # https://vk.com/music/album/-2000775086_8775086_3020c01f90d96ecf46
    # https://vk.com/audios283345310?z=audio_playlist-2000775086_8775086%2F3020c01f90d96ecf46

    # https://vk.com/music/playlist/283345310_50
    # https://vk.com/audios283345310?z=audio_playlist283345310_50
    params = optimize_link(link=url)

    tracks = []
    response = await api.get_context().api_request(method_name="audio.get", params=params)
    for item in response["response"]["items"]:

        track = get_track_info(item, requester)
        tracks.append(track)
    return tracks


async def get_single_audio(requester, name: str, count: int = 1) -> Union[dict, list]:
    result = await api.get_context().api_request(
        method_name="audio.search", params={"q": name, "count": count}
    )
    items = result["response"]["items"]
    if len(items) == 0:
        raise NoTracksFound(f"No tracks matches request {name}")
    if count == 1:
        item = items[0]

        track = get_track_info(item, requester)
        return track
    items_list = []
    for item in items[:count]:

        track = get_track_info(item, requester)
        items_list.append(track)
    return items_list


async def get_tracks_by_id(tracks_ids: list[str]):
    audios = ",".join(tracks_ids)
    result = await api.get_context().api_request(
        method_name="audio.getById", params={"audios": audios}
    )
    items = result["response"]
    tracks = []
    for item in items:
        track = get_track_info(item, None)
        tracks.append(track)
    return tracks
