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
        owner_id, playlist_id = temp.split("_")
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


async def get_audio(url: str) -> list:
    # https://vk.com/music/album/-2000775086_8775086_3020c01f90d96ecf46
    # https://vk.com/audios283345310?z=audio_playlist-2000775086_8775086%2F3020c01f90d96ecf46

    # https://vk.com/music/playlist/283345310_50
    # https://vk.com/audios283345310?z=audio_playlist283345310_50
    params = optimize_link(link=url)

    tracks = []
    response = await api.get_context().api_request(method_name="audio.get", params=params)
    for item in response["response"]["items"]:
        name = f"{item['title']} - {item['artist']}"
        tracks.append({
            "url": item["url"],
            "name": name,
            "duration": item["duration"]
        }
        )
    return tracks


async def get_single_audio(name: str) -> dict:
    result = await api.get_context().api_request(
        method_name="audio.search", params={"q": name, "count": 1}
    )
    items = result["response"]["items"]
    if len(items) == 0:
        raise NoTracksFound(f"No tracks matches request {name}")
    item = items[0]
    name = f"{item['title']} - {item['artist']}"
    return {
        "url": item["url"],
        "name": name,
        "duration": item["duration"]
    }
