# tg-cli

[![CI](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tg-cli.svg)](https://pypi.org/project/tg-cli/)

Standalone Telegram command-line client. Connects directly to Telegram via
[Telethon](https://github.com/LonamiWebs/Telethon) (MTProto userbot) — **no MCP,
no daemon, no external service**. Everything the CLI does lives in the CLI.

[中文说明](README-zh.md) · [Roadmap](ROADMAP.md)

## Features

- QR-code login (`tg login --qr`) with an independent session
- Messaging: send / reply / edit / delete / forward / polls
- Chats: list dialogs, history, pinned messages, in-chat & global search
- Media: download, send files / albums, voice notes
- Contacts & profile management
- Chat resolution by name fuzzy match, `@username`, numeric id, or `me`
  (Saved Messages), plus local aliases

## Install

Requires Python >= 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
# from PyPI
uv tool install tg-cli          # or: pipx install tg-cli

# from source (development)
git clone https://github.com/noexcs/telegram-cli.git
cd telegram-cli
uv tool install -e .
```

The `tg` command lands in `~/.local/bin/tg` (make sure `~/.local/bin` is on
your PATH).

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Meaning |
|---|---|
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | API credentials from https://my.telegram.org/apps (required) |
| `TELEGRAM_SESSION_STRING` | Session string; generated automatically by `tg login` |
| `TELEGRAM_PROXY_TYPE/HOST/PORT` | Proxy settings; **required** when Telegram is unreachable directly (e.g. CN networks). Common setup: `socks5` + `127.0.0.1:7890` (Clash) |
| `TELEGRAM_PROXY_USERNAME/PASSWORD/RDNS` | Optional proxy auth / remote DNS |
| `TELEGRAM_DEVICE_MODEL/SYSTEM_VERSION/APP_VERSION` | Optional stable device identity |

Precedence: real environment variables > `.env` in the current directory >
`.env` in the project root.

## Login

```bash
tg login --qr      # scan the QR with your phone (Settings → Devices → Link Desktop Device)
tg login --phone   # fallback: SMS code flow
tg me              # verify
tg logout          # remove the session
```

> **Note:** the session is independent — do not reuse the session string of
> another live client (e.g. an MCP daemon). Two live clients sharing one
> session trigger `AuthKeyDuplicatedError`.

## Commands

| Command | Description |
|---|---|
| `tg me` | Show your account info |
| `tg chats [keyword]` | List dialogs; `-t user/group/channel`, `-u` unread, `--archived` |
| `tg hist <chat> [n]` | Recent messages (default 10) |
| `tg send <chat> <text...>` | Send a message; `-p md/html` |
| `tg reply <chat> <msg_id> <text...>` | Reply to a message |
| `tg edit <chat> <msg_id> <new_text>` | Edit your own message |
| `tg del <chat> <ids...>` | Delete messages (revoke for both sides) |
| `tg fwd <src> <msg_ids...> <dst>` | Forward messages (last arg is the target) |
| `tg dl <chat> <msg_id> [-o path]` | Download media (default `~/Downloads/telegram_<chat>_<msgid>`) |
| `tg sf <chat> <files...> [-c caption]` | Send files; 2–10 files become an album |
| `tg voice <chat> <file>` | Send a voice note |
| `tg search <chat> <query>` | Search messages inside a chat |
| `tg gsearch <query> [-p page]` | Global search across public chats |
| `tg contacts` | List contacts |
| `tg pinned <chat>` | Show pinned messages |
| `tg poll <chat> "<question>" <opts...>` | Create a poll; `--multiple/--quiz/--public` |
| `tg profile --name/--bio/--photo` | Update your profile |
| `tg alias set/list/rm` | Local chat aliases (`~/.config/tg/aliases.json`) |

Global flags: `--account` (v1: default only), `--json` (raw JSON output).
Exit codes: `0` ok, `1` command error, `2` config/connection/session error,
`130` interrupted.

## FAQ

- **`AuthKeyDuplicatedError`** — two live clients share one session. Run
  `tg logout` then `tg login --qr` to create a fresh one.
- **`FloodWaitError`** — Telegram rate limit; the CLI waits up to 60s
  automatically, longer waits are reported.
- **"cannot reach Telegram"** — check the proxy (e.g. Clash on
  `127.0.0.1:7890`) and `TELEGRAM_PROXY_*` in `.env`.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan (messaging enhancements, chat &
group management, contacts, folders, multi-account, voice transcription).

## License & acknowledgments

[Apache-2.0](LICENSE). Proxy-injection approach, session-generation flow and
environment variable naming inspired by
[chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp)
(Apache-2.0).
