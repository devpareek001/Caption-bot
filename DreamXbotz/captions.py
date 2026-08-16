import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import FloodWait

from config import Settings

from .helpers.caption_tools import (
    media_file_name,
    parse_message_ref,
    render_template,
    validate_template,
)

from .helpers.keyboards import start_buttons
from .helpers.logging_setup import get_logger

from .storage import (
    add_audit_log,
    clear_recaption_progress,
    delete_channel_caption,
    get_channel_caption,
    get_channel_stats,
    get_recaption_progress,
    increment_channel_stat,
    save_channel_caption,
    save_recaption_progress,
    save_user,
)

from .helpers.telegram import flood_wait_seconds


LOGGER = get_logger("Dreamxbotz.captions")

SAMPLE_FILE_NAME = "Dreamxbotz Movie 2026 Hindi 1080p"
SAMPLE_CAPTION = "Original upload caption"


# =========================================================
# PM-BASED CHANNEL CONNECTION
#
# All admin/management commands are now sent to the bot in
# PRIVATE chat, not posted in the channel itself. Each user
# first links a channel with /connect, then every command
# they send in PM targets that connected channel.
#
# In-memory only (per-process) — resets on restart, same as
# the other in-memory state below. Users just run /connect
# again if that happens.
# =========================================================

user_active_channel = {}   # user_id -> channel_id


async def get_active_channel(message):
    """Returns the channel_id the user has connected via
    /connect, or replies with an error and returns None."""

    channel_id = user_active_channel.get(
        message.from_user.id
    )

    if not channel_id:

        await message.reply(
            "❌ <b>No channel connected.</b>\n\n"
            "Use <code>/connect @yourchannel</code> "
            "(or <code>/connect -100xxxxxxxxxx</code>) first.\n\n"
            "Make sure I'm an admin in that channel and "
            "that you're an admin there too."
        )
        return None

    return channel_id


@Client.on_message(
    filters.command("connect") & filters.private
)
async def connect_channel(bot, message):

    if len(message.command) < 2:

        await message.reply(
            "<b>Connect a channel</b>\n\n"
            "Usage:\n"
            "<code>/connect @yourchannel</code>\n"
            "or\n"
            "<code>/connect -100xxxxxxxxxx</code>\n\n"
            "I must already be an admin in that channel, "
            "and you must be an admin there too.\n\n"
            "Once connected, all caption commands sent to "
            "me here in PM will target that channel."
        )
        return

    target = message.command[1]

    ADMIN_STATUSES = (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    )

    try:
        chat = await bot.get_chat(target)
    except Exception as exc:
        await message.reply(
            f"❌ Could not find that channel: <code>{exc}</code>"
        )
        return

    if chat.type != ChatType.CHANNEL:

        await message.reply("❌ That's not a channel.")
        return

    try:
        member = await bot.get_chat_member(
            chat.id, message.from_user.id
        )
    except Exception:
        await message.reply(
            "❌ You must be an admin of that channel."
        )
        return

    if member.status not in ADMIN_STATUSES:

        await message.reply(
            "❌ You must be an admin of that channel."
        )
        return

    try:
        bot_member = await bot.get_chat_member(chat.id, "me")
        bot_is_admin = bot_member.status in ADMIN_STATUSES
    except Exception:
        bot_is_admin = False

    if not bot_is_admin:

        await message.reply(
            "❌ I need to be an admin in that channel too — "
            "add me as admin there first."
        )
        return

    user_active_channel[message.from_user.id] = chat.id

    await message.reply(
        f"✅ Connected to <b>{chat.title}</b>.\n\n"
        "All caption commands sent to me here in PM will "
        "now target this channel. Run <code>/connect</code> "
        "again anytime to switch channels."
    )


# =========================================================
# DELETE COMMAND MESSAGES
# =========================================================

async def delete_messages(m1, m2):
    await asyncio.sleep(5)

    for m in (m1, m2):
        try:
            if m:
                await m.delete()
        except Exception:
            pass


# =========================================================
# START
# =========================================================

