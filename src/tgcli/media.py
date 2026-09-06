"""Media commands: dl (download), sf (send file/album), voice, sticker, gif, vtr."""

import asyncio
import os
import re

from telethon import functions, types

from .client import run_with_client
from .output import TgError
from .resolve import resolve_chat


async def cmd_dl(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msgs = await client.get_messages(entity, ids=args.msg_id)
        if not isinstance(msgs, list):  # single id returns a bare Message
            msgs = [msgs]
        msg = msgs[0] if msgs else None
        if msg is None or not msg.media:
            raise TgError(
                f"message {args.msg_id} has no media",
                hint=f"check with: tg hist {args.chat} 5",
            )
        if args.out:
            out = os.path.expanduser(args.out)
        else:
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(args.chat))
            out = os.path.expanduser(f"~/Downloads/telegram_{safe}_{args.msg_id}")
        # append the real extension when the caller did not give one
        ext = getattr(getattr(msg, "file", None), "ext", None)
        if ext and not os.path.splitext(out)[1]:
            out += ext
        try:
            path = await client.download_media(msg, file=out)
        except OSError as e:
            raise TgError(
                f"cannot write to {out}: {e}",
                "macOS: grant the terminal app access to this folder "
                "(System Settings → Privacy & Security → Files and Folders), "
                "or pass -o with a different path",
                code=2,
            ) from None
        if not path:
            raise TgError("download failed (no data returned)")
        print(f"Media downloaded to {path}")


async def cmd_sf(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        files = [os.path.expanduser(f) for f in args.files]
        # single file must be a string; a list of 2-10 becomes an album
        payload = files[0] if len(files) == 1 else files
        sent = await client.send_file(entity, payload, caption=args.caption)
        count = len(sent) if isinstance(sent, list) else 1
        print(f"Sent {count} file(s)")


async def cmd_voice(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.send_file(entity, os.path.expanduser(args.file), voice_note=True)
        print("Voice note sent")


async def cmd_sticker(args) -> None:
    path = os.path.expanduser(args.file)
    if not os.path.exists(path):
        raise TgError(f"file not found: {path}")
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        await client.send_file(entity, path, force_document=False)
        print("Sticker sent")


async def cmd_gif(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        # GIF search = inline query to the built-in @gif bot (searchGifs was
        # removed from the TL layer; this is what official clients use)
        res = await client(
            functions.messages.GetInlineBotResultsRequest(
                bot="gif", peer=entity, query=args.query, offset=""
            )
        )
        docs = [r.document for r in res.results if getattr(r, "document", None) is not None]
        if not docs:
            raise TgError(f"no GIFs found for {args.query!r}")
        idx = min(max(args.index, 1), len(docs)) - 1
        await client.send_file(entity, docs[idx])
        print(f"GIF sent (match {idx + 1} of {len(docs)} for {args.query!r})")


async def cmd_vtr(args) -> None:
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.chat)
        msg = await client.get_messages(entity, ids=args.msg_id)
        doc = getattr(getattr(msg, "media", None), "document", None)
        is_voice = any(
            isinstance(a, types.DocumentAttributeAudio) and a.voice
            for a in getattr(doc, "attributes", [])
        )
        if not is_voice:
            raise TgError(
                f"message {args.msg_id} has no voice note",
                hint=f"check with: tg hist {args.chat} 5",
            )
        text, pending = "", True
        for _ in range(10):
            res = await client(
                functions.messages.TranscribeAudioRequest(peer=entity, msg_id=args.msg_id)
            )
            text, pending = res.text or "", bool(res.pending)
            if not pending:
                break
            await asyncio.sleep(1.5)
        if pending:
            raise TgError("transcription is still processing; try again in a moment")
        if not text:
            raise TgError("no transcription returned (Telegram Premium required for this feature)")
        print(text)


async def cmd_upload(args) -> None:
    path = os.path.expanduser(args.file)
    if not os.path.exists(path):
        raise TgError(f"file not found: {path}")
    async with run_with_client(args) as client:
        handle = await client.upload_file(path)
        md5 = getattr(handle, "md5", None)
        print(f"Uploaded {path}")
        print(f"  id={handle.id}  parts={handle.parts}  name={handle.name}")
        if md5:
            print(f"  md5={md5.hex()}")


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser(
        "dl", parents=parents, help="Download media, e.g. tg dl 7381828427 785"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.add_argument(
        "-o",
        "--out",
        default=None,
        help="output path (default ~/Downloads/telegram_<chat>_<msgid>)",
    )
    sp.set_defaults(func=cmd_dl)

    sp = subparsers.add_parser(
        "sf", parents=parents, help="Send files (2-10 files become an album)"
    )
    sp.add_argument("chat")
    sp.add_argument("files", nargs="+")
    sp.add_argument("-c", "--caption", default=None)
    sp.set_defaults(func=cmd_sf)

    sp = subparsers.add_parser("voice", parents=parents, help="Send a voice note")
    sp.add_argument("chat")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_voice)

    sp = subparsers.add_parser(
        "sticker", parents=parents, help="Send a sticker file (.webp / .tgs / .webm)"
    )
    sp.add_argument("chat")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_sticker)

    sp = subparsers.add_parser("gif", parents=parents, help="Search GIFs and send the first match")
    sp.add_argument("chat")
    sp.add_argument("query")
    sp.add_argument("-n", "--index", type=int, default=1, help="send the Nth match (default 1)")
    sp.set_defaults(func=cmd_gif)

    sp = subparsers.add_parser(
        "vtr", parents=parents, help="Transcribe a voice note (Telegram Premium)"
    )
    sp.add_argument("chat")
    sp.add_argument("msg_id", type=int)
    sp.set_defaults(func=cmd_vtr)

    sp = subparsers.add_parser(
        "upload", parents=parents, help="Upload a file to Telegram without sending it"
    )
    sp.add_argument("file")
    sp.set_defaults(func=cmd_upload)
