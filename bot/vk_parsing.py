from typing import Optional, Union

from vkwave.api.methods._error import APIError

from .config import TokenConfig
from vkwave.api import API

from vkwave.client import AIOHTTPClient

client = AIOHTTPClient()
api = API(clients=client, tokens=TokenConfig.VK_ME_TOKEN, api_version="5.90")


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
            "access_key": access_key,
        }
    return {"owner_id": int(owner_id), "playlist_id": int(playlist_id)}


def get_thumb(track_info: dict):
    if "album" not in track_info or "thumb" not in track_info["album"]:
        return "https://i.pinimg.com/originals/22/38/18/2238189ed157972bec6a29413f2c23ca.png"
    return track_info["album"]["thumb"]["photo_270"]


def get_track_info(
    item: dict, requester: Optional[int] = None
) -> dict[str, Union[str, int]]:
    image = get_thumb(item)
    name = f"{item['title']} - {item['artist']}"
    item["url"] = item["url"].split("?extra")[0]
    track_id = f"{item['owner_id']}_{item['id']}"

    return {
        "url": item["url"],
        "name": name,
        "duration": item["duration"],
        "thumb": image,
        "id": track_id,
        "requester": requester,
    }


async def get_audio(url: str, requester: int) -> Optional[list]:
    # https://vk.com/music/album/-2000775086_8775086_3020c01f90d96ecf46
    # https://vk.com/audios283345310?z=audio_playlist-2000775086_8775086%2F3020c01f90d96ecf46

    # https://vk.com/music/playlist/283345310_50
    # https://vk.com/audios283345310?z=audio_playlist283345310_50
    offset = 0
    params = optimize_link(link=url)
    max_count = 6000
    first = True
    items = []
    all_items = []
    while items or first:
        params.update({"count": max_count, "offset": offset})
        first = False
        response = await api.get_context().api_request(
            method_name="audio.get", params=params
        )
        items = response["response"].get("items")
        offset += max_count
        all_items.extend(items)
    if not all_items:
        return
    return [get_track_info(item, requester) for item in all_items]


async def find_tracks_by_name(requester: int, name: str, count: int) -> Optional[list]:
    result = await api.get_context().api_request(
        method_name="audio.search", params={"q": name, "count": count}
    )
    items = result["response"].get("items")
    if items is None or len(items) == 0:
        return
    return [get_track_info(item, requester) for item in items[:count]]


async def get_tracks_by_id(tracks_ids: list[str]):
    limit = 500
    if len(tracks_ids) > limit:
        audios = []
        start = 0
        end = limit
        while len(audios) <= len(tracks_ids) // limit:
            # TODO вк возвращает не все треки
            # temp = tracks_ids[start:end]
            # print(f"{len(temp)=}")
            audios.append(",".join(tracks_ids[start:end]))
            start += limit
            if end + limit > len(tracks_ids):
                end = len(tracks_ids) + 1
            else:
                end += limit

    else:
        audios = [",".join(tracks_ids)]

    tracks = []
    for audios_temp in audios:
        result = await api.get_context().api_request(
            method_name="audio.getById", params={"audios": audios_temp}
        )
        items = result["response"]
        # print(f"{len(items)=}")
        for item in items:
            track = get_track_info(item, None)
            tracks.append(track)
    return tracks


# PLAYLISTS PARSING
def parse_playlist_info(playlist_dict: dict, requester: Optional[int] = None):
    title = playlist_dict["title"]
    if len(title) > 50:
        title = f"{title[:50]} ..."
    description = playlist_dict["description"]
    if len(description) > 50:
        description = f"{description[:50]} ..."
    return {
        "id": playlist_dict["id"],
        "owner_id": playlist_dict["owner_id"],
        "title": title,
        "description": description,
        "access_key": playlist_dict["access_key"],
        "requester": requester,
    }


async def find_playlists_by_name(requester: int, playlist_name: str, count: int):
    result = await api.get_context().api_request(
        method_name="audio.searchPlaylists", params={"q": playlist_name, "count": count}
    )
    items = result["response"].get("items")
    if items is None or len(items) == 0:
        return
    return [parse_playlist_info(item, requester) for item in items[:count]]


async def get_playlist_tracks(parsed_playlist: dict, requester: Optional[int] = None):
    result = await api.get_context().api_request(
        method_name="audio.get",
        params={
            "owner_id": parsed_playlist["owner_id"],
            "playlist_id": parsed_playlist["id"],
            "access_key": parsed_playlist["access_key"],
        },
    )
    tracks = result["response"]["items"]
    return [get_track_info(track, requester) for track in tracks]


# USER SAVED AUDIO
async def get_user_saved_tracks(user_name: str, requester: int):
    try:
        user = await api.get_context().api_request(
            method_name="users.get",
            params={"user_ids": user_name},
        )
    except APIError:
        return
    except Exception as err:
        print("user get error: ", err)
        return
    user_id = int(user["response"][0]["id"])
    try:
        result = await api.get_context().api_request(
            method_name="audio.get", params={"owner_id": user_id, "count": 9999}
        )
    except APIError:
        return
    except Exception as err:
        print("user audio error: ", err)  # TODO логгирование
        return
    items = result["response"]["items"]
    tracks = [get_track_info(item, requester) for item in items]
    return tracks
