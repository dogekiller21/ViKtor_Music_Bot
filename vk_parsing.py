from asyncio import StreamReader

from cfg import VK_ME_TOKEN
from vkwave.api import API
from vkwave.bots import SimpleLongPollUserBot
import asyncio
import os
import requests
from vkwave.client import AIOHTTPClient


client = AIOHTTPClient()

api = API(clients=client, tokens=VK_ME_TOKEN, api_version="5.90")


async def get_audio(api_: API, url: str, guild_name="123"):
    # https://vk.com/audios283345310?section=all&z=audio_playlist283345310_42
    url_pars = url.split("audio_playlist")[1]
    params = {}
    owner_id, playlist_id = url_pars.split("_")
    params["owner_id"] = int(owner_id)
    key = playlist_id.split("%")

    if key == playlist_id.split("%"):
        params["access_key"] = key

    params["playlist_id"] = int(playlist_id)
    tracks = []
    response = await api_.get_context().api_request(method_name="audio.get", params=params)

    if not os.path.exists(guild_name):
        os.mkdir(guild_name)
    for i, item in enumerate(response["response"]["items"]):

        r: StreamReader = await client.http_client.raw_request(url=item["url"], method="get")

        track_info = {
            "name": f"{item['artist']} {item['title']}",
            "duration": item["duration"],

        }
        if "/" in track_info["name"]:
            track_info["name"] = track_info["name"].replace("/", "")
        with open(f"{guild_name}/{i+1}_{track_info['name']}.mp3", "wb") as file:
            file.write(await r.read())

        tracks.append(track_info)
    for track in tracks:
        print(track)
    # TODO

loop = asyncio.get_event_loop()

loop.run_until_complete(get_audio(api, "https://vk.com/audios571496731?section=playlists&z=audio_playlist571496731_4"))
