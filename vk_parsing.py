from cfg import VK_ME_TOKEN
from vkwave.api import API

from vkwave.client import AIOHTTPClient


client = AIOHTTPClient()

api = API(clients=client, tokens=VK_ME_TOKEN, api_version="5.90")


async def get_audio(url: str) -> list:
    # https://vk.com/audios578716413?z=audio_playlist-2000620821_1620821%2F18e2571a420a5b9d6b
    # https://vk.com/audios283345310?section=all&z=audio_playlist283345310_42
    url_pars = url.split("audio_playlist")[1]
    params = {}
    owner_id, playlist_id = url_pars.split("_")
    playlist_id = playlist_id.split("%")[0]
    params["owner_id"] = int(owner_id)
    key = playlist_id.split("%")

    if key == playlist_id.split("%"):
        params["access_key"] = key

    params["playlist_id"] = int(playlist_id)
    tracks = []
    response = await api.get_context().api_request(method_name="audio.get", params=params)
    for item in response["response"]["items"]:
        tracks.append(item["url"])
    return tracks
    # TODO dodelat

