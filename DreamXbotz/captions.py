import asyncio

from pyrogram import Client, filters
from pyrogram.errors import FloodWait

from config import Settings

from .helpers.caption_tools import (
    media_file_name,
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
            "Use <code>/set_caption</code> in a channel "
            "to set a custom caption.\n"
            "Use <code>/del_caption</code> in a channel "
            "to restore the default caption.\n"
            "Use <code>/recaption_all</code> in a channel "
            "(admin only) to update captions on "
            "previously posted files too."
        ),
        reply_markup=start_buttons(),
    )


# =========================================================
# SET CAPTION
# =========================================================

@Client.on_message(
    filters.command("set_caption") & filters.channel
)
async def set_caption(bot, message):

    if len(message.command) < 2:

        rep = await message.reply(
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

        asyncio.create_task(
            delete_messages(message, rep)
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

        rep = await message.reply(
            f"Unknown placeholder(s): "
            f"<code>{invalid_fields}</code>\n\n"
            "Use only allowed placeholders."
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    await save_channel_caption(
        message.chat.id,
        caption
    )

    await add_audit_log(
        "caption_saved",
        message.chat.id,
        actor_id=getattr(
            message.from_user,
            "id",
            None
        ),
        detail={
            "caption": caption
        },
    )

    rep = await message.reply(
        "Caption saved successfully.\n\n"
        f"New caption:\n<code>{caption}</code>"
    )

    asyncio.create_task(
        delete_messages(message, rep)
    )


# =========================================================
# CAPTION PREVIEW
# =========================================================

@Client.on_message(
    filters.command("caption_preview") & filters.channel
)
async def caption_preview(bot, message):

    template = (
        message.text.split(" ", 1)[1].strip()
        if len(message.command) > 1
        else None
    )

    if not template:

        caption_doc = await get_channel_caption(
            message.chat.id
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

        rep = await message.reply(
            f"Template error: "
            f"<code>{invalid_fields}</code>"
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    preview = render_template(
        template,
        None,
        SAMPLE_FILE_NAME,
        SAMPLE_CAPTION
    )

    rep = await message.reply(
        f"<b>Caption preview</b>\n\n{preview}"
    )

    asyncio.create_task(
        delete_messages(message, rep)
    )


# =========================================================
# CAPTION VARIABLES
# =========================================================

@Client.on_message(
    filters.command("caption_vars") & filters.channel
)
async def caption_vars(bot, message):

    rep = await message.reply(
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

    asyncio.create_task(
        delete_messages(message, rep)
    )


# =========================================================
# CHANNEL SETTINGS
# =========================================================

@Client.on_message(
    filters.command("settings") & filters.channel
)
async def channel_settings(bot, message):

    caption_doc = await get_channel_caption(
        message.chat.id
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

    rep = await message.reply(
        "<b>Channel settings</b>\n\n"
        f"<b>Caption mode:</b> <code>{mode}</code>\n"
        f"<b>Template:</b>\n<code>{template}</code>"
    )

    asyncio.create_task(
        delete_messages(message, rep)
    )


# =========================================================
# CHANNEL STATS
# =========================================================

@Client.on_message(
    filters.command("channel_stats") & filters.channel
)
async def channel_stats(bot, message):

    stats = await get_channel_stats(
        message.chat.id
    )

    rep = await message.reply(
        "<b>Channel stats</b>\n\n"
        f"<b>Caption edits:</b> "
        f"<code>{stats.get('caption_edits', 0)}</code>"
    )

    asyncio.create_task(
        delete_messages(message, rep)
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
    & filters.channel
)
async def del_caption(_, message):

    result = await delete_channel_caption(
        message.chat.id
    )

    if result.deleted_count:

        await add_audit_log(
            "caption_deleted",
            message.chat.id,
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
PROGRESS_UPDATE_EVERY = 5       # update progress message every N chunks

# In-memory (per-process) state.
# Stop flags and the range-flow Q&A are per-channel and
# reset if the bot restarts — but the MongoDB checkpoint
# still lets /recaption_all resume a stopped/interrupted job.

recaption_stop_flags = {}     # channel_id -> True (stop requested)
recaption_range_state = {}    # channel_id -> {"stage": ..., "top_id": _id": ...}
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

                elif msg.caption == target_caption:

                    skipped += 1

                else:

                    await msg.edit_caption(
                        target_caption
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

                    if file_name and msg.caption != target_caption:

                        await msg.edit_caption(
                            target_caption
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
    filters.command("stop_recaption") & filters.channel
)
async def stop_recaption(bot, message):

    channel_id = message.chat.id

    recaption_stop_flags[channel_id] = True

    rep = await message.reply(
        "🛑 <b>Stop requested.</b>\n\n"
        "The running recaption job will stop after "
        "finishing its current batch.\n\n"
        "Progress is saved — run <code>/recaption_all</code> "
        "anytime to resume from where it stopped."
    )

    asyncio.create_task(
        delete_messages(message, rep)
    )


# =========================================================
# CANCEL (used to cancel the /recaption_range Q&A flow)
# =========================================================

@Client.on_message(
    filters.command("cancel") & filters.channel
)
async def cancel_range_flow(bot, message):

    channel_id = message.chat.id

    if channel_id in recaption_range_state:

        recaption_range_state.pop(channel_id, None)

        rep = await message.reply("❌ Cancelled.")
        asyncio.create_task(delete_messages(message, rep))


# =========================================================
# RECAPTION RANGE
#
# /recaption_range
#
# Interactive flow — bot asks for the TOP message ID,
# then the BOTTOM message ID, then the new caption,
# and scans only that range.
# =========================================================

@Client.on_message(
    filters.command("recaption_range") & filters.channel
)
async def recaption_range_start(bot, message):

    channel_id = message.chat.id

    recaption_range_state[channel_id] = {
        "stage": "top",
        "requested_by": getattr(message.from_user, "id", None),
    }

    await message.reply(
        "<b>Custom range recaption</b>\n\n"
        "Send the <b>TOP</b> message ID "
        "(the newer / higher one) to start from.\n\n"
        "Send <code>/cancel</code> anytime to cancel."
    )


@Client.on_message(
    filters.channel
    & filters.text
    & filters.create(
        lambda _, __, m: m.chat.id in recaption_range_state
    )
)
async def recaption_range_collect(bot, message):

    channel_id = message.chat.id
    state = recaption_range_state.get(channel_id)

    if not state:
        return

    text = (message.text or "").strip()

    # -----------------------------------------------------
    # Stage 1: TOP id
    # -----------------------------------------------------

    if state["stage"] == "top":

        if not text.isdigit():
            await message.reply(
                "❌ Please send a valid numeric message ID."
            )
            return

        state["top_id"] = int(text)
        state["stage"] = "bottom"

        await message.reply(
            "Got it. Now send the <b>BOTTOM</b> message ID "
            "(the older / lower one) to stop at."
        )
        return

    # -----------------------------------------------------
    # Stage 2: BOTTOM id
    # -----------------------------------------------------

    if state["stage"] == "bottom":

        if not text.isdigit():
            await message.reply(
                "❌ Please send a valid numeric message ID."
            )
            return

        bottom_id = int(text)
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

        top_id = state["top_id"]
        bottom_id = state["bottom_id"]

        recaption_range_state.pop(channel_id, None)

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
    & filters.channel
)
async def recaption_all(bot, message):

    channel_id = message.chat.id

    old_job = await get_recaption_progress(
        channel_id
    )

    if len(message.command) < 2 and not old_job:

        rep = await message.reply(
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

        asyncio.create_task(
            delete_messages(message, rep)
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
        start_id = message.id - 1
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
