# Dev tz Caption Bot

Telegram channel auto-caption bot built with Pyrogram, MongoDB, and aiohttp.

## Features

- Automatically edits captions for channel video, audio, voice, and document posts.
- Per-channel custom captions with `/set_caption`.
- Default caption fallback with configurable `DEF_CAP`.
- Force-subscribe gate for private bot users.
- Admin-only `/status`, `/users`, `/broadcast`, and `/restart`.
- Caption preview, channel settings, channel stats, and audit logging.
- MongoDB user/channel storage.
- Lightweight aiohttp health endpoint for web deployments.

## Caption Placeholders

Custom captions can use:

```text
{file_name}
{caption}
{language}
{year}
```

Example:

```text
/set_caption <b>{file_name}</b>

Language: {language}
Year: {year}
Main Channel: @dreamxbotz
```

## BotFather Commands

```text
start - Start the bot
set_caption - Set a custom channel caption
del_caption - Delete the custom channel caption
caption_preview - Preview current or provided caption template
caption_vars - Show available caption placeholders
settings - Show channel caption settings
channel_stats - Show channel caption edit stats
status - Show bot status, uptime, ping, and users
users - Show bot status, uptime, ping, and users
broadcast - Broadcast a replied message to all saved users
restart - Restart the bot
```

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Bot token from BotFather |
| `API_ID` | Yes | Telegram API ID from my.telegram.org |
| `API_HASH` | Yes | Telegram API hash from my.telegram.org |
| `DB_URL` | Yes | MongoDB connection URL |
| `ADMINS` | Yes | Admin user IDs separated by spaces |
| `DB_NAME` | No | MongoDB database name |
| `FORCE_SUB` | No | Required channel username without `@` |
| `BOT_USERNAME` | No | Pyrogram session name, defaults to `Dreamxbotz_caption` |
| `BOT_PIC` | No | Start message image URL |
| `DEF_CAP` | No | Default caption template |
| `CHANNEL_URL` | No | Main channel button URL, defaults to `https://t.me/dreamxbotz` |
| `SUPPORT_URL` | No | Optional help group button URL |
| `SOURCE_URL` | No | Optional source-code button URL |
| `WORKERS` | No | Pyrogram worker count, defaults to `200` |
| `LOG_LEVEL` | No | Logging level, defaults to `INFO` |
| `PORT` | No | Web server port, defaults to `8080` |

`START_PIC` is still accepted as a fallback for older deployments, but `BOT_PIC` is preferred.

## Deploy

The bot can run anywhere Python apps are supported.

```bash
pip install -r requirements.txt
python bot.py
```

Health endpoints:

```text
/
/health
/metrics
```

Repository URL used by deploy manifests:

```text
https://github.com/DreamXBotz/Auto_Caption.git
```
