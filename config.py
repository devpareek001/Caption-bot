import os
import re
import time


ID_PATTERN = re.compile(r"^-?\d+$")


def env(name, default=""):
    return os.environ.get(name, default).strip()


def env_int(name, default):
    value = env(name, str(default))
    return int(value) if value else default


def clean_channel(value):
    return value.strip().lstrip("@") if value else ""


def parse_admins(value):
    return [
        int(admin) if ID_PATTERN.fullmatch(admin) else admin
        for admin in value.split()
    ]


class Settings:
    # Direct values in repo
    API_ID = 24942826
    API_HASH = "e3e2f3b65ef58634139ccd27d6b7d8cb"

    # Environment variables
    BOT_TOKEN = env("BOT_TOKEN")

    BOT_PIC = env("BOT_PIC") or env(
        "START_PIC",
        "https://telegra.ph/file/21a8e96b45cd6ac4d3da6.jpg"
    )

    BOT_UPTIME = time.time()

    PORT = env_int("PORT", 8080)
    WORKERS = env_int("WORKERS", 200)

    FORCE_SUB = clean_channel(env("FORCE_SUB"))

    DB_NAME = env("DB_NAME", "dev_caption")

    BOT_USERNAME = env(
        "BOT_USERNAME",
        "@Advance_caption_pro_bot"
    )

    CHANNEL_URL = env(
        "CHANNEL_URL",
        "https://t.me/DMovies_Empire_backup"
    )

    SUPPORT_URL = env("SUPPORT_URL")
    SOURCE_URL = env("SOURCE_URL")

    # MongoDB URL directly in repo
    DB_URL = "mongodb+srv://opkatil1_db_user:caption@cluster0.fows7bk.mongodb.net/?appName=Cluster0"

    LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()

    DEF_CAP = env(
        "DEF_CAP",
        "<b>{file_name}</b>\n\n"
        "<b>Main Telegram Channel:</b> @DMovies_Empire_backup",
    )

    STICKER_ID = env(
        "STICKER_ID",
        "CAACAgIAAxkBAAELFqBllhB70i13m-woXeIWDXU6BD2j7wAC9gcAAkb7rAR7xdjVOS5ziTQE",
    )

    ADMINS = parse_admins(env("ADMINS"))

    @classmethod
    def missing_required(cls):
        required = {
            "API_ID": cls.API_ID,
            "API_HASH": cls.API_HASH,
            "BOT_TOKEN": cls.BOT_TOKEN,
            "DB_URL": cls.DB_URL,
        }

        return [
            name
            for name, value in required.items()
            if not value
        ]

    @classmethod
    def summary(cls):
        return {
            "bot": cls.BOT_USERNAME,
            "database": cls.DB_NAME,
            "force_sub": bool(cls.FORCE_SUB),
            "admins": len(cls.ADMINS),
            "workers": cls.WORKERS,
            "port": cls.PORT,
        }


DreamXbotz = Settings
