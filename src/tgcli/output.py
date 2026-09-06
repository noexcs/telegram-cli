"""Shared output helpers: errors, JSON pretty-print, row formatters."""

import json
from datetime import datetime
from typing import Any


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


def fmt_chat_row(chat: Any) -> str:
    name = getattr(chat, "title", None) or getattr(chat, "first_name", None) or ""
    uname = getattr(chat, "username", None)
    unread = getattr(chat, "dialog", None)
    unread_n = unread.unread_count if unread else 0
    muted = unread.unread_mark if unread else False
    mark = "M" if muted else " "
    unread_s = f"({unread_n})" if unread_n else ""
    kind = type(chat).__name__.replace("Channel", "channel").replace("Chat", "group").replace("User", "user")
    return f"{kind:<8} {chat.id:>14} {mark}{unread_s:<5} {name} {'@' + uname if uname else ''}"


def fmt_message_row(msg: Any) -> str:
    if msg.text:
        body = " ".join(msg.text.split())[:200]
    elif msg.media:
        body = f"[{type(msg.media).__name__}]"
    else:
        body = "[empty]"
    sender = getattr(msg, "sender_id", None) or "?"
    try:
        sender = msg.sender.first_name if msg.sender else sender
    except Exception:
        pass
    out_mark = ">" if msg.out else " "
    return f"[{msg.id}] {fmt_date(msg.date)} {out_mark}{sender}: {body}"
