import logging
from typing import Optional, Union

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from lyrics.config import GENIUS_TOKEN
from lyrics.constants import BASE_API_URL, BASE_URL
from lyrics.exceptions import SongNotFoundException, LyricsParsingError


class LyricsParser:
    def __init__(self):
        self.session: ClientSession | None = None

    async def make_request(
        self, url: str, headers: dict | None = None, return_json: bool = True
    ) -> Union[dict, str]:
        if self.session is None:
            self.session = ClientSession()
            logging.info("Session for lyrics parser was not initialized until now")
        async with self.session.get(url=url, headers=headers) as resp:
            if resp.status != 200:
                logging.warning(f"{resp.status} while fetching {url} in lyrics parser")
                raise LyricsParsingError()
            if return_json:
                return await resp.json()
            return await resp.text()

    async def _parse_lyrics(self, lyrics_path: str):
        soup = BeautifulSoup(
            await self.make_request(url=f"{BASE_URL}{lyrics_path}", return_json=False),
            "lxml",
        )
        return soup.find("div", attrs={"data-lyrics-container": True}).get_text(
            separator="\n\n", strip=True
        )

    async def search(self, q: str) -> Optional[str]:
        json_data: dict = await self.make_request(
            url=f"{BASE_API_URL}/search?q={q}",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"},
            return_json=True,
        )
        if json_data is None:
            return
        songs = [
            hit["result"]
            for hit in json_data["response"]["hits"]
            if hit["type"] == "song"
        ]
        if not songs:
            raise SongNotFoundException()
        lyrics_path = songs[0]["path"]

        return await self._parse_lyrics(lyrics_path=lyrics_path)
