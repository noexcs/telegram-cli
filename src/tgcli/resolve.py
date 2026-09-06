"""Chat resolution: aliases, 'me', @username / numeric id, fuzzy dialog match."""

import json
import re
from pathlib import Path

from .output import TgError

_ALIAS_FILE = Path.home() / ".config" / "tg" / "aliases.json"


def _load_aliases() -> dict:
    try:
        return json.loads(_ALIAS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_aliases(aliases: dict) -> None:
    _ALIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ALIAS_FILE.write_text(
        json.dumps(aliases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


async def resolve_chat(client, spec: str):
    """Resolve a chat reference to an entity accepted by telethon.

    Order: alias file → me/saved → numeric id → @username / fuzzy dialog match.
    Dialog matches return the input entity (carries access_hash — a fresh
    session cannot resolve bare user ids it has never seen).
    """
    s = str(spec).strip()
    aliases = _load_aliases()
    while s in aliases and aliases[s] != s:
        s = aliases[s]  # follow alias chains
    if s.lower() in ("me", "saved"):
        return "me"
    dialogs = await client.get_dialogs(limit=200)
    if re.fullmatch(r"-?\d+", s):
        want = int(s)
        for d in dialogs:
            if d.id == want:
                return d.input_entity  # has access_hash
        return want  # not in dialogs; let telethon try (e.g. public channels)
    if s.startswith("@"):
        s = s[1:]
    hits = [d for d in dialogs if s.lower() in (d.name or "").lower()]
    if not hits:
        # look at usernames too
        hits = [
            d
            for d in dialogs
            if d.entity is not None
            and getattr(d.entity, "username", None)
            and s.lower() in d.entity.username.lower()
        ]
    if not hits:
        return s  # let telethon resolve the bare username itself
    exact = [d for d in hits if (d.name or "").lower() == s.lower()]
    if len(exact) == 1:
        return exact[0].input_entity
    if len(hits) > 1:
        ids = ", ".join(str(d.id) for d in hits[:5])
        raise TgError(
            f"'{spec}' matches multiple chats [{ids}]; use a more precise name or numeric id"
        )
    return hits[0].input_entity


# ---- alias subcommands (stretch) ----


async def cmd_alias_set(args) -> None:
    aliases = _load_aliases()
    aliases[args.name] = args.target
    _save_aliases(aliases)
    print(f"alias {args.name} → {args.target}")


async def cmd_alias_list(args) -> None:
    aliases = _load_aliases()
    if not aliases:
        print("(no aliases)")
        return
    for name, target in sorted(aliases.items()):
        print(f"{name}\t→ {target}")


async def cmd_alias_rm(args) -> None:
    aliases = _load_aliases()
    if args.name not in aliases:
        raise TgError(f"alias '{args.name}' does not exist")
    del aliases[args.name]
    _save_aliases(aliases)
    print(f"alias {args.name} removed")


def setup_alias(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser(
        "alias", parents=parents, help="Manage chat aliases (local shortcuts)"
    )
    sub = sp.add_subparsers(dest="alias_cmd", required=True)
    s1 = sub.add_parser("set", help="alias set NAME TARGET")
    s1.add_argument("name")
    s1.add_argument("target")
    s1.set_defaults(func=cmd_alias_set)
    s2 = sub.add_parser("list", help="list aliases")
    s2.set_defaults(func=cmd_alias_list)
    s3 = sub.add_parser("rm", help="alias rm NAME")
    s3.add_argument("name")
    s3.set_defaults(func=cmd_alias_rm)
