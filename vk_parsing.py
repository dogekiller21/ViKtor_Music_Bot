from cfg import VK_ME_TOKEN
from vkwave.api import API

from vkwave.client import AIOHTTPClient


client = AIOHTTPClient()

api = API(clients=client, tokens=VK_ME_TOKEN, api_version="5.90")


async def get_audio(url: str) -> list:
    # TODO ссылки могут быть разные

    # https://vk.com/music/album/-2000775086_8775086_3020c01f90d96ecf46
    # https://vk.com/audios283345310?z=audio_playlist-2000775086_8775086%2F3020c01f90d96ecf46

    # https://vk.com/music/playlist/283345310_50
    # https://vk.com/audios283345310?z=audio_playlist283345310_50
    url_pars = url.split("audio_playlist")[1]
    params = {}
    owner_id, playlist_id = url_pars.split("_")
    playlist_id = playlist_id.split("%")[0]
    params["owner_id"] = int(owner_id)
    if (len(spl := playlist_id.split("%"))) > 1:
        key = spl[1]
        params["access_key"] = key

    params["playlist_id"] = int(playlist_id)
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
