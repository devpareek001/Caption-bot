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
# RECAPTION ALL
#
# /recaption_all NEW CAPTION
#
# - Scans Telegram channel history directly
# - Does NOT depend on old DB file records
# - Completely replaces old captions
# - Saves checkpoint in MongoDB
# - Resumes after restart
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

    # -----------------------------------------------------
    # Check whether an old job is already in progress
    # -----------------------------------------------------

    old_job = await get_recaption_progress(
        channel_id
    )

    # -----------------------------------------------------
    # New caption
    # -----------------------------------------------------

    if len(message.command) < 2:

        if old_job:

            saved_caption = old_job.get(
                "caption",
                ""
            )

            rep = await message.reply(
                "⏳ <b>Previous recaption job found.</b>\n\n"
                f"Caption:\n<code>{saved_caption}</code>\n\n"
                f"Last message ID: "
                f"<code>{old_job.get('last_message_id')}</code>\n\n"
                "The job will continue automatically "
                "from the saved checkpoint when you run "
                "<code>/recaption_all</code>."
            )

        else:

            rep = await message.reply(
                "<b>Usage:</b>\n\n"
                "<code>/recaption_all YOUR NEW CAPTION</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/recaption_all "
                "🔥 Dreamxbotz Movies 🔥</code>\n\n"
                "The old caption will be completely replaced."
            )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    command_caption = message.text.split(
        " ",
        1
    )[1].strip()

    if not command_caption:

        rep = await message.reply(
            "❌ New caption cannot be empty."
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    if len(command_caption) > 1024:

        rep = await message.reply(
            "❌ Caption is too long.\n\n"
            "Telegram captions cannot be longer than "
            "<code>1024</code> characters."
        )

        asyncio.create_task(
            delete_messages(message, rep)
        )
        return

    # -----------------------------------------------------
    # If checkpoint exists, ALWAYS use its caption.
    #
    # This prevents accidentally changing the caption
    # halfway through an existing 2 lakh file job.
    # -----------------------------------------------------

    if old_job:

        target_caption = old_job.get(
            "caption",
            command_caption
        )

        last_message_id = old_job.get(
            "last_message_id"
        )

        processed = old_job.get(
            "processed",
            0
        )

        updated = old_job.get(
            "updated",
            0
        )

        skipped = old_job.get(
            "skipped",
            0
        )

        failed = old_job.get(
            "failed",
            0
        )

        resume_text = (
            "♻️ <b>Resuming previous job...</b>\n\n"
            f"Starting after message ID: "
            f"<code>{last_message_id}</code>"
        )

    else:

        target_caption = command_caption

        last_message_id = None

        processed = 0
        updated = 0
        skipped = 0
        failed = 0

        resume_text = (
            "🚀 <b>Starting new recaption job...</b>"
        )

    # -----------------------------------------------------
    # Progress message
    # -----------------------------------------------------

    progress_msg = await message.reply(
        f"{resume_text}\n\n"
        f"<b>Target caption:</b>\n"
        f"<code>{target_caption}</code>\n\n"
        f"Processed: <code>{processed}</code>\n"
        f"Updated: <code>{updated}</code>\n"
        f"Skipped: <code>{skipped}</code>\n"
        f"Failed: <code>{failed}</code>"
    )

    if not old_job:

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
                "mode": "telegram_history",
            },
        )

    # -----------------------------------------------------
    # Telegram history
    #
    # If checkpoint exists, offset_id starts us around
    # the previous message instead of scanning everything.
    # -----------------------------------------------------

    history_kwargs = {}

    if last_message_id:
        history_kwargs["offset_id"] = last_message_id

    try:

        async for msg in bot.get_chat_history(
            channel_id,
            **history_kwargs
        ):

            # -------------------------------------------------
            # Safety: don't process service messages etc.
            # -------------------------------------------------

            try:

                file_name = media_file_name(msg)

            except Exception as exc:

                LOGGER.warning(
                    "Could not detect media for %s: %s",
                    msg.id,
                    exc
                )

                file_name = None

            # -------------------------------------------------
            # Process message
            # -------------------------------------------------

            processed += 1

            try:

                # ---------------------------------------------
                # No media/file
                # ---------------------------------------------

                if not file_name:

                    skipped += 1

                # ---------------------------------------------
                # Caption already same
                # ---------------------------------------------

                elif msg.caption == target_caption:

                    skipped += 1

                # ---------------------------------------------
                # Replace COMPLETE caption
                # ---------------------------------------------

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

                    # Small delay to reduce FloodWait
                    await asyncio.sleep(0.35)

            except FloodWait as e:

                wait_time = flood_wait_seconds(e)

                LOGGER.warning(
                    "FloodWait on message %s. "
                    "Sleeping %s seconds.",
                    msg.id,
                    wait_time,
                )

                await asyncio.sleep(
                    wait_time
                )

                # ---------------------------------------------
                # Retry
                # ---------------------------------------------

                try:

                    if file_name:

                        if msg.caption != target_caption:

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
                    "Recaption failed for "
                    "%s/%s: %s",
                    channel_id,
                    msg.id,
                    exc,
                )

            # -------------------------------------------------
            # SAVE CHECKPOINT
            #
            # Save AFTER processing this message.
            #
            # If bot crashes:
            # it will continue from this message.
            # -------------------------------------------------

            try:

                await save_recaption_progress(
                    channel_id=channel_id,
                    last_message_id=msg.id,
                    caption=target_caption,
                    processed=processed,
                    updated=updated,
                    skipped=skipped,
                    failed=failed,
                )

            except Exception as checkpoint_exc:

                LOGGER.warning(
                    "Could not save checkpoint "
                    "for %s: %s",
                    msg.id,
                    checkpoint_exc,
                )

            # -------------------------------------------------
            # Progress update
            # -------------------------------------------------

            if processed % 50 == 0:

                    try:
        # history wala pura code yahan
        async for msg in bot.get_chat_history(channel_id):

            # tumhara processing code
            pass

    except Exception as history_exc:

        LOGGER.exception(
            "Recaption history stopped for channel %s",
            channel_id
        )

        error_text = (
            f"{type(history_exc).__name__}: "
            f"{str(history_exc)}"
        )

        try:
            await progress_msg.edit(
                "⚠️ <b>Recaption paused!</b>\n\n"
                f"Processed: <code>{processed}</code>\n"
                f"Updated: <code>{updated}</code>\n"
                f"Skipped: <code>{skipped}</code>\n"
                f"Failed: <code>{failed}</code>\n\n"
                f"<b>Error:</b>\n"
                f"<code>{error_text[:3500]}</code>\n\n"
                "♻️ Progress is saved in MongoDB.\n"
                "Run <code>/recaption_all</code> again to continue."
            )
        except Exception:
            pass

        return
    # -----------------------------------------------------
    # JOB COMPLETED
    # -----------------------------------------------------

    await add_audit_log(
        "recaption_all_completed",
        channel_id,
        actor_id=getattr(
            message.from_user,
            "id",
            None
        ),
        detail={
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "caption": target_caption,
        },
    )

    # -----------------------------------------------------
    # Remove checkpoint ONLY after complete success
    # -----------------------------------------------------

    await clear_recaption_progress(
        channel_id
    )

    try:

        await progress_msg.edit(
            "✅ <b>Recaption completed!</b>\n\n"
            f"📨 Messages scanned: "
            f"<code>{processed}</code>\n"
            f"✏️ Captions updated: "
            f"<code>{updated}</code>\n"
            f"⏭ Skipped: "
            f"<code>{skipped}</code>\n"
            f"❌ Failed: "
            f"<code>{failed}</code>\n\n"
            "🎉 All available old files have been processed.\n\n"
            "♻️ Checkpoint removed from MongoDB."
        )

    except Exception:
        pass


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
