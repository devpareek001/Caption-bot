from datetime import datetime

import motor.motor_asyncio
from pymongo import DESCENDING

from config import Settings
from .helpers.logging_setup import get_logger


LOGGER = get_logger("Dreamxbotz.storage")


client = motor.motor_asyncio.AsyncIOMotorClient(
    Settings.DB_URL
)

db = client[Settings.DB_NAME]


# =========================================================
# COLLECTIONS
# =========================================================

channel_captions = db.channel_captions
legacy_channel_captions = db.chnl_ids
channel_stats = db.channel_stats
audit_logs = db.audit_logs
users = db.users


# =========================================================
# PREPARE STORAGE
# =========================================================

async def prepare_storage():

    await channel_captions.create_index(
        "channel_id",
        unique=True
    )

    await channel_stats.create_index(
        "channel_id",
        unique=True
    )

    await audit_logs.create_index(
        [
            ("created_at", DESCENDING)
        ]
    )

    await audit_logs.create_index(
        [
            ("scope_id", 1),
            ("created_at", DESCENDING)
        ]
    )

    LOGGER.info(
        "MongoDB storage ready: %s",
        Settings.DB_NAME
    )


# =========================================================
# CLOSE STORAGE
# =========================================================

def close_storage():
    client.close()


# =========================================================
# USERS
# =========================================================

async def save_user(user_id):

    await users.update_one(
        {
            "_id": user_id
        },
        {
            "$setOnInsert": {
                "_id": user_id
            }
        },
        upsert=True,
    )


async def count_users():

    return await users.count_documents({})


def iter_users():

    return users.find(
        {},
        {
            "_id": 1
        }
    )


async def delete_user(user_id):

    await users.delete_one(
        {
            "_id": user_id
        }
    )


# =========================================================
# CHANNEL CAPTION
# =========================================================

async def save_channel_caption(
    channel_id,
    caption
):

    await channel_captions.update_one(
        {
            "channel_id": channel_id
        },
        {
            "$set": {
                "channel_id": channel_id,
                "caption": caption,
            }
        },
        upsert=True,
    )


async def get_channel_caption(channel_id):

    caption = await channel_captions.find_one(
        {
            "channel_id": channel_id
        }
    )

    if caption:
        return caption

    legacy_caption = await legacy_channel_captions.find_one(
        {
            "chnl_id": channel_id
        }
    )

    if legacy_caption:

        await save_channel_caption(
            channel_id,
            legacy_caption["caption"]
        )

        LOGGER.info(
            "Migrated legacy caption for channel %s",
            channel_id
        )

        return {
            "channel_id": channel_id,
            "caption": legacy_caption["caption"],
        }

    return None


async def delete_channel_caption(
    channel_id
):

    result = await channel_captions.delete_one(
        {
            "channel_id": channel_id
        }
    )

    legacy_result = await legacy_channel_captions.delete_one(
        {
            "chnl_id": channel_id
        }
    )

    if result.deleted_count:
        return result

    return legacy_result


# =========================================================
# CHANNEL STATS
# =========================================================

async def increment_channel_stat(
    channel_id,
    field,
    amount=1
):

    await channel_stats.update_one(
        {
            "channel_id": channel_id
        },
        {
            "$inc": {
                field: amount
            },
            "$setOnInsert": {
                "channel_id": channel_id
            },
        },
        upsert=True,
    )


async def get_channel_stats(
    channel_id
):

    stats = await channel_stats.find_one(
        {
            "channel_id": channel_id
        }
    )

    return (
        stats
        or {
            "channel_id": channel_id,
            "caption_edits": 0,
        }
    )


# =========================================================
# AUDIT LOG
# =========================================================

async def add_audit_log(
    action,
    scope_id,
    actor_id=None,
    detail=None
):

    await audit_logs.insert_one(
        {
            "action": action,
            "scope_id": scope_id,
            "actor_id": actor_id,
            "detail": detail or {},
            "created_at": datetime.utcnow(),
        }
    )


# =========================================================
# RECAPTION CHECKPOINT
#
# Uses ID-range scanning (bot.get_messages with known IDs)
# instead of get_chat_history, because Telegram blocks
# get_chat_history for bot accounts (BOT_METHOD_INVALID).
# =========================================================

async def save_recaption_progress(
    channel_id,
    next_id,
    caption,
    processed=0,
    updated=0,
    skipped=0,
    failed=0,
):

    await audit_logs.update_one(
        {
            "action": "recaption_checkpoint",
            "scope_id": channel_id,
        },
        {
            "$set": {
                "action": "recaption_checkpoint",
                "scope_id": channel_id,
                "detail": {
                    "next_id": next_id,
                    "caption": caption,
                    "processed": processed,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                },
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


async def get_recaption_progress(
    channel_id
):

    doc = await audit_logs.find_one(
        {
            "action": "recaption_checkpoint",
            "scope_id": channel_id,
        }
    )

    if not doc:
        return None

    detail = doc.get("detail", {})
    detail["channel_id"] = channel_id
    return detail


async def clear_recaption_progress(
    channel_id
):

    await audit_logs.delete_one(
        {
            "action": "recaption_checkpoint",
            "scope_id": channel_id,
        }
    )
