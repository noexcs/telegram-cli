"""Shared output helpers: errors, JSON pretty-print, row formatters."""

import contextlib
import json
from datetime import datetime
from typing import Any

from telethon import types


class TgError(Exception):
    """Command error carrying an optional fix hint and exit code."""

    def __init__(self, msg: str, hint: str | None = None, code: int = 1):
        super().__init__(msg)
        self.hint = hint
        self.code = code


def json_pp(obj: Any) -> str:
    """Pretty-print JSON-ish data; fall back to a plain string."""
    try:
        if isinstance(obj, str):
            obj = json.loads(obj)
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return str(obj)


def fmt_date(dt: Any) -> str:
    """ISO-ish 'YYYY-MM-DD HH:MM' in local time."""
    if not isinstance(dt, datetime):
        return str(dt)[:16].replace("T", " ")
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def fmt_message_row(msg: Any, *, full: bool = False) -> str:
    """One-line message row. `full` disables the 200-char text cut."""
    if msg.text:
        body = " ".join(msg.text.split())
        if not full:
            body = body[:200]
    elif msg.media:
        body = _fmt_media(msg.media)
    else:
        body = "[empty]"
    sender = getattr(msg, "sender_id", None) or "?"
    with contextlib.suppress(Exception):
        sender = msg.sender.first_name if msg.sender else sender
    out_mark = ">" if msg.out else " "
    return f"[{msg.id}] {fmt_date(msg.date)} {out_mark}{sender}: {body}"


def _fmt_size(n: float) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{n}B"


def _fmt_media(media: Any) -> str:
    """Human-readable summary of a media object (audio title, file name, ...)."""
    name = type(media).__name__
    try:
        if isinstance(media, types.MessageMediaDocument):
            doc = media.document
            parts: list[str] = []
            for a in getattr(doc, "attributes", []) or []:
                if isinstance(a, types.DocumentAttributeAudio):
                    label = "voice" if getattr(a, "voice", None) else "audio"
                    parts.append(label)
                    if getattr(a, "performer", None):
                        parts.append(a.performer)
                    if getattr(a, "title", None):
                        parts.append(f"— {a.title}")
                    if getattr(a, "duration", None):
                        parts.append(f"{int(a.duration)}s")
                elif isinstance(a, types.DocumentAttributeFilename):
                    parts.append(a.file_name)
                elif isinstance(a, types.DocumentAttributeVideo):
                    parts.append(f"video {int(getattr(a, 'duration', 0))}s")
                elif isinstance(a, types.DocumentAttributeSticker):
                    parts.append("sticker")
                elif isinstance(a, types.DocumentAttributeAnimated):
                    parts.append("gif")
            parts.append(getattr(doc, "mime_type", "") or "")
            if getattr(doc, "size", None):
                parts.append(_fmt_size(doc.size))
            body = " ".join(x for x in parts if x).replace("  ", " ")
            return f"[{name} {body}]".rstrip()
        if isinstance(media, types.MessageMediaWebPage):
            wp = media.webpage
            title = getattr(wp, "title", None) or getattr(wp, "author", None) or ""
            url = getattr(wp, "url", None) or ""
            return f"[webpage {title} {url}]".strip()
        if isinstance(media, types.MessageMediaPhoto):
            return "[photo]"
        if isinstance(media, types.MessageMediaContact):
            return "[contact]"
        if isinstance(media, types.MessageMediaGeo):
            return "[location]"
    except Exception:  # never let formatting break the row
        pass
    return f"[{name}]"
