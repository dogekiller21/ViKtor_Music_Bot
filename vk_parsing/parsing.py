import logging
from typing import Optional

from vkwave.api import API
from vkwave.api.methods._error import APIError
from vkwave.client import AIOHTTPClient

from config import TokenConfig
from vk_parsing.constants import ApiMethods
from vk_parsing.exceptions import (
    NoTracksParsedException,
    PlaylistParsingApiError,
    SingleTrackParsingApiError,
)
from vk_parsing.models import TrackInfo, LinkParams, AutocompleteTrackInfo


logger = logging.getLogger(__name__)


class VkParsingClient:
    def __init__(self):
        self.api: API | None = None
        self.client: AIOHTTPClient | None = None

    async def init_client(self):
        self.client = AIOHTTPClient()
        self.api = API(
            clients=self.client, tokens=TokenConfig.VK_TOKEN, api_version="5.90"
        )

    async def _make_request(
        self, method_name: str, params: dict = None, get_items: bool = True
    ) -> list[dict]:
        if self.api is None:
            logger.info("VK API client was not initialized until now")
            await self.init_client()
        if params is None:
            params = {}
        response = await self.api.get_context().api_request(
            method_name=method_name,
            params=params,
        )
        result = response.get("response")
        if get_items:
            return result.get("items")
        return result

    async def search_tracks_by_title(
        self, title: str
    ) -> list[AutocompleteTrackInfo] | None:
        items = await self._make_request(
            method_name=ApiMethods.AUDIO_SEARCH, params={"q": title, "count": 25}
        )
        if not items:
            return
        tracks = AutocompleteTrackInfo.parse_response_list(items_list=items)
        if not tracks:
            return
        return tracks

    async def get_track_by_id(self, track_id: str) -> Optional[TrackInfo]:
        try:
            track = (
                await self._make_request(
                    method_name=ApiMethods.AUDIO_GET_BY_ID,
                    params={"audios": track_id},
                    get_items=False,
                )
            )[0]
        except APIError as e:
            logger.info(f"API error for {track_id}: {e}")
            raise SingleTrackParsingApiError
        else:
            return TrackInfo.from_response(item_dict=track)

    async def get_playlist_tracks(self, url: str) -> list[TrackInfo] | None:
        request_params = LinkParams.from_input_url(
            url=url,
        ).to_dict()
        try:
            items = await self._make_request(
                method_name=ApiMethods.AUDIO_GET, params=request_params
            )
        except APIError as e:
            logger.info(f"API error while parsing playlist {url}: {e}")
            raise PlaylistParsingApiError
        # items = await self._make_request(
        #     method_name="audio.getPlaylistById", params=request_params
        # ) # если нужна будет инфа без треков
        if not items:
            raise NoTracksParsedException
        tracks = TrackInfo.parse_response_list(items_list=items)
        if not tracks:
            raise NoTracksParsedException
        return tracks


async def get_client() -> VkParsingClient:
    vk_client = VkParsingClient()
    await vk_client.init_client()
    # await vk_client.search_tracks_by_name("Fantastic Blame My Youth")
    # tracks = await vk_client.get_playlist_tracks(
    #     "https://vk.com/music/playlist/99883438_53060307_f46a1aba7e616001c3"
    # )
    # print(tracks[0])
    return vk_client
