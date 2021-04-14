from cfg import VK_ME_TOKEN
from vkwave.bots import SimpleLongPollUserBot
import asyncio
import os
import requests

user = SimpleLongPollUserBot(tokens=VK_ME_TOKEN)


async def get_audio(bot: SimpleLongPollUserBot, url: str, guild_name="123"):
    # https://vk.com/audios283345310?section=all&z=audio_playlist283345310_42
    url_pars = url.split("audio_playlist")[1]
    params = {}
    owner_id, playlist_id = url_pars.split("_")
    params["owner_id"] = int(owner_id)

    if key := playlist_id.split("%"):
        params["access_key"] = key

    params["playlist_id"] = int(playlist_id)
    tracks = []
    response = await user.api_context.api_request(method_name="audio.get", params=params)
    os.mkdir(f"{guild_name}")
    for i, item in enumerate(response["response"]["items"]):

        r = requests.get(item["url"])

        track_info = {
            "name": f"{item['artist']} {item['title']}",
            "duration": item["duration"],

        }
        if "/" in track_info["name"]:
            track_info["name"] = track_info["name"].replace("/", "")
        with open(f"{guild_name}/{i+1}_{track_info['name']}.m3u8", "wb") as file:
            file.write(r.content)

        tracks.append(track_info)
    for track in tracks:
        print(track)
    # TODO

loop = asyncio.get_event_loop()

loop.run_until_complete(get_audio(user, "https://vk.com/audios283345310?section=all&z=audio_playlist283345310_42"))
