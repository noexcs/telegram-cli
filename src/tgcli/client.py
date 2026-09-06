"""Telethon client factory and per-invocation lifecycle."""

import contextlib
import os
from collections.abc import AsyncIterator

from telethon import TelegramClient
from telethon.sessions import StringSession

from . import config
from .output import TgError


def build_client(session: str | StringSession, api_id: int, api_hash: str) -> TelegramClient:
    """Build a client with proxy and device identity injected."""
    kwargs: dict = {}
    proxy = config.build_proxy()
    if proxy is None:
        raise TgError(
            "No proxy configured (TELEGRAM_PROXY_TYPE/HOST/PORT are empty)",
            "Telegram is unreachable directly from this network; set the proxy in .env "
            "(e.g. socks5 127.0.0.1:7890 for Clash)",
            code=2,
        )
    kwargs["proxy"] = proxy
    for kw, env in (
        ("device_model", "TELEGRAM_DEVICE_MODEL"),
        ("system_version", "TELEGRAM_SYSTEM_VERSION"),
        ("app_version", "TELEGRAM_APP_VERSION"),
    ):
        if os.environ.get(env):
            kwargs[kw] = os.environ[env]
    return TelegramClient(session, api_id, api_hash, **kwargs)


@contextlib.asynccontextmanager
async def run_with_client(args) -> AsyncIterator[TelegramClient]:
    """One short-lived client per invocation: connect → yield → disconnect."""
    api_id, api_hash = config.require_credentials()
    session_str = config.load_session(getattr(args, "account", None))
    client = build_client(StringSession(session_str), api_id, api_hash)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()
