from enum import Enum

from tortoise.models import Model
from tortoise import fields


class Guild(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    discord_id = fields.IntField(unique=True)
    create_date = fields.DatetimeField(auto_now_add=True)


class LoopOption(str, Enum):
    none = "none"
    single = "single"
    all = "all"


class Settings(Model):
    id = fields.IntField(pk=True)
    guild = fields.ForeignKeyField(model_name="guild", unique=True)
    loop_option = fields.CharEnumField(enum_type=LoopOption, default=LoopOption.none)
    volume_option = fields.IntField(default=50)
