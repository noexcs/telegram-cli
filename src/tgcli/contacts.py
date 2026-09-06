"""Contact management: add, delete, bulk import/export."""

import csv
import json
from pathlib import Path

from telethon import functions, types

from .client import run_with_client
from .output import TgError, json_pp
from .resolve import resolve_chat

_FIELDS = ("phone", "first_name", "last_name")


def _row_from(entry: dict) -> dict:
    row = {}
    for key in _FIELDS:
        for alias in (key, key.replace("_", ""), {"phone": "tel"}.get(key, key)):
            if alias in entry and str(entry[alias]).strip():
                row[key] = str(entry[alias]).strip()
                break
        else:
            row[key] = ""
    if not row["first_name"]:
        raise TgError(f"contact entry needs at least a first_name: {entry}")
    return row


def _load_contacts_file(path: str) -> list[dict]:
    p = Path(path).expanduser()
    if not p.exists():
        raise TgError(f"file not found: {p}")
    rows: list[dict] = []
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8-sig") as fh:
            for i, raw in enumerate(csv.DictReader(fh), start=2):
                entry = {k.strip().lower(): v for k, v in raw.items() if k}
                try:
                    rows.append(_row_from(entry))
                except TgError as e:
                    raise TgError(f"{p.name} line {i}: {e}") from None
    else:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise TgError(
                f"{p} is not valid JSON: {e}", "expected a list of contact objects"
            ) from None
        if not isinstance(data, list):
            raise TgError(f"{p} must contain a JSON list of contact objects")
        for i, entry in enumerate(data, start=1):
            if not isinstance(entry, dict):
                raise TgError(f"{p} entry {i} is not an object")
            rows.append(_row_from(entry))
    if not rows:
        raise TgError(f"no contacts found in {p}")
    return rows


async def cmd_contact_add(args) -> None:
    first, _, last = args.name.partition(" ")
    async with run_with_client(args) as client:
        entity = await resolve_chat(client, args.user)
        res = await client(
            functions.contacts.AddContactRequest(
                id=entity,
                first_name=first,
                last_name=last,
                phone=args.phone or "",
            )
        )
        status = getattr(res, "status", None)
        print(f"Contact added: {args.name!r} ({args.user})" + (f" [{status}]" if status else ""))


async def _resolve_contact_refs(client, users: list[str]) -> list:
    """Resolve users by name/@username/id, or by phone when prefixed with +."""
    res = await client(functions.contacts.GetContactsRequest(hash=0))
    by_phone = {}
    for u in getattr(res, "users", []) or []:
        phone = getattr(u, "phone", None)
        if phone:
            by_phone["+" + phone.lstrip("+")] = u
    refs = []
    for spec in users:
        if spec.startswith("+"):
            u = by_phone.get(spec)
            if u is None:
                raise TgError(f"no contact with phone {spec}")
            refs.append(u)
        else:
            refs.append(await resolve_chat(client, spec))
    return refs


async def cmd_contact_del(args) -> None:
    async with run_with_client(args) as client:
        refs = await _resolve_contact_refs(client, args.users)
        await client(functions.contacts.DeleteContactsRequest(id=refs))
        print(f"Deleted {len(refs)} contact(s)")


async def cmd_contact_import(args) -> None:
    rows = _load_contacts_file(args.file)
    contacts = [
        types.InputPhoneContact(
            client_id=i,
            phone=r["phone"] or "+10000000000",
            first_name=r["first_name"],
            last_name=r["last_name"],
        )
        for i, r in enumerate(rows)
    ]
    async with run_with_client(args) as client:
        res = await client(functions.contacts.ImportContactsRequest(contacts=contacts))
        imported = len(getattr(res, "imported", []) or [])
        retry = len(getattr(res, "retry_contacts", []) or [])
        print(
            f"Imported {imported} new contact(s) from {args.file}"
            + (f"; {retry} could not be matched" if retry else "")
        )
        if args.json:
            print(json_pp([u.to_dict() for u in getattr(res, "users", []) or []]))


async def cmd_contact_export(args) -> None:
    async with run_with_client(args) as client:
        res = await client(functions.contacts.GetContactsRequest(hash=0))
        out = []
        for u in getattr(res, "users", []) or []:
            if not getattr(u, "contact", False):
                continue  # GetContacts may return non-contact users; keep true contacts
            out.append(
                {
                    "id": u.id,
                    "phone": f"+{u.phone}" if getattr(u, "phone", None) else "",
                    "first_name": u.first_name or "",
                    "last_name": u.last_name or "",
                    "username": getattr(u, "username", None) or "",
                }
            )
        payload = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
        if args.file:
            path = Path(args.file).expanduser()
            path.write_text(payload, encoding="utf-8")
            print(f"Exported {len(out)} contact(s) to {path}")
        else:
            print(payload, end="")


def setup(subparsers, common=None) -> None:
    parents = [common] if common else []
    sp = subparsers.add_parser("contact", parents=parents, help="Manage contacts")
    sub = sp.add_subparsers(dest="contact_cmd", required=True)

    s1 = sub.add_parser("add", help="contact add USER [NAME] [--phone +86...]")
    s1.add_argument("user")
    s1.add_argument("name", nargs="?", default=None, help='display name, e.g. "John Doe"')
    s1.add_argument("--phone", default="")
    s1.set_defaults(func=cmd_contact_add)

    s2 = sub.add_parser("del", help="contact del USER...")
    s2.add_argument("users", nargs="+")
    s2.set_defaults(func=cmd_contact_del)

    s3 = sub.add_parser("import", help="contact import FILE (.json or .csv)")
    s3.add_argument("file")
    s3.set_defaults(func=cmd_contact_import)

    s4 = sub.add_parser("export", help="contact export [FILE] (JSON, re-importable)")
    s4.add_argument("file", nargs="?", default=None)
    s4.set_defaults(func=cmd_contact_export)
