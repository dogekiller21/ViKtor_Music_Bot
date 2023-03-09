from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guild" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "discord_id" BIGINT NOT NULL UNIQUE,
    "create_date" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "settings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "loop_option" VARCHAR(6) NOT NULL  DEFAULT 'none',
    "volume_option" INT NOT NULL  DEFAULT 50,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "settings"."loop_option" IS 'none: none\nsingle: single\nall: all';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
