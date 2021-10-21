import json

from bot._types import JSON_DATA
from bot.config import PathConfig


class JsonFile:
    def __init__(self, file_name: str):
        self.file_name = file_name

    def read(self) -> JSON_DATA:
        with open(self.file_name, encoding="utf-8") as file:
            return json.loads(file.read())

    def write(self, data: JSON_DATA) -> None:
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=False, indent=2))


def update_json(file: JsonFile):
    def decorator(function):
        def wrapper(*args, **kwargs):
            data = file.read()
            result = function(*args, **kwargs, json_data=data)

            file.write(data)
            return result

        return wrapper

    return decorator


PlayListsFile = JsonFile(PathConfig.PLAYLISTS)
ConfigFile = JsonFile(PathConfig.CONFIG)
