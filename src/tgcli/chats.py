"""Chat / search / contacts / profile / privacy / block commands."""

from datetime import datetime

from telethon import functions, types

from .client import run_with_client
from .output import TgError, fmt_message_row, json_pp
from .resolve import resolve_chat

# friendly names for the privacy keys (value -> InputPrivacyKey class name)
_PRIVACY_KEYS = {
    "lastseen": "InputPrivacyKeyStatusTimestamp",
    "phone": "InputPrivacyKeyPhoneNumber",
    "calls": "InputPrivacyKeyPhoneCall",
    "p2p": "InputPrivacyKeyPhoneP2P",
    "groups": "InputPrivacyKeyChatInvite",
    "photo": "InputPrivacyKeyProfilePhoto",
    "forwards": "InputPrivacyKeyForwards",
    "voicemail": "InputPrivacyKeyVoiceMessages",
    "about": "InputPrivacyKeyAbout",
    "birthday": "InputPrivacyKeyBirthday",
    "addedby": "InputPrivacyKeyAddedByPhone",
}


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
        collected: list = []
        # --media filters client-side (one API call can't cover all media kinds);
        # scan up to 300 messages (or 6x the requested count) to fill the window
        scan_cap = 300 if args.media else args.n
        offset_id = 0
        while len(collected) < args.n and scan_cap > 0:
            batch = await client.get_messages(entity, limit=min(scan_cap, 50), offset_id=offset_id)
            if not batch:
                break
            offset_id = batch[-1].id
            scan_cap -= len(batch)
            for m in batch:
                if args.media and not getattr(m, "media", None):
                    continue
                collected.append(m)
                if len(collected) >= args.n:
                    break
        if not collected:
            print("(no messages)")
            return
        if args.json:
            print(json_pp([m.to_dict() for m in collected]))
            return
        for m in collected:
            print(fmt_message_row(m, full=args.full))


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


async def cmd_photo_del(args) -> None:
    async with run_with_client(args) as client:
        photos = await client.get_profile_photos("me")
        if not photos:
            print("(no profile photos)")
            return
        if not args.all:
            photos = photos[:1]  # just the most recent one
        await client(
            functions.photos.DeletePhotosRequest(
                id=[
                    types.InputPhoto(
                        id=p.id, access_hash=p.access_hash, file_reference=p.file_reference
                    )
                    for p in photos
                ]
            )
        )
        print(f"Deleted {len(photos)} profile photo(s)")


def _privacy_key(name: str) -> types.TypeInputPrivacyKey:
    cls_name = _PRIVACY_KEYS.get(name.lower())
    if not cls_name:
        raise TgError(
            f"unknown privacy key: {name!r}",
            f"choose from: {', '.join(sorted(_PRIVACY_KEYS))}",
        )
    return getattr(types, cls_name)()


def _privacy_rule_text(rule, users: dict) -> str:
    kind = type(rule).__name__.removeprefix("PrivacyValue")
    if kind == "AllowAll":
        return "everyone"
    if kind == "AllowContacts":
        return "contacts"
    if kind == "AllowCloseFriends":
        return "close friends"
    if kind == "AllowBots":
        return "bots"
    if kind == "AllowPremium":
        return "premium"
    if kind == "AllowChatParticipants":
        return "members of " + ", ".join(_display_chat(c, users) for c in rule.chats)
    if kind == "AllowUsers":
        return "+" + ", ".join(_display_chat(users.get(u), users) or str(u) for u in rule.users)
    if kind == "DisallowAll":
        return "nobody"
    if kind == "DisallowContacts":
        return "no contacts"
    if kind == "DisallowUsers":
        return "-" + ", ".join(_display_chat(users.get(u), users) or str(u) for u in rule.users)
    return kind


def _display_chat(chat, users: dict) -> str:
    if chat is None:
        return "?"
    title = getattr(chat, "title", None)
    if title:
        return title
    name = " ".join(
        x for x in (getattr(chat, "first_name", None), getattr(chat, "last_name", None)) if x
    )
    return name or "?"


async def cmd_privacy_get(args) -> None:
    keys = args.key or sorted(_PRIVACY_KEYS)
    async with run_with_client(args) as client:
        rows = []
        for name in keys:
            res = await client(functions.account.GetPrivacyRequest(key=_privacy_key(name)))
            users = {u.id: u for u in getattr(res, "users", []) or []}
            rules = " + ".join(_privacy_rule_text(r, users) for r in res.rules) or "(unset)"
            rows.append((name, rules))
        if args.json:
            print(json_pp([{"key": k, "rules": v} for k, v in rows]))
            return
        for name, rules in rows:
            print(f"{name:<10} {rules}")


