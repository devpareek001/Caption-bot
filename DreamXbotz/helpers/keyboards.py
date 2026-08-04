from pyrogram import types
from config import Settings


def start_buttons():
    rows = []
    first_row = []

    if Settings.CHANNEL_URL:
        first_row.append(types.InlineKeyboardButton("Main Channel", url=Settings.CHANNEL_URL))
    if Settings.SUPPORT_URL:
        first_row.append(types.InlineKeyboardButton("Help Group", url=Settings.SUPPORT_URL))
    if first_row:
        rows.append(first_row)

    if Settings.SOURCE_URL:
        rows.append([types.InlineKeyboardButton("Source Code", url=Settings.SOURCE_URL)])

    return types.InlineKeyboardMarkup(rows) if rows else None


def force_subscribe_buttons():
    return types.InlineKeyboardMarkup(
        [[types.InlineKeyboardButton("Join Update Channel", url=f"https://t.me/{Settings.FORCE_SUB}")]]
    )
