"""Group administration: create, members, bans, admins, slow mode, topics, admin log."""

import random
import re
from datetime import datetime, timedelta, timezone

from telethon import functions, types

from .client import run_with_client
from .output import TgError, json_pp
from .resolve import resolve_chat

# rights granted by `promote`: full admin minus the dangerous ones
_PROMOTE_RIGHTS = dict(
    change_info=True,
    post_messages=True,
    edit_messages=True,
    delete_messages=True,
    ban_users=True,
    invite_users=True,
    pin_messages=True,
    manage_call=True,
    manage_topics=True,
    other=True,
)

# granular flags accepted by `admin-rights` (arg name == ChatAdminRights field)
_RIGHT_FLAGS = [
    "change_info",
    "post_messages",
    "edit_messages",
    "delete_messages",
    "ban_users",
    "invite_users",
    "pin_messages",
    "add_admins",
    "anonymous",
    "manage_call",
    "other",
    "manage_topics",
    "post_stories",
    "edit_stories",
    "delete_stories",
]


async def _peer(client, chat):
    return await client.get_input_entity(await resolve_chat(client, chat))


def _require_group(peer):
    """Return 'channel' (supergroup/channel) or 'basic', or raise for non-groups."""
    if isinstance(peer, types.InputPeerChannel):
        return "channel"
    if isinstance(peer, types.InputPeerChat):
        return "basic"
    raise TgError("this command only works for groups and channels")


def _users_by_id(res) -> dict:
    return {u.id: u for u in getattr(res, "users", []) or []}


def _display(users: dict, uid) -> str:
    u = users.get(uid)
    if u is None:
        return str(uid)
    name = " ".join(x for x in (u.first_name, u.last_name) if x)
    return name or getattr(u, "username", None) and f"@{u.username}" or str(uid)


def _action_text(action) -> str:
    name = type(action).__name__.removeprefix("AdminLogEventAction")
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower()


async def cmd_new_group(args) -> None:
    if not args.users:
        raise TgError("a group needs at least one member", "e.g. tg new-group Friends @alice")
    async with run_with_client(args) as client:
        res = await client(functions.messages.CreateChatRequest(users=args.users, title=args.title))
        upd = getattr(res, "updates", res)
        chat = next(iter(getattr(upd, "chats", []) or []), None)
        print(f"Group created: {args.title} (id: {getattr(chat, 'id', '?')})")


async def cmd_new_channel(args) -> None:
    async with run_with_client(args) as client:
        res = await client(
            functions.channels.CreateChannelRequest(
                title=args.title,
                about=args.about or "",
                broadcast=not args.group,
                megagroup=args.group,
            )
        )
        ch = next(iter(getattr(res, "chats", []) or []), None)
        kind = "supergroup" if args.group else "channel"
        if ch is not None and getattr(ch, "id", None):
            print(f"{kind.capitalize()} created: {args.title} (id: -100{ch.id})")
        else:
            print(f"{kind.capitalize()} created: {args.title}")


