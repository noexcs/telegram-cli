"""Chat / search / contacts / profile commands."""

from datetime import datetime

from telethon import functions, types

from .client import run_with_client
from .output import TgError, fmt_message_row, json_pp
from .resolve import resolve_chat


async def cmd_me(args) -> None:
    async with run_with_client(args) as client:
        me = await client.get_me()
        print(json_pp(me.to_dict() if me else {}))


async def cmd_chats(args) -> None:
    async with run_with_client(args) as client:
        dialogs = await client.get_dialogs(limit=args.limit)
        q = args.query.lower() if args.query else None
        rows = []
        for d in dialogs:
            kind = kind_of(d)
            if args.type and kind != args.type:
                continue
            if args.unread and not d.unread_count:
                continue
            if args.archived is not None and bool(d.archived) != args.archived:
                continue
            name = d.name or ""
            uname = getattr(d.entity, "username", None) or ""
            if q and q not in f"{name} {uname}".lower():
                continue
            rows.append((d, kind, name, uname))
        if args.json:
            print(
                json_pp(
                    [
                        {
                            "id": d.id,
                            "name": name,
                            "username": uname,
                            "type": kind,
                            "unread": d.unread_count,
                            "muted": muted_of(d),
                            "archived": d.archived,
                        }
                        for d, kind, name, uname in rows
                    ]
                )
            )
            return
        if not rows:
            print("(no chats matched)")
            return
        for d, kind, name, uname in rows:
            mark = "M" if muted_of(d) else " "
            unread_s = f"({d.unread_count})" if d.unread_count else ""
            print(f"{kind:<8} {d.id:>14} {mark}{unread_s:<5} {name} {'@' + uname if uname else ''}")


def kind_of(d) -> str:
    if d.is_group:
        return "group"
    if d.is_channel:
        return "channel"
    return "user"


def muted_of(d) -> bool:
    # The custom Dialog wrapper drops the mute state; read it from the raw dialog.
    notify = getattr(getattr(d, "dialog", None), "notify_settings", None)
    mute_until = getattr(notify, "mute_until", None)
    if not mute_until:
        return False
    # an unmuted chat sends mute_until=0, which telethon deserializes as
    # datetime(1970, ...) — truthy but in the past, i.e. not muted
    return mute_until > datetime.now(mute_until.tzinfo)


async def cmd_hist(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msgs = await client.get_messages(entity, limit=args.n)
        if not msgs:
            print("(no messages)")
            return
        if args.json:
            print(json_pp([m.to_dict() for m in msgs]))
            return
        for m in msgs:
            print(fmt_message_row(m))


async def cmd_pinned(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        # telethon 1.44 removed get_pinned_messages; use the raw search
        res = await client(
            functions.messages.SearchRequest(
                peer=entity,
                q="",
                filter=types.InputMessagesFilterPinned(),
                min_date=None,
                max_date=None,
                offset_id=0,
                add_offset=0,
                limit=10,
                max_id=0,
                min_id=0,
                hash=0,
            )
        )
        msgs = getattr(res, "messages", [])
        if not msgs:
            print("No pinned messages found in this chat.")
            return
        print(json_pp([m.to_dict() for m in msgs]))


async def cmd_search(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msgs = await client.get_messages(entity, search=args.query, limit=args.n)
        if not msgs:
            print("(no matches)")
            return
        print(json_pp([m.to_dict() for m in msgs]))


async def cmd_gsearch(args) -> None:
    async with run_with_client(args) as client:
        req = functions.messages.SearchGlobalRequest(
            q=args.query,
            filter=types.InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_rate=0,
            offset_peer=types.InputPeerEmpty(),
            offset_id=0,
            limit=20,
        )
        results: list = []
        page = args.page
        while page > 0:
            res = await client(req)
            results.extend(getattr(res, "messages", []))
            if not isinstance(res, (types.messages.MessagesSlice, types.messages.ChannelMessages)):
                break
            if not res.next_rate:
                break
            req.offset_rate, req.offset_peer, req.offset_id = (
                res.next_rate,
                res.next_peer,
                res.next_id,
            )
            page -= 1
        if not results:
            print("(no results)")
            return
        print(json_pp([m.to_dict() for m in results]))


async def cmd_contacts(args) -> None:
    async with run_with_client(args) as client:
        res = await client(functions.contacts.GetContactsRequest(hash=0))
        print(json_pp([u.to_dict() for u in res.users]))


async def cmd_profile(args) -> None:
    if not (args.name or args.bio or args.photo):
        raise TgError("nothing to update; pass at least one of --name / --bio / --photo")
    async with run_with_client(args) as client:
        if args.name:
            first, _, last = args.name.partition(" ")
            await client(
                functions.account.UpdateProfileRequest(first_name=first, last_name=last or "")
            )
        if args.bio:
            await client(functions.account.UpdateProfileRequest(about=args.bio))
        if args.photo:
            uploaded = await client.upload_file(args.photo)
            await client(functions.photos.UploadProfilePhotoRequest(file=uploaded))
        me = await client.get_me()
        print(json_pp(me.to_dict() if me else {}))


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser("me", parents=parents, help="Show your account info")
    sp.set_defaults(func=cmd_me)

    sp = subparsers.add_parser(
        "chats", parents=parents, help="List dialogs (optional keyword filter)"
    )
    sp.add_argument("query", nargs="?", default=None, help="filter by name/username")
    sp.add_argument("-n", "--limit", type=int, default=20)
    sp.add_argument("-t", "--type", choices=["user", "group", "channel"])
    sp.add_argument("-u", "--unread", action="store_true", help="unread only")
    sp.add_argument("--archived", action="store_true", default=None, help="archived only")
    sp.set_defaults(func=cmd_chats)

    sp = subparsers.add_parser(
        "hist", parents=parents, help='Show recent messages, e.g. tg hist "Music Bot" 10'
    )
    sp.add_argument("chat")
    sp.add_argument("n", nargs="?", type=int, default=10, help="count (default 10)")
    sp.set_defaults(func=cmd_hist)

    sp = subparsers.add_parser("pinned", parents=parents, help="Show pinned messages of a chat")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_pinned)

    sp = subparsers.add_parser("search", parents=parents, help="Search messages inside a chat")
    sp.add_argument("chat")
    sp.add_argument("query")
    sp.add_argument("-n", "--limit", type=int, default=20, dest="n")
    sp.set_defaults(func=cmd_search)

    sp = subparsers.add_parser("gsearch", parents=parents, help="Global search across public chats")
    sp.add_argument("query")
    sp.add_argument("-p", "--page", type=int, default=1)
    sp.set_defaults(func=cmd_gsearch)

    sp = subparsers.add_parser("contacts", parents=parents, help="List contacts")
    sp.set_defaults(func=cmd_contacts)

    sp = subparsers.add_parser(
        "profile", parents=parents, help="Update your profile (name / bio / photo)"
    )
    sp.add_argument("--name", default=None, help='first and last name, e.g. "John Doe"')
    sp.add_argument("--bio", default=None)
    sp.add_argument("--photo", default=None, help="path to an image")
    sp.set_defaults(func=cmd_profile)
