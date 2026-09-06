# telegram-userbot-cli

[![CI](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/telegram-userbot-cli.svg)](https://pypi.org/project/telegram-userbot-cli/)

Standalone Telegram command-line client. Connects directly to Telegram via
[Telethon](https://github.com/LonamiWebs/Telethon) (MTProto userbot) — **no MCP,
no daemon, no external service**. Everything the CLI does lives in the CLI.

[中文说明](README-zh.md) · [Roadmap](ROADMAP.md)

## Features

- QR-code login (`tg login --qr`) with an independent session
- Messaging: send / reply / edit / delete / forward / polls / schedule /
  drafts / reactions / pinning
- Group administration: create groups/channels, invite / kick / ban,
  admin promotion with granular rights, slow mode, forum topics, admin log
- Chat management: archive, mute, edit title / description / photo,
  invite links, clear history
- Contacts, privacy settings, blocking, dialog folders, multi-account,
  voice transcription
- Media: download, send files / albums / voice notes / stickers / GIFs,
  contact cards
- Chats: list dialogs, history, pinned messages, in-chat & global search,
  online status, common chats
- Contacts & profile management
- Chat resolution by name fuzzy match, `@username`, numeric id, or `me`
  (Saved Messages), plus local aliases

## Install

Requires Python >= 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
# from PyPI
uv tool install telegram-userbot-cli   # or: pipx install telegram-userbot-cli

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

### Core

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

### Messaging & chat management (v2)

| Command | Description |
|---|---|
| `tg schedule <chat> <time> <text...>` | Schedule a message; time is `+30m`/`+2h`/`+1d`, `2026-09-07 14:30`, or a unix ts |
| `tg scheduled <chat>` | List scheduled messages (`--json` supported) |
| `tg unschedule <chat> <ids...>` | Delete scheduled messages |
| `tg draft <chat> [text]` | Save a draft (with text) or show the current draft |
| `tg draft-clear <chat>` | Clear the draft |
| `tg react <chat> <msg_id> <emoji>` | React to a message; `--big` for the big animation |
| `tg unreact <chat> <msg_id>` | Remove your reaction |
| `tg pin <chat> <msg_id>` / `tg unpin <chat> [msg_id]` | Pin / unpin (no id = unpin all) |
| `tg read <chat>` | Mark the chat as read (also clears mention badges) |
| `tg msg-link <chat> <msg_id>` | Export a t.me message link (channels/supergroups only) |
| `tg contact-card <chat> "<name>" <phone>` | Send a contact card |
| `tg sticker <chat> <file>` | Send a sticker file (`.webp` / `.tgs` / `.webm`) |
| `tg gif <chat> <query>` | Search GIFs and send the first match; `-n N` sends the Nth |
| `tg archive <chat>` / `tg unarchive <chat>` | Archive / unarchive a dialog |
| `tg mute <chat> [hours]` / `tg unmute <chat>` | Mute notifications (permanent unless hours given) / unmute |
| `tg chat-title <chat> <title>` | Change group/channel title |
| `tg chat-about <chat> <text>` | Change chat description |
| `tg chat-photo <chat> <file>` | Change the chat photo |
| `tg invite-link <chat>` | Export a chat invite link |
| `tg join <link>` | Join via `t.me/+hash`, `t.me/joinchat/…`, or `t.me/<username>` |
| `tg clear-history <chat>` | Delete all messages (both sides; `--self-only` keeps the other copy) |
| `tg status <user>` | Show a user's online status |
| `tg common-chats <user>` | List chats you share with a user |

### Group administration (v3)

| Command | Description |
|---|---|
| `tg new-group <title> <user...>` | Create a basic group with initial members |
| `tg new-channel <title> [--about text]` | Create a channel; `--group` creates a supergroup |
| `tg invite <chat> <user...>` | Invite users (supergroups & basic groups) |
| `tg kick <chat> <user...>` | Remove users (supergroup kick = view-messages ban; `unban` to reverse) |
| `tg leave <chat>` | Leave a group/channel |
| `tg ban <chat> <user> [days]` | Ban a user (permanent unless days given); supergroups only |
| `tg unban <chat> <user>` | Unban a user |
| `tg banned <chat>` | List banned users (`--json` supported) |
| `tg admins <chat>` | List admins with ranks |
| `tg promote <chat> <user> [--title rank]` | Promote with the standard right set |
| `tg demote <chat> <user>` | Remove admin rights |
| `tg admin-rights <chat> <user> <flags...>` | Set exact rights: `--change-info --post-messages --edit-messages --delete-messages --ban-users --invite-users --pin-messages --add-admins --anonymous --manage-call --other --manage-topics …`; `--rank` |
| `tg slow-mode <chat> [seconds]` | Set slow mode (0 = disable); supergroups only |
| `tg topics <chat>` | List forum topics |
| `tg topic-create <chat> <title> [text]` | Create a forum topic, optionally with a first message |
| `tg admin-log <chat> [-n]` | Recent admin actions |

### Contacts, privacy & misc (v4)

| Command | Description |
|---|---|
| `tg contact add <user> [name] [--phone]` | Add/update a contact |
| `tg contact del <user...>` | Delete contacts (by name/id or `+phone`) |
| `tg contact import <file>` | Bulk import from `.json` / `.csv` (`phone,first_name,last_name`) |
| `tg contact export [file]` | Export contacts as re-importable JSON (default stdout) |
| `tg photo-del [--all]` | Delete your most recent profile photo (or all) |
| `tg privacy get [key...]` | Show privacy settings (default: all) |
| `tg privacy set <key> all\|contacts\|nobody` | Change a privacy setting; `--allow USER` / `--deny USER` refine it |
| `tg block <user>` / `tg unblock <user>` / `tg blocked` | Block management |
| `tg folders` | List dialog folders |
| `tg folder-create <name> --chat <c>...` | Create a folder with chats |
| `tg folder-assign <folder> <chat...>` | Add chats to a folder |
| `tg folder-del <folder>` | Delete a folder |
| `tg folder-order <folder...>` | Reorder folders (pass all in the wanted order) |
| `tg accounts` | List configured accounts |
| `tg login --account <label>` | Log in an additional account |
| `tg vtr <chat> <msg_id>` | Transcribe a voice note (Telegram Premium required) |

### Parity completion (v5)

| Command | Description |
|---|---|
| `tg buttons <chat> <msg_id>` | List a message's inline buttons (with press indexes) |
| `tg press <chat> <msg_id> <idx\|text>` | Press an inline button (shows the bot's answer) |
| `tg reactions <chat> <msg_id>` | Show reactions (counts + recent reactors) |
| `tg members <chat> [-n]` | Full member list (recent first) |
| `tg chat-permissions <chat> [--no-send-stickers …]` | Show/set default member permissions |
| `tg forum <chat> on\|off` | Enable/disable forum mode |
| `tg chat-photo-del <chat>` | Remove the group/channel photo |
| `tg folder-rm <folder> <chat...>` | Remove chats from a folder |
| `tg upload <file>` | Upload a file without sending (prints id/md5) |
| `tg search-public <query>` | Search public chats/users by name |
| `tg resolve <@username>` | Resolve a username to an id |
| `tg stickers` | List your sticker sets |
| `tg user-photos <user> [-n]` | List a user's profile photos |
| `tg bot-info <bot>` | Show a bot's description and commands |
| `tg bot-commands <cmd> <desc>...` | Set your bot's commands (bot accounts only; `--clear`) |

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
