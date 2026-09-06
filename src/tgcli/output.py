"""Shared output helpers: errors, JSON pretty-print, row formatters."""

import contextlib
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


def fmt_message_row(msg: Any) -> str:
    if msg.text:
        body = " ".join(msg.text.split())[:200]
    elif msg.media:
        body = f"[{type(msg.media).__name__}]"
    else:
        body = "[empty]"
    sender = getattr(msg, "sender_id", None) or "?"
    with contextlib.suppress(Exception):
        sender = msg.sender.first_name if msg.sender else sender
    out_mark = ">" if msg.out else " "
    return f"[{msg.id}] {fmt_date(msg.date)} {out_mark}{sender}: {body}"
