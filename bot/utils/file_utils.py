import json

from bot._types import JSON_DATA
from bot.config import PathConfig


class JsonFile:
    def __init__(self, file_name: str):
        self.file_name = file_name

    def get(self) -> JSON_DATA:
        with open(self.file_name, encoding="utf-8") as file:
            return json.loads(file.read())

    def write(self, data: JSON_DATA) -> None:
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=False))


def update_json(file: JsonFile):
    def decorator(function):
        def wrapper(*args, **kwargs):
            data = file.get()
            result = function(*args, **kwargs, json_data=data)

            new_data = result
            if isinstance(result, tuple):
                new_data = result[0]
            if new_data is not None:
                file.write(new_data)
            return result

        return wrapper

    return decorator


PrefixesFile = JsonFile(PathConfig.PREFIXES)
PlayListsFile = JsonFile(PathConfig.PLAYLISTS)
ConfigFile = JsonFile(PathConfig.CONFIG)
