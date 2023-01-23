from vkwave.client import AIOHTTPClient
from vkwave.api import API

from utils.config import TokenConfig
from vk_parsing.utils import optimize_link, parse_track_info

client = AIOHTTPClient()
api = API(clients=client, tokens=TokenConfig.VK_TOKEN, api_version="5.90")


async def find_tracks_by_name(name: str):
    result = await api.get_context().api_request(
        method_name="audio.search", params={"q": name, "count": 10}
    )
    items = result["response"].get("items")
    if items is None or len(items) == 0:
        return
    return [parse_track_info(item) for item in items]


async def get_request(url: str):
    request_params = optimize_link(url)
    response = await api.get_context().api_request(
        method_name="audio.get", params=request_params,
    )
    request_items = response["response"].get("items")
    if request_items is None or len(request_items) == 0:
        return
    return [parse_track_info(item) for item in request_items]
