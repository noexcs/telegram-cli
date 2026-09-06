# Roadmap

The v1 release covers the core daily workflow. The goal is full coverage of
the Telegram feature surface reachable from a userbot, roughly matching the
126-tool scope of [chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp).

Status legend: ✅ done · 🚧 planned · ❌ deliberately out of scope.

## Milestones

### v2 — Messaging enhancements & chat management (shipped)

Messaging:

- ✅ `schedule <chat> <time> <text...>` — send scheduled messages
  (`send_message(..., schedule=...)`), list/delete scheduled
  (`scheduled <chat>` / `unschedule <chat> <ids...>`)
- ✅ `draft <chat> [text]` / `draft-clear <chat>` — save/get/clear drafts
- ✅ `react <chat> <msg_id> <emoji>` / `unreact` — send/remove reactions
  (note: reacting to Saved Messages is premium-only on Telegram's side)
- ✅ `sticker <chat> <file.webp>` — send stickers (telethon handles via `send_file`)
- ✅ `gif <chat> <query>` — search GIFs (inline query to the built-in @gif bot;
  `messages.searchGifs` was removed from the TL layer) and send
- ✅ `contact-card <chat> <name> <phone>` — send a contact card
- ✅ `pin <chat> <msg_id>` / `unpin <chat> [msg_id]` — pin/unpin messages
- ✅ `read <chat>` — mark a chat as read
- ✅ `msg-link <chat> <msg_id>` — export a t.me message link (channels/supergroups)

Chat management:

- ✅ `archive <chat>` / `unarchive <chat>` — archive/unarchive dialogs
- ✅ `mute <chat> [hours]` / `unmute <chat>` — mute/unmute notifications
- ✅ `chat-title <chat> <title>` / `chat-about <chat> <text>` /
  `chat-photo <chat> <file>` — edit chat info
- ✅ `invite-link <chat>` / `join <link>` — export/import invite links
- ✅ `clear-history <chat>` — delete all messages in a chat (`--self-only` to
  keep the other side's copy)
- ✅ `status <user>` / `common-chats <user>` — online status, common chats

### v3 — Group administration (shipped)

- ✅ `new-group <title> <user...>` / `new-channel <title>` — create groups
  (`--group` flag makes a supergroup) /channels
- ✅ `invite <chat> <user...>` / `kick <chat> <user...>` / `leave <chat>`
  (basic-group kick/leave use `messages.DeleteChatUser`, supergroup kick is a
  view-messages ban like official clients)
- ✅ `ban <chat> <user> [days]` / `unban <chat> <user>` / `banned <chat>`
  (the working participant filter on the current TL layer is
  `ChannelParticipantsKicked`, not `ChannelParticipantsBanned`)
- ✅ `admins <chat>` / `promote <chat> <user> [--title]` / `demote <chat> <user>` /
  `admin-rights <chat> <user> ...` — admin management with granular rights
  (basic groups use `messages.EditChatAdmin`, no titles)
- ✅ `slow-mode <chat> [seconds]` — set/disable slow mode
- ✅ `topics <chat>` / `topic-create <chat> <title> [text]` — forum topics
  (list/create)
- ✅ `admin-log <chat>` — recent admin actions

### v4 — Contacts, profile & misc

- 🚧 `contact add/del` — add/delete contacts
- 🚧 `contact import <file>` / `contact export` — bulk import/export
- 🚧 `photo-del` — delete profile photo
- 🚧 `privacy get/set` — privacy settings (last seen, phone, …)
- 🚧 `block <user>` / `unblock <user>` / `blocked` — block management
- 🚧 `folder ...` — dialog folders (create/assign/reorder)
- 🚧 `accounts` — multi-account support (the `--account` hook already exists;
  v1 resolves the default account only)
- 🚧 `vtr <chat> <msg_id>` — voice transcription. telethon 1.44 has no
  transcribe support; options: Groq HTTP API, or raw
  `messages.transcribeAudio` TL (Telegram Premium)

### Out of scope

- ❌ Agent-oriented event tools (`wait_for_settled_message`, incoming feed
  watchers) — meaningless for an interactive CLI.
