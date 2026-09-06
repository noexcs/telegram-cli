"""Messaging commands: send, reply, edit, del, fwd, poll, schedule, draft,
reactions, pinning, read state, message links, contact cards, buttons."""

import contextlib
import random
import re
from datetime import datetime, timedelta

from telethon import functions, types

from .client import run_with_client
from .output import TgError, fmt_date, json_pp
from .resolve import resolve_chat

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_when(spec: str) -> datetime:
    """Parse a schedule time: relative (+30m/+2h/+1d), unix ts, or ISO date."""
    s = spec.strip()
    m = re.fullmatch(r"\+(\d+)([smhd])", s.lower())
    if m:
        return datetime.now().astimezone() + timedelta(
            seconds=int(m.group(1)) * _UNIT_SECONDS[m.group(2)]
        )
    if re.fullmatch(r"\d{9,12}", s):
        return datetime.fromtimestamp(int(s)).astimezone()
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        pass
    else:
        return dt.astimezone() if dt.tzinfo is None else dt
    raise TgError(
        f"cannot parse time: {spec!r}",
        'use "+30m" / "+2h", "2026-09-07 14:30", or a unix timestamp',
    )


async def cmd_send(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.send_message(entity, " ".join(args.text), parse_mode=args.parse_mode)
        print(f"Message sent (id: {msg.id})")


async def cmd_reply(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.send_message(entity, " ".join(args.text), reply_to=args.msg_id)
        print(f"Reply sent (id: {msg.id})")


async def cmd_edit(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.edit_message(entity, args.msg_id, args.new_text)
        print("Message edited")


async def cmd_del(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.delete_messages(entity, args.ids, revoke=True)
        print(f"Deleted {len(args.ids)} message(s)")


async def cmd_fwd(args) -> None:
    async with run_with_client(args) as client:
        from_entity = await resolve_chat(client, args.from_chat)
        to_entity = await resolve_chat(client, args.to)
        sent = await client.forward_messages(to_entity, args.msg_ids, from_peer=from_entity)
        print(f"Forwarded {len(sent)} message(s)")


async def cmd_poll(args) -> None:
    if len(args.options) < 2:
        raise TgError("a poll needs at least 2 options")
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        answers = [
            types.PollAnswer(
                text=types.TextWithEntities(text=a, entities=[]),
                option=bytes([i]),
            )
            for i, a in enumerate(args.options)
        ]
        poll = types.Poll(
            id=random.randint(1, 2**31),
            question=types.TextWithEntities(text=args.question, entities=[]),
            answers=answers,
            hash=0,
            closed=False,
            public_voters=args.public,
            quiz=args.quiz,
            multiple_choice=args.multiple,
        )
        msg = await client.send_message(entity, file=types.InputMediaPoll(poll=poll))
        print(f"Poll sent (id: {msg.id})")


async def cmd_schedule(args) -> None:
    when = parse_when(args.time)
    if when <= datetime.now().astimezone():
        raise TgError("schedule time must be in the future")
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.send_message(entity, " ".join(args.text), schedule=when)
        print(f"Scheduled (id: {msg.id}) for {fmt_date(when)}")


async def cmd_scheduled(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        res = await client(functions.messages.GetScheduledHistoryRequest(peer=entity, hash=0))
        msgs = getattr(res, "messages", []) or []
        if not msgs:
            print("(no scheduled messages)")
            return
        if args.json:
            print(json_pp([m.to_dict() for m in msgs]))
            return
        for m in msgs:
            body = " ".join((m.message or "").split())[:100] or "[media]"
            print(f"[{m.id}] {fmt_date(m.date)}  {body}")


async def cmd_unschedule(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client(functions.messages.DeleteScheduledMessagesRequest(peer=entity, id=args.ids))
        print(f"Unscheduled {len(args.ids)} message(s)")


async def cmd_draft(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        if args.text:
            text = " ".join(args.text)
            await client(functions.messages.SaveDraftRequest(peer=entity, message=text))
            print("Draft saved")
            return
        text = ""
        async for d in client.iter_drafts(entity):
            text = d.raw_text or ""
            break
        print(text if text else "(no draft)")


async def cmd_draft_clear(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        # an empty message clears the draft
        await client(functions.messages.SaveDraftRequest(peer=entity, message=""))
        print("Draft cleared")


async def cmd_react(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client(
            functions.messages.SendReactionRequest(
                peer=entity,
                msg_id=args.msg_id,
                big=args.big,
                reaction=[types.ReactionEmoji(emoticon=args.emoji)],
            )
        )
        print(f"Reacted {args.emoji} to message {args.msg_id}")


async def cmd_unreact(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        # an empty reaction list removes our reaction
        await client(
            functions.messages.SendReactionRequest(peer=entity, msg_id=args.msg_id, reaction=[])
        )
        print(f"Reaction removed from message {args.msg_id}")


async def cmd_pin(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.pin_message(entity, args.msg_id)
        print(f"Pinned message {args.msg_id}")


async def cmd_unpin(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        if args.msg_id is None:
            await client.unpin_message(entity)
            print("Unpinned all messages")
        else:
            await client.unpin_message(entity, args.msg_id)
            print(f"Unpinned message {args.msg_id}")


async def cmd_read(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.send_read_acknowledge(entity, clear_mentions=True)
        print("Marked as read")


async def cmd_msg_link(args) -> None:
    async with run_with_client(args) as client:
        peer = await client.get_input_entity(await resolve_chat(client, args.chat))
        if not isinstance(peer, types.InputPeerChannel):
            raise TgError(
                "message links only exist for channels and supergroups",
                "basic groups and private chats have no t.me message links",
            )
        res = await client(
            functions.channels.ExportMessageLinkRequest(
                channel=types.InputChannel(
                    channel_id=peer.channel_id, access_hash=peer.access_hash
                ),
                id=args.msg_id,
            )
        )
        print(res.link)


async def cmd_contact_card(args) -> None:
    first, _, last = args.name.partition(" ")
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.send_message(
            entity,
            file=types.InputMediaContact(
                phone_number=args.phone, first_name=first, last_name=last, vcard=""
            ),
        )
        print(f"Contact card sent (id: {msg.id})")


def _reaction_text(reaction) -> str:
    if isinstance(reaction, types.ReactionEmoji):
        return reaction.emoticon
    if isinstance(reaction, types.ReactionCustomEmoji):
        return f"custom-emoji:{reaction.document_id}"
    return str(reaction)


async def cmd_buttons(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.get_messages(entity, ids=args.msg_id)
        rows = getattr(msg, "buttons", None)
        if not rows:
            raise TgError(f"message {args.msg_id} has no inline buttons")
        idx = 0
        for row in rows:
            cells = []
            for b in row:
                kind = "url" if getattr(b, "url", None) else "callback"
                cells.append(f"[{idx}] {b.text} ({kind})")
                idx += 1
            print("  ".join(cells))
        print(f"\npress one with: tg press {args.chat} {args.msg_id} <index|text>")


async def cmd_press(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.get_messages(entity, ids=args.msg_id)
        if not getattr(msg, "buttons", None):
            raise TgError(f"message {args.msg_id} has no inline buttons")
        spec = args.button
        if spec.lstrip("-").isdigit():
            res = await msg.click(int(spec))
        else:
            res = await msg.click(text=spec)
        answer = getattr(res, "message", None) if res is not None else None
        alert = bool(getattr(res, "alert", None)) if res is not None else False
        out = f"Pressed button {spec!r}"
        if answer:
            out += f" — bot answered: {answer!r}" + (" (alert)" if alert else "")
        print(out)


async def cmd_reactions(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.get_messages(entity, ids=args.msg_id)
        r = getattr(msg, "reactions", None)
        # after removing your own reaction the server still returns an
        # (empty) MessageReactions object instead of None
        if r is None or not getattr(r, "results", None):
            print("(no reactions)")
            return
        if args.json:
            print(json_pp(r.to_dict()))
            return
        for rc in r.results:
            chosen = " *" if rc.chosen_order is not None else ""
            print(f"{_reaction_text(rc.reaction)}  x{rc.count}{chosen}")
        recent = getattr(r, "recent_reactions", None) or []
        if recent:
            print("\nrecent:")
            for rr in recent:
                pid = getattr(rr.peer_id, "user_id", None) or rr.peer_id
                who = str(pid)
                with contextlib.suppress(Exception):
                    ent = await client.get_entity(rr.peer_id)
                    who = (
                        " ".join(x for x in (ent.first_name, getattr(ent, "last_name", None)) if x)
                        or f"@{ent.username}"
                    )
                print(f"  {_reaction_text(rr.reaction)}  {who}")


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser(
        "send", parents=parents, help="Send a message, e.g. tg send me hello"
    )
    sp.add_argument("chat")
    sp.add_argument("text", nargs="+")
    sp.add_argument("-p", "--parse-mode", default=None, choices=["md", "markdown", "html"])
    sp.set_defaults(func=cmd_send)

    sp = subparsers.add_parser(
        "reply", parents=parents, help="Reply to a message, e.g. tg reply me 12 got it"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.add_argument("text", nargs="+")
    sp.set_defaults(func=cmd_reply)

    sp = subparsers.add_parser("edit", parents=parents, help="Edit your own message")
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.add_argument("new_text")
    sp.set_defaults(func=cmd_edit)

    sp = subparsers.add_parser(
        "del", parents=parents, help="Delete messages (revoke for both sides)"
    )
    sp.add_argument("chat")
    sp.add_argument("ids", nargs="+", type=int)
    sp.set_defaults(func=cmd_del)

    sp = subparsers.add_parser(
        "fwd", parents=parents, help="Forward messages, e.g. tg fwd SRC 1 2 3 DST (last is target)"
    )
    sp.add_argument("from_chat")
    sp.add_argument("msg_ids", nargs="+", type=int)
    sp.add_argument("to")
    sp.set_defaults(func=cmd_fwd)

    sp = subparsers.add_parser(
        "poll", parents=parents, help='Create a poll, e.g. tg poll me "Q?" a b c'
    )
    sp.add_argument("chat")
    sp.add_argument("question")
    sp.add_argument("options", nargs="+")
    sp.add_argument("--multiple", action="store_true", help="allow multiple answers")
    sp.add_argument("--quiz", action="store_true", help="quiz mode")
    sp.add_argument("--public", action="store_true", help="public votes")
    sp.set_defaults(func=cmd_poll)

    sp = subparsers.add_parser(
        "schedule",
        parents=parents,
        help='Schedule a message, e.g. tg schedule me "+2h" ping',
    )
    sp.add_argument("chat")
    sp.add_argument("time", help='+30m / +2h / +1d, "2026-09-07 14:30", or a unix timestamp')
    sp.add_argument("text", nargs="+")
    sp.set_defaults(func=cmd_schedule)

    sp = subparsers.add_parser("scheduled", parents=parents, help="List scheduled messages")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_scheduled)

    sp = subparsers.add_parser(
        "unschedule", parents=parents, help="Delete scheduled messages (ids from `scheduled`)"
    )
    sp.add_argument("chat")
    sp.add_argument("ids", nargs="+", type=int)
    sp.set_defaults(func=cmd_unschedule)

    sp = subparsers.add_parser(
        "draft",
        parents=parents,
        help="Save a draft (with text) or show the current draft (without)",
    )
    sp.add_argument("chat")
    sp.add_argument("text", nargs="*", default=[])
    sp.set_defaults(func=cmd_draft)

    sp = subparsers.add_parser("draft-clear", parents=parents, help="Clear the draft")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_draft_clear)

    sp = subparsers.add_parser("react", parents=parents, help="React to a message")
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.add_argument("emoji", help='e.g. "👍", "❤️", "🎉"')
    sp.add_argument("--big", action="store_true", help="big animation")
    sp.set_defaults(func=cmd_react)

    sp = subparsers.add_parser("unreact", parents=parents, help="Remove your reaction")
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.set_defaults(func=cmd_unreact)

    sp = subparsers.add_parser("pin", parents=parents, help="Pin a message")
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.set_defaults(func=cmd_pin)

    sp = subparsers.add_parser(
        "unpin", parents=parents, help="Unpin a message (or all if no id given)"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", nargs="?", type=int, default=None)
    sp.set_defaults(func=cmd_unpin)

    sp = subparsers.add_parser("read", parents=parents, help="Mark the chat as read")
    sp.add_argument("chat")
    sp.set_defaults(func=cmd_read)

    sp = subparsers.add_parser(
        "msg-link", parents=parents, help="Export a t.me link (channels/supergroups)"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.set_defaults(func=cmd_msg_link)

    sp = subparsers.add_parser(
        "contact-card",
        parents=parents,
        help='Send a contact card, e.g. tg contact-card me "Jo Do" +8613800000000',
    )
    sp.add_argument("chat")
    sp.add_argument("name", help='contact name, e.g. "John Doe"')
    sp.add_argument("phone")
    sp.set_defaults(func=cmd_contact_card)

    sp = subparsers.add_parser(
        "buttons", parents=parents, help="List a message's inline buttons (with press indexes)"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.set_defaults(func=cmd_buttons)

    sp = subparsers.add_parser(
        "press", parents=parents, help="Press an inline button by index (from `buttons`) or text"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.add_argument("button", help="button index (0-based, from `buttons`) or its text")
    sp.set_defaults(func=cmd_press)

    sp = subparsers.add_parser("reactions", parents=parents, help="Show reactions on a message")
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.set_defaults(func=cmd_reactions)
