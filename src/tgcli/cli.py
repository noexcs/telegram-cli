"""tg — standalone Telegram command-line client (direct Telethon, no MCP)."""

import argparse
import asyncio
import sys

from telethon import errors

from . import __version__, auth, chats, media, messages, resolve
from .output import TgError


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--account", default=None, help="account label (v1: default only)")
    common.add_argument(
        "--json", action="store_true", help="print raw tool output without line formatting"
    )

    p = argparse.ArgumentParser(
        prog="tg",
        description="Standalone Telegram command-line client (direct Telethon connection, no MCP).",
        epilog='Tip: messages starting with "-" need "--", e.g. tg send me -- -hello',
    )
    p.add_argument("--version", action="version", version=f"tg {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # auth (no --account/--json needed, but harmless to keep consistent)
    sp = sub.add_parser("login", parents=[common], help="Log in (default: QR code)")
    sp.add_argument(
        "--qr", action="store_true", default=False, help="QR login (this is the default)"
    )
    sp.add_argument(
        "--phone",
        nargs="?",
        const="",
        default=None,
        help="phone login instead of QR; optionally pass the number",
    )
    sp.set_defaults(func=auth.cmd_login)
    sp2 = sub.add_parser("logout", parents=[common], help="Log out and remove the session")
    sp2.set_defaults(func=auth.cmd_logout)

    for mod in (messages, chats, media):
        mod.setup(sub, common)

    resolve.setup_alias(sub, common)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        asyncio.run(args.func(args))
        return 0
    except TgError as e:
        print(f"tg: {e}", file=sys.stderr)
        if e.hint:
            print(f"hint: {e.hint}", file=sys.stderr)
        return e.code
    except errors.AuthKeyDuplicatedError:
        print(
            "tg: session is in use by another connection (AuthKeyDuplicatedError)", file=sys.stderr
        )
        print(
            "hint: this CLI and the MCP daemon must use separate sessions; "
            "run `tg logout` then `tg login --qr` to get a fresh one",
            file=sys.stderr,
        )
        return 2
    except (errors.UnauthorizedError, errors.AuthKeyInvalidError):
        print("tg: session is no longer valid", file=sys.stderr)
        print("hint: log in again with: tg login --qr", file=sys.stderr)
        return 2
    except errors.SessionPasswordNeededError:
        print("tg: two-step verification password required", file=sys.stderr)
        return 2
    except errors.FloodWaitError as e:
        print(f"tg: rate-limited; Telegram asks to wait {e.seconds}s", file=sys.stderr)
        return 1
    except ValueError as e:
        # e.g. entity resolution failures ("Cannot find any entity ...")
        print(f"tg: {e}", file=sys.stderr)
        return 1
    except errors.RPCError as e:
        print(f"tg: Telegram API error: {e}", file=sys.stderr)
        return 1
    except (OSError, ConnectionError) as e:
        print(f"tg: cannot reach Telegram: {e}", file=sys.stderr)
        print(
            "hint: check that the proxy is up (e.g. Clash 127.0.0.1:7890) "
            "and TELEGRAM_PROXY_* in .env",
            file=sys.stderr,
        )
        return 2
    except (KeyboardInterrupt, BrokenPipeError):
        return 130


if __name__ == "__main__":
    sys.exit(main())
