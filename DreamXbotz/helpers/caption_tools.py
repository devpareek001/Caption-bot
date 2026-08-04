import re
from string import Formatter


ALLOWED_PLACEHOLDERS = {"file_name", "caption", "language", "year", "quality", "file_size", "duration", "season", "episode"}
TELEGRAM_CAPTION_LIMIT = 1024
LANGUAGE_PATTERN = re.compile(
    r"\b(Hindi|English|Tamil|Bhojpuri|Nepali|Punjabi|Telugu|Malayalam|Kannada|Marathi|Bengali|Gujarati|Urdu|Hin)\b",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
QUALITY_PATTERN = re.compile(r"\b(1080p|720p|480p|360p|2160p|4k|8k)\b", re.IGNORECASE)


def clean_file_name(file_name):
    file_name = file_name or ""
    file_name = re.sub(r"(?i)@\w+|https?://\S+|www\.\S+|t\.me/\S+", "", file_name)
    file_name = re.sub(r"[_\.]+", " ", file_name)
    return re.sub(r"\s+", " ", file_name).strip() or "Untitled"


def extract_language(file_name):
    languages = {lang.title() for lang in LANGUAGE_PATTERN.findall(file_name or "")}
    if "Hin" in languages:
        languages.discard("Hin")
        languages.add("Hindi")
    return ", ".join(sorted(languages)) if languages else "Hindi-English"


def extract_year(file_name):
    match = YEAR_PATTERN.search(file_name or "")
    return match.group(1) if match else None


def extract_quality(file_name):
    match = QUALITY_PATTERN.search(file_name or "")
    return match.group(1) if match else ""


def extract_season_episode(file_name):
    season, episode = "", ""
    match = re.search(r"(?i)s(\d{1,2})[\s\-]*e(\d{1,2})", file_name or "")
    if match:
        season = f"S{match.group(1).zfill(2)}"
        episode = f"E{match.group(2).zfill(2)}"
    return season, episode


def extract_file_size(message):
    if message is None:
        return "1.50 GB"
    size = 0
    for file_type in ("video", "audio", "document", "voice"):
        media = getattr(message, file_type, None)
        if media and getattr(media, "file_size", None):
            size = media.file_size
            break
    if not size:
        return ""
    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    return f"{size / (1024 ** 3):.2f} GB"


def extract_duration(message):
    if message is None:
        return "02:15:30"
    duration = 0
    for file_type in ("video", "audio", "voice"):
        media = getattr(message, file_type, None)
        if media and getattr(media, "duration", None):
            duration = media.duration
            break
    if not duration:
        return ""
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def template_context(message, file_name, caption):
    season, episode = extract_season_episode(file_name)
    return {
        "file_name": file_name,
        "caption": caption or file_name,
        "language": extract_language(file_name),
        "year": extract_year(file_name) or "",
        "quality": extract_quality(file_name),
        "file_size": extract_file_size(message),
        "duration": extract_duration(message),
        "season": season,
        "episode": episode,
    }


def validate_template(template):
    try:
        fields = {
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        }
    except ValueError as exc:
        return False, str(exc)
    invalid_fields = sorted(fields - ALLOWED_PLACEHOLDERS)
    return not invalid_fields, ", ".join(invalid_fields)


def render_template(template, message, file_name, caption):
    rendered = template.format(**template_context(message, file_name, caption))
    return trim_caption(rendered)


def trim_caption(caption):
    if len(caption) <= TELEGRAM_CAPTION_LIMIT:
        return caption
    return caption[: TELEGRAM_CAPTION_LIMIT - 3].rstrip() + "..."


def media_file_name(message):
    for file_type in ("video", "audio", "document", "voice"):
        media = getattr(message, file_type, None)
        if media:
            raw_name = getattr(media, "file_name", "") or message.caption or file_type.title()
            return clean_file_name(raw_name)
    return None
