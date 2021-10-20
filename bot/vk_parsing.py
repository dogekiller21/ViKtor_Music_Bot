from typing import Optional

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


def get_track_info(item: dict, requester: Optional[int]):
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
        "id": track_id,
    }


async def get_audio(url: str, requester) -> list:
    # https://vk.com/music/album/-2000775086_8775086_3020c01f90d96ecf46
    # https://vk.com/audios283345310?z=audio_playlist-2000775086_8775086%2F3020c01f90d96ecf46

    # https://vk.com/music/playlist/283345310_50
    # https://vk.com/audios283345310?z=audio_playlist283345310_50
    params = optimize_link(link=url)

    tracks = []
    response = await api.get_context().api_request(
        method_name="audio.get", params=params
    )
    for item in response["response"]["items"]:
        track = get_track_info(item, requester)
        tracks.append(track)
    return tracks


async def find_tracks_by_name(
        requester: int, name: str, count: int = 25
) -> Optional[list]:
    result = await api.get_context().api_request(
        method_name="audio.search", params={"q": name, "count": count}
    )
    items = result["response"].get("items")
    if items is None:
        return

    return [get_track_info(item, requester) for item in items[:count]]


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


def parse_playlist_info(playlist_dict: dict):
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
    }


async def get_playlists_by_name(playlist_name: str, count: int = 25):
    result = await api.get_context().api_request(
        method_name="audio.searchPlaylists",
        params={"q": playlist_name,
                "count": count}
    )
    items = result["response"].get("items")
    if items is None:
        return
    return [parse_playlist_info(item) for item in items[:count]]


async def get_playlist_tracks(parsed_playlist: dict):
    result = await api.get_context().api_request(
        method_name="audio.get",
        params={"owner_id": parsed_playlist["owner_id"],
                "playlist_id": parsed_playlist["id"],
                "access_key": parsed_playlist["access_key"]}
    )
    tracks = result["response"]["items"]
    return [get_track_info(track, None) for track in tracks]


async def get_user_saved_tracks(user_name: str, requester):
    try:
        user = await api.get_context().api_request(
            method_name="users.get",
            params={"user_ids": user_name,
                    "fields": "uid,first_name,last_name"}
        )
    except APIError:
        return
    except Exception as err:
        print("user get error: ", err)
        return
    user_id = int(user["response"][0]["id"])
    try:
        result = await api.get_context().api_request(
            method_name="audio.get",
            params={"owner_id": user_id,
                    "count": 9999}
        )
    except APIError:
        return
    except Exception as err:
        print("user audio error: ", err)  # TODO логгирование
        return
    items = result["response"]["items"]
    tracks = [get_track_info(item, requester) for item in items]
    return tracks
