from datetime import datetime

import motor.motor_asyncio
from pymongo import DESCENDING

from config import Settings
from .helpers.logging_setup import get_logger

LOGGER = get_logger("Dreamxbotz.storage")

client = motor.motor_asyncio.AsyncIOMotorClient(Settings.DB_URL)
db = client[Settings.DB_NAME]
channel_captions = db.channel_captions
legacy_channel_captions = db.chnl_ids
channel_stats = db.channel_stats
audit_logs = db.audit_logs
users = db.users
posted_files = db.posted_files


async def prepare_storage():
    await users.create_index("_id", unique=True)
    await channel_captions.create_index("channel_id", unique=True)
    await channel_stats.create_index("channel_id", unique=True)
    await audit_logs.create_index([("created_at", DESCENDING)])
    await audit_logs.create_index([("scope_id", 1), ("created_at", DESCENDING)])
    await posted_files.create_index([("channel_id", 1), ("message_id", 1)], unique=True)
    LOGGER.info("MongoDB storage ready: %s", Settings.DB_NAME)


def close_storage():
    client.close()


async def save_user(user_id):
    await users.update_one({"_id": user_id}, {"$setOnInsert": {"_id": user_id}}, upsert=True)


async def count_users():
    return await users.count_documents({})


def iter_users():
    return users.find({}, {"_id": 1})


async def delete_user(user_id):
    await users.delete_one({"_id": user_id})


async def save_channel_caption(channel_id, caption):
    await channel_captions.update_one(
        {"channel_id": channel_id},
        {"$set": {"channel_id": channel_id, "caption": caption}},
        upsert=True,
    )


async def get_channel_caption(channel_id):
    caption = await channel_captions.find_one({"channel_id": channel_id})
    if caption:
        return caption

    legacy_caption = await legacy_channel_captions.find_one({"chnl_id": channel_id})
    if legacy_caption:
        await save_channel_caption(channel_id, legacy_caption["caption"])
        LOGGER.info("Migrated legacy caption for channel %s", channel_id)
        return {"channel_id": channel_id, "caption": legacy_caption["caption"]}
    return None


async def delete_channel_caption(channel_id):
    result = await channel_captions.delete_one({"channel_id": channel_id})
    legacy_result = await legacy_channel_captions.delete_one({"chnl_id": channel_id})
    return result if result.deleted_count else legacy_result


async def increment_channel_stat(channel_id, field, amount=1):
    await channel_stats.update_one(
        {"channel_id": channel_id},
        {"$inc": {field: amount}, "$setOnInsert": {"channel_id": channel_id}},
        upsert=True,
    )


async def get_channel_stats(channel_id):
    stats = await channel_stats.find_one({"channel_id": channel_id})
    return stats or {"channel_id": channel_id, "caption_edits": 0}


async def save_posted_file(channel_id, message_id):
    await posted_files.update_one(
        {"channel_id": channel_id, "message_id": message_id},
        {"$set": {"channel_id": channel_id, "message_id": message_id, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


def iter_posted_files(channel_id):
    return posted_files.find({"channel_id": channel_id}).sort("message_id", DESCENDING)


async def count_posted_files(channel_id):
    return await posted_files.count_documents({"channel_id": channel_id})


async def delete_posted_file(channel_id, message_id):
    await posted_files.delete_one({"channel_id": channel_id, "message_id": message_id})


async def add_audit_log(action, scope_id, actor_id=None, detail=None):
    await audit_logs.insert_one(
        {
            "action": action,
            "scope_id": scope_id,
            "actor_id": actor_id,
            "detail": detail or {},
            "created_at": datetime.utcnow(),
        }
    )
