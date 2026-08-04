import asyncio
import os
import sys
import time
from pyrogram import Client, errors, filters
from pyrogram.errors import FloodWait
from config import Settings
from .helpers.logging_setup import get_logger
from .storage import add_audit_log, count_users, delete_user, iter_users
from .helpers.telegram import flood_wait_seconds


LOGGER = get_logger("Dreamxbotz.admin")


@Client.on_message(filters.private & filters.user(Settings.ADMINS) & filters.command(["users", "status"]))
async def bot_status(client, message):
    start_t = time.time()
    status_msg = await message.reply_text("Processing...")
    uptime = time.strftime("%Hh %Mm %Ss", time.gmtime(time.time() - client.uptime))
    ping_ms = (time.time() - start_t) * 1000
    users_count = await count_users()
    await status_msg.edit(
        "**Bot status**\n\n"
        f"**Uptime:** `{uptime}`\n"
        f"**Ping:** `{ping_ms:.3f} ms`\n"
        f"**Users:** `{users_count}`"
    )


@Client.on_message(filters.private & filters.user(Settings.ADMINS) & filters.command("broadcast"))
async def broadcast(client, message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message with /broadcast to send it to all users.")

    progress_msg = await message.reply_text("Broadcast started...")
    await add_audit_log("broadcast_started", message.chat.id, actor_id=message.from_user.id)
    total = await count_users()
    success = failed = deactivated = blocked = 0

    async for user in iter_users():
        user_id = user["_id"]
        try:
            await message.reply_to_message.copy(user_id)
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(flood_wait_seconds(e))
            try:
                await message.reply_to_message.copy(user_id)
                success += 1
            except Exception as exc:
                LOGGER.warning("Broadcast retry failed for %s: %s", user_id, exc)
                failed += 1
        except errors.InputUserDeactivated:
            deactivated += 1
            await delete_user(user_id)
        except errors.UserIsBlocked:
            blocked += 1
            await delete_user(user_id)
        except Exception as exc:
            LOGGER.warning("Broadcast failed for %s: %s", user_id, exc)
            failed += 1

        processed = success + failed + deactivated + blocked
        if processed % 10 == 0 or processed == total:
            await progress_msg.edit(
                "<u>Broadcast progress</u>\n\n"
                f"Total users: {total}\n"
                f"Sent: {success}\n"
                f"Blocked: {blocked}\n"
                f"Deleted accounts: {deactivated}\n"
                f"Failed: {failed}"
            )

    await add_audit_log(
        "broadcast_completed",
        message.chat.id,
        actor_id=message.from_user.id,
        detail={
            "total": total,
            "sent": success,
            "blocked": blocked,
            "deactivated": deactivated,
            "failed": failed,
        },
    )
    return await progress_msg.edit(
        "<u>Broadcast completed</u>\n\n"
        f"Total users: {total}\n"
        f"Sent: {success}\n"
        f"Blocked: {blocked}\n"
        f"Deleted accounts: {deactivated}\n"
        f"Failed: {failed}"
    )


@Client.on_message(filters.private & filters.user(Settings.ADMINS) & filters.command("restart"))
async def restart_bot(client, message):
    restart_msg = await client.send_message(message.chat.id, "Restarting bot...")
    await asyncio.sleep(3)
    await restart_msg.edit("Bot restarted. Starting again now...")
    os.execl(sys.executable, sys.executable, *sys.argv)
