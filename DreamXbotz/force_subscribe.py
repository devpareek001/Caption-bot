from pyrogram import Client, enums, filters
from pyrogram.errors import UserNotParticipant
from config import Settings
from .helpers.keyboards import force_subscribe_buttons
from .helpers.logging_setup import get_logger
from .storage import save_user


LOGGER = get_logger("Dreamxbotz.force_subscribe")


async def not_subscribed(_, client, message):
    if not message.from_user:
        return False

    await save_user(int(message.from_user.id))
    if not Settings.FORCE_SUB:
        return False

    try:
        user = await client.get_chat_member(Settings.FORCE_SUB, message.from_user.id)
        return user.status in {enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT}
    except UserNotParticipant:
        return True
    except Exception as exc:
        LOGGER.warning("Force-sub check failed for %s: %s", message.from_user.id, exc)
        return False


@Client.on_message(filters.private & filters.create(not_subscribed))
async def force_subscribe(client, message):
    text = (
        "You need to join our update channel before using this bot.\n\n"
        "Join the channel, then send /start again."
    )

    try:
        user = await client.get_chat_member(Settings.FORCE_SUB, message.from_user.id)
        if user.status == enums.ChatMemberStatus.BANNED:
            await client.send_message(
                message.from_user.id,
                "You are banned from the required update channel.",
            )
            return message.stop_propagation()
    except UserNotParticipant:
        pass

    await message.reply_text(text=text, reply_markup=force_subscribe_buttons())
    return message.stop_propagation()
