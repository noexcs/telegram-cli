"""Chat management: archive, mute, chat info, invite links, history, user status."""

import os
import re
import time
from datetime import datetime

from telethon import functions, types

from .client import run_with_client
from .output import TgError, fmt_date, json_pp
from .resolve import resolve_chat

# "forever" mute: the official clients pin mute_until to a far-future timestamp
_MUTE_FOREVER = 2**31 - 1


async def _input_peer(client, chat):
    return await client.get_input_entity(await resolve_chat(client, chat))


async def cmd_archive(args) -> None:
    await _set_folder(args, 1, "Archived")


async def cmd_unarchive(args) -> None:
    await _set_folder(args, 0, "Unarchived")


async def _set_folder(args, folder: int, done: str) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.edit_folder(entity, folder=folder)
        print(done)


async def cmd_mute(args) -> None:
    if args.hours:
        until = int(time.time()) + args.hours * 3600
        human = f"muted for {args.hours}h"
    else:
        until = _MUTE_FOREVER
        human = "muted permanently"
    await _update_notify(args, until, human)


async def cmd_unmute(args) -> None:
    await _update_notify(args, 0, "unmuted")


async def _update_notify(args, mute_until: int, done: str) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client(
            functions.account.UpdateNotifySettingsRequest(
                peer=entity,
                settings=types.InputPeerNotifySettings(mute_until=mute_until),
            )
        )
        print(done)


async def cmd_chat_title(args) -> None:
    async with run_with_client(args) as client:
        peer = await _input_peer(client, args.chat)
        if isinstance(peer, types.InputPeerChannel):
            await client(functions.channels.EditTitleRequest(channel=peer, title=args.title))
        elif isinstance(peer, types.InputPeerChat):
            await client(
                functions.messages.EditChatTitleRequest(chat_id=peer.chat_id, title=args.title)
            )
        else:
            raise TgError("chat titles can only be changed for groups and channels")
        print("Chat title updated")