def _input_user(client, peer) -> types.TypeInputUser:
    if isinstance(peer, types.InputPeerUser):
        return types.InputUser(user_id=peer.user_id, access_hash=peer.access_hash)
    if isinstance(peer, types.InputPeerSelf):
        return types.InputUserSelf()
    raise TgError("only users can appear in privacy rules")


async def cmd_privacy_set(args) -> None:
    base = args.value.lower()
    base_map = {"all": "everyone", "contacts": "contacts", "nobody": "nobody"}
    if base not in base_map:
        raise TgError(
            f"unknown privacy value: {args.value!r}",
            "use all / contacts / nobody, with optional --allow USER / --deny USER",
        )
    async with run_with_client(args) as client:
        # rules need Input* rule classes and InputUser entries
        resolved_allow = [
            _input_user(client, await client.get_input_entity(await resolve_chat(client, u)))
            for u in args.allow
        ]
        resolved_deny = [
            _input_user(client, await client.get_input_entity(await resolve_chat(client, u)))
            for u in args.deny
        ]
        rules: list = []
        if base == "all":
            rules.append(types.InputPrivacyValueAllowAll())
        elif base == "contacts":
            rules.append(types.InputPrivacyValueAllowContacts())
        else:
            rules.append(types.InputPrivacyValueDisallowAll())
        if resolved_allow:
            rules.append(types.InputPrivacyValueAllowUsers(users=resolved_allow))
        if resolved_deny:
            rules.append(types.InputPrivacyValueDisallowUsers(users=resolved_deny))
        await client(functions.account.SetPrivacyRequest(key=_privacy_key(args.key), rules=rules))
        desc = base_map[base]
        if resolved_allow:
            desc += ", allow " + ", ".join(args.allow)
        if resolved_deny:
            desc += ", deny " + ", ".join(args.deny)
        print(f"{args.key} set to {desc}")


async def cmd_block(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.user)
        await client(functions.contacts.BlockRequest(id=entity))
        print(f"Blocked {args.user}")


async def cmd_unblock(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.user)
        await client(functions.contacts.UnblockRequest(id=entity))
        print(f"Unblocked {args.user}")


async def cmd_blocked(args) -> None:
    async with run_with_client(args) as client:
        res = await client(functions.contacts.GetBlockedRequest(offset=0, limit=100))
        users = {u.id: u for u in getattr(res, "users", []) or []}
        rows = []
        for pb in getattr(res, "blocked", []) or []:
            pid = pb.peer_id.user_id if isinstance(pb.peer_id, types.PeerUser) else pb.peer_id
            rows.append((pid, getattr(pb, "date", None)))
        if args.json:
            print(json_pp([p.to_dict() for p in getattr(res, "blocked", []) or []]))
            return
        if not rows:
            print("(nobody is blocked)")
            return
        for pid, date in rows:
            u = users.get(pid)
            name = _display_chat(u, users) if u else str(pid)
            when = date.astimezone().strftime("%Y-%m-%d") if date else ""
            print(f"{pid:>14}  {name}  {when}")


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
    sp.add_argument("--full", action="store_true", help="do not truncate message text")
    sp.add_argument(
        "--media",
        action="store_true",
        help="only media messages (audio/video/files); scans up to 300 messages",
    )
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

    sp = subparsers.add_parser(
        "photo-del", parents=parents, help="Delete your most recent profile photo (--all for all)"
    )
    sp.add_argument("--all", action="store_true", help="delete every profile photo")
    sp.set_defaults(func=cmd_photo_del)

    sp = subparsers.add_parser("privacy", parents=parents, help="Show privacy settings")
    sub = sp.add_subparsers(dest="privacy_cmd", required=True)
    g = sub.add_parser("get", help="privacy get [key...] (default: all)")
    g.add_argument("key", nargs="*", default=[])
    g.set_defaults(func=cmd_privacy_get)
    s = sub.add_parser(
        "set", help="privacy set KEY all|contacts|nobody [--allow USER] [--deny USER]"
    )
    s.add_argument("key", help=f"one of: {', '.join(sorted(_PRIVACY_KEYS))}")
    s.add_argument("value")
    s.add_argument("-a", "--allow", action="append", default=[], metavar="USER")
    s.add_argument("-d", "--deny", action="append", default=[], metavar="USER")
    s.set_defaults(func=cmd_privacy_set)

    sp = subparsers.add_parser("block", parents=parents, help="Block a user")
    sp.add_argument("user")
    sp.set_defaults(func=cmd_block)

    sp = subparsers.add_parser("unblock", parents=parents, help="Unblock a user")
    sp.add_argument("user")
    sp.set_defaults(func=cmd_unblock)

    sp = subparsers.add_parser("blocked", parents=parents, help="List blocked users")
    sp.set_defaults(func=cmd_blocked)
