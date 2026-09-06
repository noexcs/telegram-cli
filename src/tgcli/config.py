"""Configuration: .env precedence, proxy tuple, session persistence."""

import os
from pathlib import Path

from dotenv import load_dotenv

from .output import TgError

# src/tgcli/config.py -> project root (parents[2]); works for both source
# checkouts and editable installs (which point at the same file).
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Precedence (highest wins): real env vars > .env in CWD > .env in project root.
# load_dotenv never overrides already-set variables, so load project root first.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path.cwd() / ".env")


def require_credentials() -> tuple[int, str]:
    """Return (api_id, api_hash) or raise with a config hint."""
    raw_id = os.environ.get("TELEGRAM_API_ID", "").strip()
    api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()
    if not raw_id or not api_hash:
        raise TgError(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH are not configured",
            "Get them from https://my.telegram.org/apps and put them in .env",
            code=2,
        )
    try:
        api_id = int(raw_id)
    except ValueError:
        raise TgError("TELEGRAM_API_ID must be an integer", code=2) from None
    return api_id, api_hash


def build_proxy() -> tuple | None:
    """Build the telethon proxy tuple from TELEGRAM_PROXY_* vars.

    Telethon tuple form: (type, addr, port[, rdns, username, password]).
    NOTE: the 4th element is rdns, NOT username.
    """
    ptype = os.environ.get("TELEGRAM_PROXY_TYPE", "").strip().lower()
    host = os.environ.get("TELEGRAM_PROXY_HOST", "").strip()
    port = os.environ.get("TELEGRAM_PROXY_PORT", "").strip()
    if not (ptype and host and port):
        return None
    user = os.environ.get("TELEGRAM_PROXY_USERNAME", "").strip()
    pw = os.environ.get("TELEGRAM_PROXY_PASSWORD", "").strip()
    rdns_raw = os.environ.get("TELEGRAM_PROXY_RDNS", "true").strip().lower()
    rdns = rdns_raw not in ("0", "false", "no")
    try:
        port_int = int(port)
    except ValueError:
        raise TgError(f"TELEGRAM_PROXY_PORT must be an integer, got: {port}", code=2) from None
    if user:
        return (ptype, host, port_int, rdns, user, pw)
    return (ptype, host, port_int)


def session_env_var(account: str | None) -> str:
    """Env var name holding the session string for an account (v1: default only)."""
    if account is None:
        return "TELEGRAM_SESSION_STRING"
    return f"TELEGRAM_SESSION_STRING_{account.strip().upper()}"


def load_session(account: str | None) -> str:
    """Return the session string, or raise a config hint if not logged in."""
    var = session_env_var(account)
    value = os.environ.get(var, "").strip()
    if not value:
        if account is not None:
            raise TgError(
                f"No session configured for account '{account}'",
                f"Set {var} in .env (v1 supports the default account only)",
                code=2,
            )
        raise TgError(
            "Not logged in: TELEGRAM_SESSION_STRING not found",
            "Run: tg login --qr",
            code=2,
        )
    return value


def write_env(key: str, value: str, comment: str | None = None) -> Path:
    """Rewrite .env in the project root, preserving comments; replace the
    existing key line in place or append. Returns the .env path."""
    env_path = PROJECT_ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    out: list[str] = []
    done = False
    for line in lines:
        if line.startswith(f"{key}="):
            if comment:
                out.append(f"# {comment}")
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        if out and out[-1].strip():
            out.append("")
        if comment:
            out.append(f"# {comment}")
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return env_path


def clear_env(key: str) -> None:
    """Remove a key line (and the comment line directly above it) from .env."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith(f"{key}="):
            # drop the comment line immediately above, if any
            if out and out[-1].startswith("#"):
                out.pop()
            i += 1
            continue
        out.append(lines[i])
        i += 1
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
