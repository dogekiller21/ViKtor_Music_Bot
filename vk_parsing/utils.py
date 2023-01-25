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
        owner_id, temp = temp.split("_")
        if len(temp.split("%")) > 1:
            playlist_id, access_key = temp.split("%")
        else:
            playlist_id = temp
    if access_key is not None:
        return {
            "owner_id": int(owner_id),
            "playlist_id": int(playlist_id),
            "access_key": access_key,
        }
    return {"owner_id": int(owner_id), "playlist_id": int(playlist_id)}


def get_thumb(track: dict):
    if "album" not in track or "thumb" not in track["album"]:
        return "https://i.pinimg.com/564x/63/43/d6/6343d6f55d4b22cdeea0de8f9cb6ebab.jpg"
    return track["album"]["thumb"]["photo_270"]


def parse_track_info(item: dict):
    image = get_thumb(item)
    name = f"{item['title']} - {item['artist']}"
    item["url"] = item["url"].split("?extra")[0]
    track_id = f"{item['owner_id']}_{item['id']}"

    return {
        "url": item["url"],
        "name": name,
        "duration": item["duration"],
        "thumbnail": image,
        "id": track_id,
    }


def time_format(seconds):
    seconds = seconds
    d = seconds // (3600 * 24)
    h = seconds // 3600 % 24
    m = seconds % 3600 // 60
    s = seconds % 3600 % 60
    if d > 0:
        return f"{d:02d}D {h:02d}:{m:02d}:{s:02d}"
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