async def cmd_invite(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        kind = _require_group(peer)
        n = 0
        if kind == "channel":
            res = await client(functions.channels.InviteToChannelRequest(peer, args.users))
            missing = getattr(res, "missing_invitees", []) or []
            n = len(args.users) - len(missing)
            if missing:
                print(f"warning: {len(missing)} user(s) could not be invited (privacy settings)")
        else:
            for u in args.users:
                await client(
                    functions.messages.AddChatUserRequest(
                        chat_id=peer.chat_id, user_id=u, fwd_limit=0
                    )
                )
                n += 1
        print(f"Invited {n} user(s)")


async def cmd_kick(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        kind = _require_group(peer)
        for u in args.users:
            if kind == "channel":
                # no dedicated kick call: "remove" == view-messages ban, as official clients do
                await client(
                    functions.channels.EditBannedRequest(
                        peer,
                        u,
                        types.ChatBannedRights(until_date=None, view_messages=True),
                    )
                )
            else:
                await client(
                    functions.messages.DeleteChatUserRequest(chat_id=peer.chat_id, user_id=u)
                )
        print(f"Kicked {len(args.users)} user(s)")


async def cmd_leave(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        kind = _require_group(peer)
        if kind == "channel":
            await client(functions.channels.LeaveChannelRequest(peer))
        else:
            await client(
                functions.messages.DeleteChatUserRequest(
                    chat_id=peer.chat_id, user_id=types.InputUserSelf()
                )
            )
        print("Left the group")


async def _require_channel(peer):
    if _require_group(peer) != "channel":
        raise TgError(
            "this command is only supported in supergroups and channels",
            "basic groups have no ban list / slow mode / topics",
        )
    return peer


async def cmd_ban(args) -> None:
    until = None
    if args.days:
        until = datetime.now(timezone.utc) + timedelta(days=args.days)
    async with run_with_client(args) as client:
        peer = await _require_channel(await _peer(client, args.chat))
        await client(
            functions.channels.EditBannedRequest(
                peer,
                args.user,
                types.ChatBannedRights(until_date=until, view_messages=True),
            )
        )
        print(f"Banned {args.user}" + (f" for {args.days}d" if args.days else " permanently"))


async def cmd_unban(args) -> None:
    async with run_with_client(args) as client:
        peer = await _require_channel(await _peer(client, args.chat))
        await client(
            functions.channels.EditBannedRequest(
                peer, args.user, types.ChatBannedRights(until_date=None)
            )
        )
        print(f"Unbanned {args.user}")


async def cmd_banned(args) -> None:
    async with run_with_client(args) as client:
        peer = await _require_channel(await _peer(client, args.chat))
        res = await client(
            functions.channels.GetParticipantsRequest(
                # despite the name, Kicked (not Banned) is the filter that
                # actually returns banned users on the current TL layer
                peer,
                types.ChannelParticipantsKicked(q=""),
                offset=0,
                limit=100,
                hash=0,
            )
        )
        rows = [p for p in res.participants if isinstance(p, types.ChannelParticipantBanned)]
        users = _users_by_id(res)
        if args.json:
            print(json_pp([p.to_dict() for p in rows]))
            return
        if not rows:
            print("(no banned users)")
            return
        for p in rows:
            uid = p.peer.user_id
            until = getattr(p.banned_rights, "until_date", None)
            dur = f"until {until:%Y-%m-%d}" if until and until.year > 1971 else "permanent"
            print(f"{uid:>14}  {_display(users, uid)}  {dur}  by {p.kicked_by}")


async def cmd_admins(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        kind = _require_group(peer)
        if kind == "channel":
            res = await client(
                functions.channels.GetParticipantsRequest(
                    peer,
                    types.ChannelParticipantsAdmins(),
                    offset=0,
                    limit=50,
                    hash=0,
                )
            )
            rows = []
            for p in res.participants:
                if isinstance(p, types.ChannelParticipantCreator):
                    rows.append((p.user_id, p.rank or "creator"))
                else:
                    rows.append((p.user_id, getattr(p, "rank", "") or "admin"))
            users = _users_by_id(res)
        else:
            res = await client(functions.messages.GetFullChatRequest(chat_id=peer.chat_id))
            users = _users_by_id(res)
            rows = []
            for p in res.full_chat.participants.participants:
                if isinstance(p, types.ChatParticipantCreator):
                    rows.append((p.user_id, "creator"))
                elif isinstance(p, types.ChatParticipantAdmin):
                    rows.append((p.user_id, "admin"))
        if args.json:
            print(
                json_pp(
                    [{"id": uid, "rank": rank, "user": _display(users, uid)} for uid, rank in rows]
                )
            )
            return
        if not rows:
            print("(no admins)")
            return
        for uid, rank in rows:
            print(f"{uid:>14}  {rank:<8} {_display(users, uid)}")


async def cmd_promote(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        if _require_group(peer) == "channel":
            rank = args.title or "admin"
            await client(
                functions.channels.EditAdminRequest(
                    peer,
                    args.user,
                    types.ChatAdminRights(**_PROMOTE_RIGHTS),
                    rank=rank,
                )
            )
            print(f"Promoted {args.user} (rank: {rank})")
        else:
            if args.title:
                raise TgError("basic groups have no admin titles")
            await client(
                functions.messages.EditChatAdminRequest(
                    chat_id=peer.chat_id, user_id=args.user, is_admin=True
                )
            )
            print(f"Promoted {args.user}")


async def cmd_demote(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        if _require_group(peer) == "channel":
            await client(
                functions.channels.EditAdminRequest(
                    peer, args.user, types.ChatAdminRights(), rank=""
                )
            )
        else:
            await client(
                functions.messages.EditChatAdminRequest(
                    chat_id=peer.chat_id, user_id=args.user, is_admin=False
                )
            )
        print(f"Demoted {args.user}")


async def cmd_admin_rights(args) -> None:
    granted = {f: True for f in _RIGHT_FLAGS if getattr(args, f, False)}
    if not granted and not args.rank:
        raise TgError(
            "no rights requested",
            "pass flags like --pin-messages --delete-messages,"
            " or use `tg promote` for the standard set",
        )
    async with run_with_client(args) as client:
        peer = await _require_channel(await _peer(client, args.chat))
        await client(
            functions.channels.EditAdminRequest(
                peer, args.user, types.ChatAdminRights(**granted), rank=args.rank or ""
            )
        )
        names = ", ".join(granted) or "(none)"
        print(
            f"Rights set for {args.user}: {names}" + (f" (rank: {args.rank})" if args.rank else "")
        )


async def cmd_slow_mode(args) -> None:
    seconds = args.seconds or 0
    async with run_with_client(args) as client:
        peer = await _require_channel(await _peer(client, args.chat))
        await client(functions.channels.ToggleSlowModeRequest(peer, seconds))
        print(f"Slow mode {'disabled' if seconds == 0 else f'set to {seconds}s'}")


async def _forum_check(client, peer):
    ent = await client.get_entity(peer)
    if not getattr(ent, "forum", False):
        raise TgError("this group has forum mode disabled", "topics only exist in forum groups")
    return ent


async def cmd_topics(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        await _require_channel(peer)
        await _forum_check(client, peer)
        res = await client(
            functions.messages.GetForumTopicsRequest(
                peer=peer,
                offset_date=None,
                offset_id=0,
                offset_topic=0,
                limit=args.n,
            )
        )
        topics = getattr(res, "topics", []) or []
        if args.json:
            print(json_pp([t.to_dict() for t in topics]))
            return
        if not topics:
            print("(no topics)")
            return
        for t in topics:
            unread = f"  ({t.unread_count} unread)" if t.unread_count else ""
            print(f"[{t.id}] {t.title}{unread}")


async def cmd_topic_create(args) -> None:
    async with run_with_client(args) as client:
        peer = await _peer(client, args.chat)
        await _require_channel(peer)
        await _forum_check(client, peer)
        res = await client(
            functions.messages.CreateForumTopicRequest(
                peer=peer, title=args.title, random_id=random.randint(1, 2**31)
            )
        )
        topic_id = None
        for u in getattr(res, "updates", []) or []:
            msg = getattr(u, "message", None)
            if msg is not None:
                topic_id = msg.id
                break
        if topic_id is None:  # fallback: find the fresh topic by title
            lst = await client(
                functions.messages.GetForumTopicsRequest(
                    peer=peer, offset_date=None, offset_id=0, offset_topic=0, limit=20
                )
            )
            topic_id = next((t.id for t in lst.topics if t.title == args.title), None)
        if args.text and topic_id is not None:
            await client.send_message(peer, " ".join(args.text), reply_to=topic_id)
        print(f"Topic created: [{topic_id}] {args.title}")


async def cmd_admin_log(args) -> None:
    async with run_with_client(args) as client:
        peer = await _require_channel(await _peer(client, args.chat))
        res = await client(
            functions.channels.GetAdminLogRequest(
                peer,
                q="",
                max_id=0,
                min_id=0,
                limit=args.n,
            )
        )
        events = getattr(res, "events", []) or []
        users = _users_by_id(res)
        if args.json:
            print(json_pp([e.to_dict() for e in events]))
            return
        if not events:
            print("(no admin actions recorded)")
            return
        for e in events:
            date = e.date.astimezone().strftime("%Y-%m-%d %H:%M")
            print(f"[{e.id}] {date}  {_display(users, e.user_id)}: {_action_text(e.action)}")


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser(
        "new-group", parents=parents, help="Create a basic group, e.g. tg new-group Friends @alice"
    )
    sp.add_argument("title")
    sp.add_argument("users", nargs="+")
    sp.set_defaults(func=cmd_new_group)

    sp = subparsers.add_parser(
        "new-channel", parents=parents, help="Create a channel (--group for a supergroup)"
    )
    sp.add_argument("title")
    sp.add_argument("--about", default="")
    sp.add_argument("--group", action="store_true", help="create a supergroup instead")
    sp.set_defaults(func=cmd_new_channel)

    sp = subparsers.add_parser("invite", parents=parents, help="Invite users to a group")
    sp.add_argument("chat")
    sp.add_argument("users", nargs="+")
    sp.set_defaults(func=cmd_invite)

    sp = subparsers.add_parser("kick", parents=parents, help="Remove users from a group")
    sp.add_argument("chat")
    sp.add_argument("users", nargs="+")
    sp.set_defaults(func=cmd_kick)

    sp = subparsers.add_parser("leave", parents=parents, help="Leave a group/channel")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_leave)

    sp = subparsers.add_parser(
        "ban", parents=parents, help="Ban a user (permanent unless [days] given); supergroups only"
    )
    sp.add_argument("chat")
    sp.add_argument("user")
    sp.add_argument("days", nargs="?", type=int, default=None)
    sp.set_defaults(func=cmd_ban)

    sp = subparsers.add_parser("unban", parents=parents, help="Unban a user; supergroups only")
    sp.add_argument("chat")
    sp.add_argument("user")
    sp.set_defaults(func=cmd_unban)

    sp = subparsers.add_parser(
        "banned", parents=parents, help="List banned users; supergroups only"
    )
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_banned)

    sp = subparsers.add_parser("admins", parents=parents, help="List admins (and their ranks)")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_admins)

    sp = subparsers.add_parser(
        "promote", parents=parents, help="Promote to admin with the standard right set"
    )
    sp.add_argument("chat")
    sp.add_argument("user")
    sp.add_argument("--title", default=None, help="admin rank/title")
    sp.set_defaults(func=cmd_promote)

    sp = subparsers.add_parser("demote", parents=parents, help="Remove admin rights")
    sp.add_argument("chat")
    sp.add_argument("user")
    sp.set_defaults(func=cmd_demote)

    sp = subparsers.add_parser(
        "admin-rights", parents=parents, help="Set exact admin rights (supergroups only)"
    )
    sp.add_argument("chat")
    sp.add_argument("user")
    for f in _RIGHT_FLAGS:
        sp.add_argument(f"--{f.replace('_', '-')}", action="store_true", dest=f)
    sp.add_argument("--rank", default="", help="admin rank/title")
    sp.set_defaults(func=cmd_admin_rights)

    sp = subparsers.add_parser(
        "slow-mode", parents=parents, help="Set slow mode seconds (0 = disable); supergroups only"
    )
    sp.add_argument("chat")
    sp.add_argument("seconds", nargs="?", type=int, default=0)
    sp.set_defaults(func=cmd_slow_mode)

    sp = subparsers.add_parser("topics", parents=parents, help="List forum topics")
    sp.add_argument("chat")
    sp.add_argument("-n", type=int, default=20)
    sp.set_defaults(func=cmd_topics)

    sp = subparsers.add_parser(
        "topic-create",
        parents=parents,
        help="Create a forum topic, optionally with a first message",
    )
    sp.add_argument("chat")
    sp.add_argument("title")
    sp.add_argument("text", nargs="*", default=[])
    sp.set_defaults(func=cmd_topic_create)

    sp = subparsers.add_parser(
        "admin-log", parents=parents, help="Recent admin actions; supergroups only"
    )
    sp.add_argument("chat")
    sp.add_argument("-n", type=int, default=20)
    sp.set_defaults(func=cmd_admin_log)
