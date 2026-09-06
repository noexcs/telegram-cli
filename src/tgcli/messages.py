"""Messaging commands: send, reply, edit, del, fwd, poll."""

import random

from telethon import types

from .client import run_with_client
from .output import TgError
from .resolve import resolve_chat


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
