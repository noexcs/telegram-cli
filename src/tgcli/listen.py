"""listen — stream new messages as they arrive (no polling).

Runs the connected client's update loop and prints matching messages live.
Useful for waiting on a bot's reply / media delivery, e.g.::

    tg listen 7381828427 --media --once --timeout 300
"""

import asyncio
import contextlib
import os
import sys

from telethon import events, functions

from .client import run_with_client
from .output import TgError, fmt_message_row
from .resolve import resolve_chat


def _chat_label(chat) -> str:
    if chat is None:
        return "?"
    title = getattr(chat, "title", None)
    if title:
        return title
    name = " ".join(
        x for x in (getattr(chat, "first_name", None), getattr(chat, "last_name", None)) if x
    )
    if name:
        return name
    return getattr(chat, "username", None) or str(getattr(chat, "id", "?"))


async def _keep_update_route(client, done: asyncio.Event, interval: float = 12.0) -> None:
    """Best-effort keep-alive: re-request GetState on an interval.

    Telegram routes pushed updates to the *newest* connection of a session,
    so a concurrent tg command temporarily takes delivery over (observed:
    the older listener does not recover until it reconnects). GetState alone
    cannot force the route back, but it keeps this socket warm and synced.
    """
    while not done.is_set():
        await asyncio.sleep(interval)
        with contextlib.suppress(Exception):
            await client(functions.updates.GetStateRequest())


async def cmd_listen(args) -> None:
    async with run_with_client(args) as client:
        target_id = None
        if args.chat:
            entity = await resolve_chat(client, args.chat)
            target_id = getattr(entity, "id", None)
            print(f"listening for new messages in {args.chat} ...", flush=True)
        else:
            print("listening for new messages in all chats ...", flush=True)

        done = asyncio.Event()

        async def on_message(event) -> None:
            msg = event.message
            if msg is None:
                return
            if args.media and not getattr(msg, "media", None):
                return
            if target_id is not None and event.chat_id != target_id:
                return
            prefix = ""
            if target_id is None:
                prefix = f"[{_chat_label(event.chat)}] "
            print(prefix + fmt_message_row(msg, full=True), flush=True)
            if args.once:
                done.set()

        client.add_event_handler(on_message, events.NewMessage())
        if os.environ.get("TGC_DEBUG_LISTEN"):
            async def on_raw(update) -> None:
                print(f"RAW {type(update).__name__}", flush=True)

            client.add_event_handler(on_raw, events.Raw())
        keepalive = asyncio.ensure_future(_keep_update_route(client, done))
        try:
            if args.once:
                # run_until_disconnected keeps the socket alive for updates
                # while we wait for the first matching message
                runner = asyncio.ensure_future(client.run_until_disconnected())
                try:
                    await asyncio.wait_for(done.wait(), timeout=args.timeout or None)
                finally:
                    if not done.is_set():
                        runner.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await runner
            elif args.timeout:
                await asyncio.wait_for(
                    asyncio.shield(client.run_until_disconnected()), timeout=args.timeout
                )
            else:
                await client.run_until_disconnected()
        except asyncio.TimeoutError:
            print("timeout: no matching message arrived", file=sys.stderr)
            raise TgError("no matching message within the timeout", code=3) from None
        finally:
            keepalive.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keepalive


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser(
        "listen",
        parents=parents,
        help='Stream new messages live, e.g. tg listen "Music Bot" --media --once --timeout 300',
    )
    sp.add_argument(
        "chat", nargs="?", default=None, help="restrict to one chat (default: all chats)"
    )
    sp.add_argument("--media", action="store_true", help="only messages that carry media")
    sp.add_argument("--once", action="store_true", help="exit after the first matching message")
    sp.add_argument(
        "--timeout", type=int, default=0, help="give up after N seconds (0 = wait forever)"
    )
    sp.set_defaults(func=cmd_listen)