async def cmd_chat_about(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client(functions.messages.EditChatAboutRequest(peer=entity, about=args.text))
        print("Chat description updated")


async def cmd_chat_photo(args) -> None:
    path = os.path.expanduser(args.file)
    if not os.path.exists(path):
        raise TgError(f"file not found: {path}")
    async with run_with_client(args) as client:
        peer = await _input_peer(client, args.chat)
        uploaded = await client.upload_file(path)
        photo = types.InputChatUploadedPhoto(file=uploaded)
        if isinstance(peer, types.InputPeerChannel):
            await client(functions.channels.EditPhotoRequest(channel=peer, photo=photo))
        elif isinstance(peer, types.InputPeerChat):
            await client(functions.messages.EditChatPhotoRequest(chat_id=peer.chat_id, photo=photo))
        else:
            raise TgError("chat photos can only be changed for groups and channels")
        print("Chat photo updated")


async def cmd_invite_link(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        res = await client(functions.messages.ExportChatInviteRequest(peer=entity))
        link = getattr(res, "link", None)
        if not link:
            raise TgError("no invite link returned (check your admin rights)")
        print(link)


def _invite_hash(link: str) -> str | None:
    m = re.search(r"t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]+)", link)
    return m.group(1) if m else None


def _invite_username(link: str) -> str | None:
    m = re.search(r"t\.me/([A-Za-z0-9_]{4,})", link)
    return m.group(1) if m else link.lstrip("@")


async def cmd_join(args) -> None:
    async with run_with_client(args) as client:
        h = _invite_hash(args.link)
        if h:
            await client(functions.messages.ImportChatInviteRequest(hash=h))
            print("Joined private group")
            return
        name = _invite_username(args.link)
        await client(functions.channels.JoinChannelRequest(channel=name))
        print(f"Joined @{name}")


async def cmd_clear_history(args) -> None:
    async with run_with_client(args) as client:
        peer = await client.get_input_entity(await resolve_chat(client, args.chat))
        if isinstance(peer, types.InputPeerChannel):
            # supergroups/channels reject messages.DeleteHistoryRequest
            await client(
                functions.channels.DeleteHistoryRequest(
                    channel=peer, max_id=0, for_everyone=not args.self_only
                )
            )
        else:
            await client(
                functions.messages.DeleteHistoryRequest(
                    peer=peer,
                    max_id=0,
                    revoke=not args.self_only,
                )
            )
        scope = "for both sides" if not args.self_only else "locally only"
        print(f"History cleared ({scope})")


def _status_text(status) -> str:
    if isinstance(status, types.UserStatusOnline):
        if status.expires > datetime.now(status.expires.tzinfo):
            return "online"
        return f"last seen {fmt_date(status.expires)}"
    if isinstance(status, types.UserStatusOffline):
        return f"last seen {fmt_date(status.was_online)}"
    if isinstance(status, types.UserStatusRecently):
        return "last seen recently"
    if isinstance(status, types.UserStatusLastWeek):
        return "last seen within a week"
    if isinstance(status, types.UserStatusLastMonth):
        return "last seen within a month"
    if isinstance(status, types.UserStatusLongAgo):
        return "last seen a long time ago"
    return str(status)


async def cmd_status(args) -> None:
    async with run_with_client(args) as client:
        user = await client.get_entity(await resolve_chat(client, args.user))
        name = " ".join(x for x in (user.first_name, user.last_name) if x)
        print(f"{name} ({user.id}): {_status_text(user.status)}")


async def cmd_common_chats(args) -> None:
    async with run_with_client(args) as client:
        peer = await _input_peer(client, args.user)
        if isinstance(peer, types.InputPeerSelf):
            raise TgError("cannot list common chats with yourself")
        if not isinstance(peer, types.InputPeerUser):
            raise TgError(f"'{args.user}' is not a user")
        user = types.InputUser(user_id=peer.user_id, access_hash=peer.access_hash)
        res = await client(
            functions.messages.GetCommonChatsRequest(user_id=user, max_id=0, limit=100)
        )
        chats = getattr(res, "chats", []) or []
        if args.json:
            print(json_pp([c.to_dict() for c in chats]))
            return
        if not chats:
            print("(no common chats)")
            return
        for c in chats:
            title = getattr(c, "title", None) or "?"
            uname = getattr(c, "username", None) or ""
            print(f"{c.id:>14}  {title}  {'@' + uname if uname else ''}")


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser("archive", parents=parents, help="Archive a chat")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_archive)

    sp = subparsers.add_parser("unarchive", parents=parents, help="Unarchive a chat")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_unarchive)

    sp = subparsers.add_parser(
        "mute", parents=parents, help="Mute notifications (permanent unless [hours] given)"
    )
    sp.add_argument("chat")
    sp.add_argument("hours", nargs="?", type=int, default=None)
    sp.set_defaults(func=cmd_mute)

    sp = subparsers.add_parser("unmute", parents=parents, help="Unmute notifications")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_unmute)

    sp = subparsers.add_parser("chat-title", parents=parents, help="Change group/channel title")
    sp.add_argument("chat")
    sp.add_argument("title")
    sp.set_defaults(func=cmd_chat_title)

    sp = subparsers.add_parser("chat-about", parents=parents, help="Change chat description")
    sp.add_argument("chat")
    sp.add_argument("text")
    sp.set_defaults(func=cmd_chat_about)

    sp = subparsers.add_parser("chat-photo", parents=parents, help="Change the chat photo")
    sp.add_argument("chat")
    sp.add_argument("file", help="path to an image")
    sp.set_defaults(func=cmd_chat_photo)

    sp = subparsers.add_parser("invite-link", parents=parents, help="Export a chat invite link")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_invite_link)

    sp = subparsers.add_parser(
        "join", parents=parents, help="Join via t.me link, @username, or invite hash"
    )
    sp.add_argument("link", help="e.g. t.me/+abc123, t.me/joinchat/abc123, or t.me/somechannel")
    sp.set_defaults(func=cmd_join)

    sp = subparsers.add_parser(
        "clear-history",
        parents=parents,
        help="Delete all messages in a chat (both sides; --self-only keeps the other copy)",
    )
    sp.add_argument("chat")
    sp.add_argument(
        "--self-only", action="store_true", help="delete only your own copy (private chats)"
    )
    sp.set_defaults(func=cmd_clear_history)

    sp = subparsers.add_parser("status", parents=parents, help="Show a user's online status")
    sp.add_argument("user")
    sp.set_defaults(func=cmd_status)

    sp = subparsers.add_parser(
        "common-chats", parents=parents, help="List chats you share with a user"
    )
    sp.add_argument("user")
    sp.set_defaults(func=cmd_common_chats)
