from dataclasses import dataclass
from typing import Optional, Union

from vk_parsing.constants import DEFAULT_THUMB_URL, UrlHeaders
from vk_parsing.exceptions import IncorrectPlaylistUrlException


@dataclass
class LinkParams:
    owner_id: int
    playlist_id: int
    access_key: str | None = None
    count: int = 9999

    def to_dict(self):
        if self.access_key is not None:
            return {
                "owner_id": self.owner_id,
                "playlist_id": self.playlist_id,
                "access_key": self.access_key,
                "count": self.count,
            }
        return {
            "owner_id": self.owner_id,
            "playlist_id": self.playlist_id,
            "count": self.count,
        }

    @classmethod
    def from_input_url(cls, url: str) -> Optional["LinkParams"]:
        """
        (owner_id: -2000421087, playlist_id: 2421087, access_key: 2F67ad8127e3ed2ac574)

        Possible links:

        1. Copied from browser


        https://vk.com/im?z=audio_playlist-2000421087_2421087%2F67ad8127e3ed2ac574

        2. Copied album link

        https://vk.com/music/album/-2000421087_2421087_67ad8127e3ed2ac574

        3. Copied playlist link (access_key is the 3rd element with "_" sep)

        https://vk.com/music/playlist/288429925_7

        :param url: str
        :return: LinkParams
        """
        access_key = None
        if url.startswith(UrlHeaders.ALBUM_HEADER):
            owner_id, playlist_id, access_key = url.split(UrlHeaders.ALBUM_HEADER)[
                1
            ].split("_")
        elif url.startswith(UrlHeaders.PLAYLIST_HEADER):
            raw_data = url.split(UrlHeaders.PLAYLIST_HEADER)[1].split("_")
            if len(raw_data) > 2:
                owner_id, playlist_id, access_key = raw_data
            else:
                owner_id, playlist_id = raw_data
        elif UrlHeaders.BAD_AUDIO_PLAYLIST_PARAM in url:
            raw_data = url.split(UrlHeaders.BAD_AUDIO_PLAYLIST_PARAM)[1].split("_")
            owner_id, tmp = raw_data
            tmp = tmp.split("%")
            if len(tmp) > 1:
                playlist_id, access_key = tmp
            else:
                playlist_id = tmp
        else:
            raise IncorrectPlaylistUrlException
        return cls(
            owner_id=int(owner_id),
            playlist_id=int(playlist_id),
            access_key=access_key,
        )


@dataclass
class AutocompleteTrackInfo:
    artist: str
    title: str
    vk_id: str
    duration: str

    @staticmethod
    def parse_duration(seconds: int) -> str:
        d = seconds // (3600 * 24)
        h = seconds // 3600 % 24
        m = seconds % 3600 // 60
        s = seconds % 3600 % 60
        if d > 0:
            return f"{d:02d}D {h:02d}:{m:02d}:{s:02d}"
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @classmethod
    def from_response(cls, item_dict: dict) -> "AutocompleteTrackInfo":
        return cls(
            artist=item_dict.get("artist"),
            title=item_dict.get("title"),
            vk_id=f"{item_dict.get('owner_id')}_{item_dict.get('id')}",
            duration=cls.parse_duration(item_dict.get("duration")),
        )

    @classmethod
    def parse_response_list(
        cls, items_list: list[dict]
    ) -> list[Union["AutocompleteTrackInfo", "TrackInfo"]]:
        return [cls.from_response(item) for item in items_list if item["url"]]


@dataclass
class TrackInfo(AutocompleteTrackInfo):
    mp3_url: str
    thumb_url: str

    def get_full_name(self, max_length: int = 40):
        full_name = f"{self.artist} - {self.title}"
        if len(full_name) >= max_length:
            full_name = f"{full_name[:max_length]}..."
        return full_name

    @staticmethod
    def get_thumb_url(item_dict: dict):
        if "album" not in item_dict or "thumb" not in item_dict.get("album"):
            return DEFAULT_THUMB_URL
        return item_dict.get("album").get("thumb").get("photo_270")

    @classmethod
    def from_response(cls, item_dict: dict) -> "TrackInfo":
        return cls(
            artist=item_dict.get("artist"),
            title=item_dict.get("title"),
            vk_id=f"{item_dict.get('owner_id')}_{item_dict.get('id')}",
            duration=cls.parse_duration(item_dict.get("duration")),
            mp3_url=item_dict.get("url"),
            thumb_url=cls.get_thumb_url(item_dict),
        )
