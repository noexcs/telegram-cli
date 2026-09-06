"""Public surface discovery: search chats, resolve usernames, stickers,
user photos, bot info/commands."""

from telethon import functions, types

from .client import run_with_client
from .output import TgError, json_pp
from .resolve import resolve_chat


def _marked(peer) -> int:
    """Marked id (-100 prefix for channels) via the peer's bare id/type."""
    if isinstance(peer, types.PeerChannel):
        return int(f"-100{peer.channel_id}")
    if isinstance(peer, types.PeerUser):
        return peer.user_id
    if isinstance(peer, types.PeerChat):
        return -peer.chat_id
    return 0


async def cmd_search_public(args) -> None:
    async with run_with_client(args) as client:
        res = await client(functions.contacts.SearchRequest(q=args.query, limit=args.n))
        chats = getattr(res, "chats", []) or []
        users = getattr(res, "users", []) or []
        if args.json:
            print(
                json_pp(
                    {"chats": [c.to_dict() for c in chats], "users": [u.to_dict() for u in users]}
                )
            )
            return
        if not chats and not users:
            print("(no results)")
            return
        for c in chats:
            uname = getattr(c, "username", None) or ""
            kind = "channel" if getattr(c, "broadcast", False) else "group"
            print(f"{c.id:>14}  {kind:<8} {c.title}  {'@' + uname if uname else ''}")
        for u in users:
            name = " ".join(x for x in (u.first_name, u.last_name) if x)
            uname = getattr(u, "username", None) or ""
            print(f"{u.id:>14}  {'user':<8} {name}  {'@' + uname if uname else ''}")


async def cmd_resolve(args) -> None:
    async with run_with_client(args) as client:
        res = await client(
            functions.contacts.ResolveUsernameRequest(username=args.username.lstrip("@"))
        )
        peer = res.peer
        chats = {c.id: c for c in getattr(res, "chats", []) or []}
        users = {u.id: u for u in getattr(res, "users", []) or []}
        if isinstance(peer, types.PeerUser):
            u = users.get(peer.user_id)
            name = (
                " ".join(
                    x for x in (getattr(u, "first_name", None), getattr(u, "last_name", None)) if x
                )
                if u
                else "?"
            )
            print(f"user    {peer.user_id:>14}  {name}")
        elif isinstance(peer, types.PeerChannel):
            c = chats.get(peer.channel_id)
            title = getattr(c, "title", "?") if c else "?"
            kind = "supergroup" if getattr(c, "megagroup", False) else "channel"
            print(f"{kind}  -100{peer.channel_id}  {title}")
        else:
            print(peer)


async def cmd_stickers(args) -> None:
    async with run_with_client(args) as client:
        res = await client(functions.messages.GetAllStickersRequest(hash=0))
        sets = getattr(res, "sets", []) or []
        if args.json:
            print(json_pp([s.to_dict() for s in sets]))
            return
        if not sets:
            print("(no sticker sets)")
            return
        for s in sets:
            flag = "*" if getattr(s, "installed", False) else " "
            print(f"{s.id:>14} {flag} {s.title}  ({s.count})")
            print(f"            t.me/addstickers/{s.short_name}")


async def cmd_user_photos(args) -> None:
    async with run_with_client(args) as client:
        user = await resolve_chat(client, args.user)
        res = await client(
            functions.photos.GetUserPhotosRequest(user_id=user, offset=0, max_id=0, limit=args.n)
        )
        photos = getattr(res, "photos", []) or []
        if args.json:
            print(json_pp([p.to_dict() for p in photos]))
            return
        if not photos:
            print("(no profile photos)")
            return
        for p in photos:
            date = p.date.astimezone().strftime("%Y-%m-%d %H:%M")
            biggest = max(p.sizes, key=lambda s: getattr(s, "w", 0) or 0, default=None)
            dims = f"{biggest.w}x{biggest.h}" if biggest and getattr(biggest, "w", 0) else ""
            print(f"{p.id:>20}  {date}  {dims}")


async def cmd_bot_info(args) -> None:
    async with run_with_client(args) as client:
        user = await resolve_chat(client, args.bot)
        res = await client(functions.users.GetFullUserRequest(id=user))
        info = getattr(res.full_user, "bot_info", None)
        if info is None:
            raise TgError(f"'{args.bot}' is not a bot (no bot info)")
        if args.json:
            print(json_pp(info.to_dict()))
            return
        desc = getattr(info, "description", "") or ""
        about = getattr(info, "about", "") or ""
        if about:
            print(about)
        if desc:
            print(desc)
        commands = getattr(info, "commands", []) or []
        if commands:
            print("\ncommands:")
            for c in commands:
                print(f"  /{c.command}  {c.description}")
        if not (about or desc or commands):
            print("(no public bot info)")


async def cmd_bot_commands(args) -> None:
    async with run_with_client(args) as client:
        me = await client.get_me()
        if not getattr(me, "bot", False):
            raise TgError(
                "only bot accounts can set their own commands",
                "log the bot in with: tg login --account <bot-label>, then pass --account",
            )
        if args.clear:
            commands: list = []
        else:
            p = args.pairs
            if len(p) % 2:
                raise TgError("commands come in <command> <description> pairs")
            commands = [
                types.BotCommand(command=p[i].lstrip("/"), description=p[i + 1])
                for i in range(0, len(p), 2)
            ]
        await client(
            functions.bots.SetBotCommandsRequest(
                scope=types.BotCommandScopeDefault(), lang_code="", commands=commands
            )
        )
        print(f"{'Cleared' if args.clear else 'Set'} {len(commands)} bot command(s)")


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser(
        "search-public", parents=parents, help="Search public chats/users by name"
    )
    sp.add_argument("query")
    sp.add_argument("-n", type=int, default=10)
    sp.set_defaults(func=cmd_search_public)

    sp = subparsers.add_parser(
        "resolve", parents=parents, help="Resolve a @username to an id without dialogs"
    )
    sp.add_argument("username")
    sp.set_defaults(func=cmd_resolve)

    sp = subparsers.add_parser("stickers", parents=parents, help="List your sticker sets")
    sp.set_defaults(func=cmd_stickers)

    sp = subparsers.add_parser("user-photos", parents=parents, help="List a user's profile photos")
    sp.add_argument("user")
    sp.add_argument("-n", type=int, default=10)
    sp.set_defaults(func=cmd_user_photos)

    sp = subparsers.add_parser(
        "bot-info", parents=parents, help="Show a bot's description and commands"
    )
    sp.add_argument("bot")
    sp.set_defaults(func=cmd_bot_info)

    sp = subparsers.add_parser(
        "bot-commands",
        parents=parents,
        help="Set your bot's commands (bot accounts only): /cmd desc [cmd desc...]",
    )
    sp.add_argument("pairs", nargs="*", default=[], metavar="CMD_DESC")
    sp.add_argument("--clear", action="store_true", help="remove all commands")
    sp.set_defaults(func=cmd_bot_commands)