@Client.on_message(
    filters.command("start") & filters.private
)
async def start_cmd(bot, message):

    await save_user(
        int(message.from_user.id)
    )

    await message.reply_photo(
        photo=Settings.BOT_PIC,
        caption=(
            f"<b>Hey, {message.from_user.mention}</b>\n\n"
            "I automatically edit captions for videos, "
            "audio files, and documents posted in channels.\n\n"
            "<b>Setup:</b>\n"
            "1️⃣ Add me as admin in your channel.\n"
            "2️⃣ Here in PM, run "
            "<code>/connect @yourchannel</code>.\n\n"
            "After that, all commands are sent to me here "
            "in PM (not in the channel):\n"
            "<code>/set_caption</code> — set a custom caption\n"
            "<code>/del_caption</code> — restore the default\n"
            "<code>/recaption_all</code> — update captions on "
            "previously posted files too (admin only)\n"
            "<code>/recaption_range</code> — recaption a "
            "custom message range\n"
            "<code>/stop_recaption</code> — stop a running job"
        ),
        reply_markup=start_buttons(),
    )


# =========================================================
# SET CAPTION
# =========================================================

@Client.on_message(
    filters.command("set_caption") & filters.private
)
async def set_caption(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    if len(message.command) < 2:

        await message.reply(
            "Usage:\n"
            "<code>/set_caption {file_name}</code>\n\n"
            "Available placeholders:\n"
            "<code>{file_name}</code>\n"
            "<code>{caption}</code>\n"
            "<code>{language}</code>\n"
            "<code>{year}</code>\n"
            "<code>{quality}</code>\n"
            "<code>{file_size}</code>\n"
            "<code>{duration}</code>\n"
            "<code>{season}</code>\n"
            "<code>{episode}</code>"
        )
        return

    caption = message.text.split(
        " ",
        1
    )[1].strip()

    is_valid, invalid_fields = validate_template(
        caption
    )

    if not is_valid:

        await message.reply(
            f"Unknown placeholder(s): "
            f"<code>{invalid_fields}</code>\n\n"
            "Use only allowed placeholders."
        )
        return

    await save_channel_caption(
        channel_id,
        caption
    )

    await add_audit_log(
        "caption_saved",
        channel_id,
        actor_id=getattr(
            message.from_user,
            "id",
            None
        ),
        detail={
            "caption": caption
        },
    )

    await message.reply(
        "Caption saved successfully.\n\n"
        f"New caption:\n<code>{caption}</code>"
    )


# =========================================================
# CAPTION PREVIEW
# =========================================================

@Client.on_message(
    filters.command("caption_preview") & filters.private
)
async def caption_preview(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    template = (
        message.text.split(" ", 1)[1].strip()
        if len(message.command) > 1
        else None
    )

    if not template:

        caption_doc = await get_channel_caption(
            channel_id
        )

        template = (
            caption_doc["caption"]
            if caption_doc
            else Settings.DEF_CAP
        )

    is_valid, invalid_fields = validate_template(
        template
    )

    if not is_valid:

        await message.reply(
            f"Template error: "
            f"<code>{invalid_fields}</code>"
        )
        return

    preview = render_template(
        template,
        None,
        SAMPLE_FILE_NAME,
        SAMPLE_CAPTION
    )

    await message.reply(
        f"<b>Caption preview</b>\n\n{preview}"
    )


# =========================================================
# CAPTION VARIABLES
# =========================================================

@Client.on_message(
    filters.command("caption_vars") & filters.private
)
async def caption_vars(bot, message):

    await message.reply(
        "<b>Available caption placeholders</b>\n\n"
        "<code>{file_name}</code> - cleaned file name\n"
        "<code>{caption}</code> - original caption or file name\n"
        "<code>{language}</code> - detected language\n"
        "<code>{year}</code> - detected release year\n"
        "<code>{quality}</code> - video quality\n"
        "<code>{file_size}</code> - media file size\n"
        "<code>{duration}</code> - media duration\n"
        "<code>{season}</code> - season number\n"
        "<code>{episode}</code> - episode number"
    )


# =========================================================
# CHANNEL SETTINGS
# =========================================================

@Client.on_message(
    filters.command("settings") & filters.private
)
async def channel_settings(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    caption_doc = await get_channel_caption(
        channel_id
    )

    template = (
        caption_doc["caption"]
        if caption_doc
        else Settings.DEF_CAP
    )

    mode = (
        "custom"
        if caption_doc
        else "default"
    )

    await message.reply(
        "<b>Channel settings</b>\n\n"
        f"<b>Caption mode:</b> <code>{mode}</code>\n"
        f"<b>Template:</b>\n<code>{template}</code>"
    )


# =========================================================
# CHANNEL STATS
# =========================================================

@Client.on_message(
    filters.command("channel_stats") & filters.private
)
async def channel_stats(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    stats = await get_channel_stats(
        channel_id
    )

    await message.reply(
        "<b>Channel stats</b>\n\n"
        f"<b>Caption edits:</b> "
        f"<code>{stats.get('caption_edits', 0)}</code>"
    )


# =========================================================
# DELETE CAPTION
# =========================================================

@Client.on_message(
    filters.command(
        [
            "delcaption",
            "del_caption",
            "delete_caption"
        ]
    )
    & filters.private
)
async def del_caption(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    result = await delete_channel_caption(
        channel_id
    )

    if result.deleted_count:

        await add_audit_log(
            "caption_deleted",
            channel_id,
            actor_id=getattr(
                message.from_user,
                "id",
                None
            ),
        )

        rep = await message.reply(
            "Custom caption deleted. "
            "I will use the default caption from now on."
        )

    else:

        rep = await message.reply(
            "No custom caption was set for this channel."
        )

    asyncio.create_task(
        delete_messages(message, rep)
    )


# =========================================================
# RECAPTION ENGINE (shared by /recaption_all and
# /recaption_range)
#
# HOW THIS WORKS (bot-token friendly):
# Telegram blocks bots from using get_chat_history
# (BOT_METHOD_INVALID). But bots CAN fetch specific
# known message IDs using get_messages(channel_id, [ids]).
#
# Channel message IDs are just sequential numbers, so we
# scan backwards from a TOP id down to a FLOOR id in
# chunks, fetching each chunk with get_messages and
# editing any file captions we find. No userbot needed.
#
# - No cap: scans the whole range in one run
# - Saves checkpoint in MongoDB after every chunk (crash safety)
# - /stop_recaption cancels a running job (resumable)
# - /recaption_range lets you pick a custom top/bottom ID
# =========================================================

GET_MESSAGES_CHUNK = 200        # IDs fetched per get_messages call
PROGRESS_UPDATE_EVERY = 1       # update progress message every N chunks (live)

# In-memory (per-process) state.
# Stop flags and the range-flow Q&A are per-channel and
# reset if the bot restarts — but the MongoDB checkpoint
# still lets /recaption_all resume a stopped/interrupted job.

recaption_stop_flags = {}     # channel_id -> True (stop requested)
recaption_range_state = {}    # user_id -> {"stage": ..., "channel_id": ..., "top_id": ...}
async def execute_recaption_job(
    bot,
    channel_id,
    progress_msg,
    target_caption,
    start_id,
    floor_id,
    processed,
    updated,
    skipped,
    failed,
    actor_id=None,
):

    current_id = start_id
    chunk_count = 0
    stopped_by_user = False

    while current_id >= floor_id:

        if recaption_stop_flags.get(channel_id):

            recaption_stop_flags.pop(channel_id, None)
            stopped_by_user = True
            break

        take = min(
            GET_MESSAGES_CHUNK,
            current_id - floor_id + 1
        )

        chunk_ids = list(
            range(
                current_id - take + 1,
                current_id + 1
            )
        )

        try:

            messages = await bot.get_messages(
                channel_id,
                chunk_ids
            )

        except FloodWait as e:

            wait_time = flood_wait_seconds(e)

            LOGGER.warning(
                "FloodWait fetching chunk ending at %s. "
                "Sleeping %s seconds.",
                current_id,
                wait_time,
            )

            await asyncio.sleep(wait_time)

            try:
                messages = await bot.get_messages(
                    channel_id,
                    chunk_ids
                )
            except Exception as exc:
                LOGGER.warning(
                    "Chunk fetch retry failed at %s: %s",
                    current_id,
                    exc
                )
                messages = []

        except Exception as exc:

            LOGGER.warning(
                "Chunk fetch failed at %s: %s",
                current_id,
                exc
            )
            messages = []

        for msg in messages:

            if not msg or getattr(msg, "empty", False):
                continue

            if getattr(msg, "service", False):
                continue

            processed += 1

            try:

                file_name = media_file_name(msg)

            except Exception as exc:

                LOGGER.warning(
                    "Could not detect media for %s: %s",
                    msg.id,
                    exc
                )
                file_name = None

            try:

                if not file_name:

                    skipped += 1

                else:

                    rendered_caption = render_template(
                        target_caption,
                        msg,
                        file_name,
                        msg.caption
                    )

                    if msg.caption == rendered_caption:

                        skipped += 1

                    else:

                        await msg.edit_caption(
                            rendered_caption
                        )

                        updated += 1

                    try:
                        await increment_channel_stat(
                            channel_id,
                            "caption_edits"
                        )
                    except Exception:
                        pass

                    await asyncio.sleep(0.35)

            except FloodWait as e:

                wait_time = flood_wait_seconds(e)

                LOGGER.warning(
                    "FloodWait editing message %s. "
                    "Sleeping %s seconds.",
                    msg.id,
                    wait_time,
                )

                await asyncio.sleep(wait_time)

                try:

                    retry_caption = (
                        render_template(
                            target_caption,
                            msg,
                            file_name,
                            msg.caption
                        )
                        if file_name
                        else None
                    )

                    if file_name and msg.caption != retry_caption:

                        await msg.edit_caption(
                            retry_caption
                        )
                        updated += 1

                        try:
                            await increment_channel_stat(
                                channel_id,
                                "caption_edits"
                            )
                        except Exception:
                            pass

                    else:
                        skipped += 1

                except Exception as retry_exc:

                    failed += 1

                    LOGGER.warning(
                        "Retry failed for %s: %s",
                        msg.id,
                        retry_exc
                    )

            except Exception as exc:

                failed += 1

                LOGGER.warning(
                    "Recaption failed for %s/%s: %s",
                    channel_id,
                    msg.id,
                    exc,
                )

        current_id -= take
        chunk_count += 1

        try:

            await save_recaption_progress(
                channel_id=channel_id,
                next_id=current_id,
                caption=target_caption,
                processed=processed,
                updated=updated,
                skipped=skipped,
                failed=failed,
                floor_id=floor_id,
            )

        except Exception as checkpoint_exc:

            LOGGER.warning(
                "Could not save checkpoint at %s: %s",
                current_id,
                checkpoint_exc,
            )

        if chunk_count % PROGRESS_UPDATE_EVERY == 0:

            try:

                await progress_msg.edit(
                    "⏳ <b>Recaption in progress...</b>\n\n"
                    f"Processed: <code>{processed}</code>\n"
                    f"Updated: <code>{updated}</code>\n"
                    f"Skipped: <code>{skipped}</code>\n"
                    f"Failed: <code>{failed}</code>\n\n"
                    f"Currently at message ID: <code>{current_id}</code>"
                )

            except Exception:
                pass

    # -----------------------------------------------------
    # Finished — stopped by user, or reached the floor
    # -----------------------------------------------------

    if stopped_by_user:

        try:

            await progress_msg.edit(
                "🛑 <b>Recaption stopped.</b>\n\n"
                f"📨 Messages scanned: <code>{processed}</code>\n"
                f"✏️ Captions updated: <code>{updated}</code>\n"
                f"⏭ Skipped: <code>{skipped}</code>\n"
                f"❌ Failed: <code>{failed}</code>\n\n"
                f"Next message ID to scan: <code>{current_id}</code>\n\n"
                "♻️ Progress is saved.\n"
                "Run <code>/recaption_all</code> to resume."
            )

        except Exception:
            pass

        return

    await add_audit_log(
        "recaption_completed",
        channel_id,
        actor_id=actor_id,
        detail={
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "caption": target_caption,
        },
    )

    await clear_recaption_progress(
        channel_id
    )

    try:

        await progress_msg.edit(
            "✅ <b>Recaption completed!</b>\n\n"
            f"📨 Messages scanned: <code>{processed}</code>\n"
            f"✏️ Captions updated: <code>{updated}</code>\n"
            f"⏭ Skipped: <code>{skipped}</code>\n"
            f"❌ Failed: <code>{failed}</code>\n\n"
            "🎉 All files in range have been processed.\n\n"
            "♻️ Checkpoint removed from MongoDB."
        )

    except Exception:
        pass


# =========================================================
# STOP RECAPTION
# =========================================================

@Client.on_message(
    filters.command("stop_recaption") & filters.private
)
async def stop_recaption(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    recaption_stop_flags[channel_id] = True

    await message.reply(
        "🛑 <b>Stop requested.</b>\n\n"
        "The running recaption job will stop after "
        "finishing its current batch.\n\n"
        "Progress is saved — run <code>/recaption_all</code> "
        "anytime to resume from where it stopped."
    )


# =========================================================
# CANCEL (used to cancel the /recaption_range Q&A flow)
# =========================================================

@Client.on_message(
    filters.command("cancel") & filters.private
)
async def cancel_range_flow(bot, message):

    user_id = message.from_user.id

    if user_id in recaption_range_state:

        recaption_range_state.pop(user_id, None)

        await message.reply("❌ Cancelled.")


# =========================================================
# RECAPTION RANGE
#
# /recaption_range
#
# Interactive flow — bot asks for the TOP message ID,
# then the BOTTOM message ID, then the new caption,
# and scans only that range.
#
# Sent in PM. State is keyed by the requesting user's ID
# and carries the connected channel_id along with it.
# =========================================================

@Client.on_message(
    filters.command("recaption_range") & filters.private
)
async def recaption_range_start(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    user_id = message.from_user.id

    recaption_range_state[user_id] = {
        "stage": "top",
        "channel_id": channel_id,
        "requested_by": user_id,
    }

    await message.reply(
        "<b>Custom range recaption</b>\n\n"
        "Send the <b>TOP</b> message — either its numeric ID "
        "or its Telegram message link "
        "(e.g. <code>https://t.me/c/12345/678</code>) — "
        "the newer / higher one, to start from.\n\n"
        "Send <code>/cancel</code> anytime to cancel."
    )


@Client.on_message(
    filters.private
    & filters.text
    & filters.create(
        lambda _, __, m: (
            m.from_user
            and m.from_user.id in recaption_range_state
        )
    )
)
async def recaption_range_collect(bot, message):

    user_id = message.from_user.id
    state = recaption_range_state.get(user_id)

    if not state:
        return

    channel_id = state["channel_id"]

    text = (message.text or "").strip()

    # -----------------------------------------------------
    # Stage 1: TOP id
    # -----------------------------------------------------

    if state["stage"] == "top":

        top_id = parse_message_ref(text)

        if top_id is None:
            await message.reply(
                "❌ Please send a valid message ID or "
                "Telegram message link."
            )
            return

        state["top_id"] = top_id
        state["stage"] = "bottom"

        await message.reply(
            "Got it. Now send the <b>BOTTOM</b> message — "
            "ID or link — (the older / lower one) to stop at."
        )
        return

    # -----------------------------------------------------
    # Stage 2: BOTTOM id
    # -----------------------------------------------------

    if state["stage"] == "bottom":

        bottom_id = parse_message_ref(text)

        if bottom_id is None:
            await message.reply(
                "❌ Please send a valid message ID or "
                "Telegram message link."
            )
            return

        top_id = state["top_id"]

        if bottom_id > top_id:
            top_id, bottom_id = bottom_id, top_id

        state["bottom_id"] = bottom_id
        state["top_id"] = top_id
        state["stage"] = "caption"

        await message.reply(
            f"Range set: <code>{bottom_id}</code> to "
            f"<code>{top_id}</code>.\n\n"
            "Now send the <b>new caption</b> to apply "
            "to every file in this range."
        )
        return

    # -----------------------------------------------------
    # Stage 3: caption — then start the job
    # -----------------------------------------------------

    if state["stage"] == "caption":

        caption = text

        if not caption:
            await message.reply("❌ Caption cannot be empty.")
            return

        if len(caption) > 1024:
            await message.reply(
                "❌ Caption is too long "
                "(max 1024 characters)."
            )
            return

        is_valid, invalid_fields = validate_template(
            caption
        )

        if not is_valid:
            await message.reply(
                f"❌ Unknown placeholder(s): "
                f"<code>{invalid_fields}</code>\n\n"
                "Use only allowed placeholders."
            )
            return

        top_id = state["top_id"]
        bottom_id = state["bottom_id"]

        recaption_range_state.pop(user_id, None)

        await add_audit_log(
            "recaption_range_started",
            channel_id,
            actor_id=getattr(message.from_user, "id", None),
            detail={
                "caption": caption,
                "top_id": top_id,
                "bottom_id": bottom_id,
            },
        )

        resume_text = (
            "🚀 <b>Starting custom range recaption...</b>\n\n"
            f"Range: <code>{bottom_id}</code> to "
            f"<code>{top_id}</code>"
        )

        progress_msg = await message.reply(
            f"{resume_text}\n\n"
            f"<b>Target caption:</b>\n<code>{caption}</code>\n\n"
            "Processed so far: <code>0</code>\n"
            "Updated: <code>0</code>\n"
            "Skipped: <code>0</code>\n"
            "Failed: <code>0</code>"
        )

        await execute_recaption_job(
            bot=bot,
            channel_id=channel_id,
            progress_msg=progress_msg,
            target_caption=caption,
            start_id=top_id,
            floor_id=bottom_id,
            processed=0,
            updated=0,
            skipped=0,
            failed=0,
            actor_id=getattr(message.from_user, "id", None),
        )

        return


# =========================================================
# RECAPTION ALL
#
# /recaption_all NEW CAPTION
#
# Scans everything from the latest message down to ID 1.
# Use /recaption_range instead if you only want a
# specific range. Use /stop_recaption to cancel either.
# =========================================================

@Client.on_message(
    filters.command(
        [
            "recaption_all",
            "update_old_captions"
        ]
    )
    & filters.private
)
async def recaption_all(bot, message):

    channel_id = await get_active_channel(message)
    if channel_id is None:
        return

    old_job = await get_recaption_progress(
        channel_id
    )

    if len(message.command) < 2 and not old_job:

        await message.reply(
            "<b>Usage:</b>\n\n"
            "<code>/recaption_all YOUR NEW CAPTION</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/recaption_all "
            "🔥 Dreamxbotz Movies 🔥</code>\n\n"
            "Scans every old file all the way down to "
            "message ID 1.\n\n"
            "Want a specific range instead? Use "
            "<code>/recaption_range</code>.\n"
            "To stop a running job, use "
            "<code>/stop_recaption</code>."
        )
        return

    if len(message.command) >= 2:

        command_caption = message.text.split(
            " ",
            1
        )[1].strip()

    else:
        command_caption = None

    if command_caption is not None and not command_caption:

        rep = await message.reply(
            "❌ New caption cannot be empty."
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    if command_caption and len(command_caption) > 1024:

        rep = await message.reply(
            "❌ Caption is too long.\n\n"
            "Telegram captions cannot be longer than "
            "<code>1024</code> characters."
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    if command_caption:

        is_valid, invalid_fields = validate_template(
            command_caption
        )

        if not is_valid:

            rep = await message.reply(
                f"❌ Unknown placeholder(s): "
                f"<code>{invalid_fields}</code>\n\n"
                "Use only allowed placeholders."
            )

            asyncio.create_task(
                delete_messages(message, rep)
            )
            return

    if old_job:

        target_caption = old_job.get(
            "caption",
            command_caption
        )

        start_id = old_job.get(
            "next_id"
        )

        floor_id = old_job.get(
            "floor_id",
            1
        )

        processed = old_job.get("processed", 0)
        updated = old_job.get("updated", 0)
        skipped = old_job.get("skipped", 0)
        failed = old_job.get("failed", 0)

        resume_text = (
            "♻️ <b>Resuming previous job...</b>\n\n"
            f"Continuing down from message ID: "
            f"<code>{start_id}</code>"
        )

    else:

        target_caption = command_caption

        # We're in PM now, so message.id belongs to this PM
        # chat, not the channel. Ping the channel with a
        # throwaway message to learn its current latest
        # message ID, then delete the ping.
        try:
            probe = await bot.send_message(channel_id, "🔄")
            start_id = probe.id - 1
            await probe.delete()
        except Exception as exc:
            await message.reply(
                "❌ Could not access the connected channel "
                f"to find its latest message: <code>{exc}</code>\n\n"
                "Make sure I'm still an admin there with "
                "permission to post and delete messages."
            )
            return

        floor_id = 1

        processed = 0
        updated = 0
        skipped = 0
        failed = 0

        resume_text = (
            "🚀 <b>Starting new recaption job...</b>\n\n"
            f"Scanning downward from message ID: "
            f"<code>{start_id}</code>"
        )

        await add_audit_log(
            "recaption_all_started",
            channel_id,
            actor_id=getattr(
                message.from_user,
                "id",
                None
            ),
            detail={
                "caption": target_caption,
                "start_id": start_id,
                "mode": "id_range_scan",
            },
        )

    if not start_id or start_id < floor_id:

        await clear_recaption_progress(channel_id)

        rep = await message.reply(
            "✅ Nothing left to scan."
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    progress_msg = await message.reply(
        f"{resume_text}\n\n"
        f"<b>Target caption:</b>\n"
        f"<code>{target_caption}</code>\n\n"
        f"Processed so far: <code>{processed}</code>\n"
        f"Updated: <code>{updated}</code>\n"
        f"Skipped: <code>{skipped}</code>\n"
        f"Failed: <code>{failed}</code>"
    )

    await execute_recaption_job(
        bot=bot,
        channel_id=channel_id,
        progress_msg=progress_msg,
        target_caption=target_caption,
        start_id=start_id,
        floor_id=floor_id,
        processed=processed,
        updated=updated,
        skipped=skipped,
        failed=failed,
        actor_id=getattr(message.from_user, "id", None),
    )


# =========================================================
# AUTO CAPTION FOR NEW FILES
# =========================================================

@Client.on_message(
    filters.channel
)
async def auto_edit_caption(bot, message):

    file_name = media_file_name(
        message
    )

    if not file_name:
        return

    caption_doc = await get_channel_caption(
        message.chat.id
    )

    template = (
        caption_doc["caption"]
        if caption_doc
        else Settings.DEF_CAP
    )

    try:

        new_caption = render_template(
            template,
            message,
            file_name,
            message.caption
        )

        if message.caption != new_caption:

            await message.edit_caption(
                new_caption
            )

            await increment_channel_stat(
                message.chat.id,
                "caption_edits"
            )

    except FloodWait as e:

        await asyncio.sleep(
            flood_wait_seconds(e)
        )

        try:

            await message.edit_caption(
                render_template(
                    template,
                    message,
                    file_name,
                    message.caption
                )
            )

        except Exception as exc:

            LOGGER.warning(
                "Caption retry failed in channel %s: %s",
                message.chat.id,
                exc
            )

    except KeyError as exc:

        LOGGER.warning(
            "Caption template fallback for channel %s: %s",
            message.chat.id,
            exc
        )

        try:

            await message.edit_caption(
                render_template(
                    Settings.DEF_CAP,
                    message,
                    file_name,
                    message.caption
                )
            )

        except Exception as inner_exc:

            LOGGER.warning(
                "Default caption failed in channel %s: %s",
                message.chat.id,
                inner_exc
            )

    except Exception as exc:

        LOGGER.warning(
            "Could not edit caption in channel %s: %s",
            message.chat.id,
            exc
    )
