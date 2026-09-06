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

### v4 — Contacts, profile & misc (shipped)

- ✅ `contact add/del` — add/delete contacts (`contact del` also matches `+phone`)
- ✅ `contact import <file>` / `contact export` — bulk JSON/CSV import,
  re-importable JSON export (note: Telegram no longer creates contacts for
  unregistered numbers — unmatched imports return 0)
- ✅ `photo-del` — delete the most recent profile photo (`--all` for all)
- ✅ `privacy get/set` — 11 keys (lastseen, phone, calls, p2p, groups, photo,
  forwards, voicemail, about, birthday, addedby); set rules must use the
  `InputPrivacyValue*` classes — the output `PrivacyValue*` classes are
  silently ignored by the server
- ✅ `block <user>` / `unblock <user>` / `blocked` — block management
- ✅ `folders` / `folder-create` / `folder-assign` / `folder-del` /
  `folder-order` — dialog folders (list/create/assign/reorder)
- ✅ `accounts` — multi-account support (`accounts` lists every
  `TELEGRAM_SESSION_STRING*`; `login --account LABEL` and
  `<command> --account LABEL` both work)
- ✅ `vtr <chat> <msg_id>` — voice transcription via raw
  `messages.TranscribeAudioRequest` (telethon has no wrapper). Telegram
  Premium is required server-side; free accounts get a clean error

### v5 — MCP parity completion (shipped)

Closes the remaining gap against the chigwell/telegram-mcp 126-tool scope.
Everything below is now aligned; only the agent-oriented event tools stay
out of scope.

- ✅ `buttons` / `press` — inline keyboard interaction (press shows the
  bot's callback answer)
- ✅ `reactions` — view message reactions (counts + recent reactors)
- ✅ `members` — full participant list (supergroups paginated via
  `ChannelParticipantsRecent`; basic groups via `GetFullChat`)
- ✅ `chat-permissions` — show/set default member rights
  (`messages.editChatDefaultBannedRights`; flags use
  `--send-messages/--no-send-messages` pairs)
- ✅ `search-public` — public chat/user search (`contacts.Search`)
- ✅ `resolve` — username → id (`contacts.ResolveUsername`)
- ✅ `forum on|off` — forum mode toggle
- ✅ `chat-photo-del` — remove group/channel photo (`InputChatPhotoEmpty`)
- ✅ `stickers` — list installed sticker sets
- ✅ `user-photos` — list a user's profile photos
- ✅ `folder-rm` — remove chats from a folder (folders cannot become empty)
- ✅ `upload` — upload a file without sending
- ✅ `bot-info` — bot description + commands (`users.GetFullUser`)
- ✅ `bot-commands` — set own bot's commands (bot accounts only, like
  telegram-mcp's implementation)

### Out of scope

- ❌ Agent-oriented event tools (`wait_for_settled_message`, incoming feed
  watchers) — meaningless for an interactive CLI.
