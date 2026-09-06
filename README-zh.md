# telegram-userbot-cli

[![CI](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/telegram-userbot-cli.svg)](https://pypi.org/project/telegram-userbot-cli/)

独立 Telegram 命令行客户端。通过 [Telethon](https://github.com/LonamiWebs/Telethon)
（MTProto userbot）直连 Telegram —— **不依赖 MCP、不依赖守护进程、不依赖任何外部服务**，
所有功能都在 CLI 内完成。

[English](README.md) · [Roadmap](ROADMAP.md)

## 特性

- 扫码登录（`tg login --qr`），使用独立会话
- 消息：发送 / 引用回复 / 编辑 / 删除 / 转发 / 投票 / 定时 / 草稿 / 表情回应 / 置顶
- 群组管理：建群 / 建频道、邀请 / 踢人 / 封禁、管理员升降级（细粒度权限）、慢速模式、论坛话题、管理日志
- 聊天管理：归档、免打扰、修改群名 / 简介 / 群头像、邀请链接、清空历史
- 联系人、隐私设置、封锁管理、会话文件夹、多账号、语音转写
- 媒体：下载、发文件 / 相册 / 语音条 / 贴纸 / GIF、发送名片
- 聊天：会话列表、历史记录、置顶消息、会话内与全局搜索、在线状态、共同群组
- 联系人与个人资料管理
- 会话解析：名称模糊匹配、`@username`、数字 id、`me`（已保存消息），以及本地别名

## 安装

需要 Python >= 3.10 与 [uv](https://docs.astral.sh/uv/)。

```bash
# 从 PyPI 安装
uv tool install telegram-userbot-cli   # 或 pipx install telegram-userbot-cli

# 从源码安装（开发）
git clone https://github.com/noexcs/telegram-cli.git
cd telegram-cli
uv tool install -e .
```

`tg` 命令安装在 `~/.local/bin/tg`（请确保 `~/.local/bin` 在 PATH 中）。

## 配置

把 `.env.example` 复制为 `.env` 并填入真实值：

| 变量 | 含义 |
|---|---|
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | my.telegram.org/apps 获取的 API 凭据（必需） |
| `TELEGRAM_SESSION_STRING` | 会话字符串；`tg login` 自动写入 |
| `TELEGRAM_PROXY_TYPE/HOST/PORT` | 代理配置；**本机必须代理**（如 socks5 + 127.0.0.1:7890 Clash） |
| `TELEGRAM_PROXY_USERNAME/PASSWORD/RDNS` | 可选代理认证 / 远程 DNS |
| `TELEGRAM_DEVICE_MODEL/SYSTEM_VERSION/APP_VERSION` | 可选设备标识（显示在 TG 设置→设备） |

优先级：真实环境变量 > 当前目录 `.env` > 项目根目录 `.env`。

## 登录

```bash
tg login --qr      # 手机扫码（设置 → 设备 → 链接桌面设备）
tg login --phone   # 备用：短信验证码流程
tg me              # 验证
tg logout          # 退出登录并删除会话
```

> **注意**：本 CLI 使用独立会话——不要与其他在线的客户端（例如 MCP 守护进程）
> 共用同一个 session 字符串，否则会触发 `AuthKeyDuplicatedError`。

## 命令

### 基础

| 命令 | 说明 |
|---|---|
| `tg me` | 查看自己的账号信息 |
| `tg chats [关键词]` | 会话列表；`-t user/group/channel`、`-u` 只看未读、`--archived` |
| `tg hist <会话> [条数]` | 最近消息（默认 10 条） |
| `tg send <会话> <文本...>` | 发消息；`-p md/html` |
| `tg reply <会话> <消息id> <文本...>` | 引用回复 |
| `tg edit <会话> <消息id> <新文本>` | 编辑自己发的消息 |
| `tg del <会话> <id...>` | 删消息（双方撤回） |
| `tg fwd <来源> <消息id...> <目标>` | 转发（最后一个参数是目标） |
| `tg dl <会话> <消息id> [-o 路径]` | 下载媒体（默认 `~/Downloads/telegram_<会话>_<消息id>`） |
| `tg sf <会话> <文件...> [-c 说明]` | 发文件；2–10 个自动合并为相册 |
| `tg voice <会话> <文件>` | 发语音条 |
| `tg search <会话> <关键词>` | 会话内搜索 |
| `tg gsearch <关键词> [-p 页]` | 全局搜索公开频道 |
| `tg contacts` | 联系人列表 |
| `tg pinned <会话>` | 查看置顶消息 |
| `tg poll <会话> "<问题>" <选项...>` | 创建投票；`--multiple/--quiz/--public` |
| `tg profile --name/--bio/--photo` | 修改个人资料 |
| `tg alias set/list/rm` | 本地会话别名（`~/.config/tg/aliases.json`） |

### 消息增强与聊天管理（v2）

| 命令 | 说明 |
|---|---|
| `tg schedule <会话> <时间> <文本...>` | 定时发送；时间支持 `+30m`/`+2h`/`+1d`、`2026-09-07 14:30` 或 unix 时间戳 |
| `tg scheduled <会话>` | 列出定时消息（支持 `--json`） |
| `tg unschedule <会话> <id...>` | 撤销定时消息 |
| `tg draft <会话> [文本]` | 存草稿（带文本）或查看当前草稿 |
| `tg draft-clear <会话>` | 清空草稿 |
| `tg react <会话> <消息id> <emoji>` | 对消息发表情回应；`--big` 大动画 |
| `tg unreact <会话> <消息id>` | 撤销自己的表情回应 |
| `tg pin <会话> <消息id>` / `tg unpin <会话> [消息id]` | 置顶 / 取消置顶（不带 id = 全部取消） |
| `tg read <会话>` | 标记已读（同时清除 @ 提醒） |
| `tg msg-link <会话> <消息id>` | 导出 t.me 消息链接（仅频道/超级群组） |
| `tg contact-card <会话> "<姓名>" <电话>` | 发送联系人名片 |
| `tg sticker <会话> <文件>` | 发贴纸文件（`.webp` / `.tgs` / `.webm`） |
| `tg gif <会话> <关键词>` | 搜索 GIF 并发送第一条；`-n N` 发第 N 条 |
| `tg archive <会话>` / `tg unarchive <会话>` | 归档 / 取消归档会话 |
| `tg mute <会话> [小时]` / `tg unmute <会话>` | 免打扰（不带小时数 = 永久）/ 取消免打扰 |
| `tg chat-title <会话> <标题>` | 修改群/频道标题 |
| `tg chat-about <会话> <文本>` | 修改群简介 |
| `tg chat-photo <会话> <文件>` | 修改群头像 |
| `tg invite-link <会话>` | 导出群邀请链接 |
| `tg join <链接>` | 通过 `t.me/+hash`、`t.me/joinchat/…` 或 `t.me/<用户名>` 加群 |
| `tg clear-history <会话>` | 清空聊天记录（双方删除；`--self-only` 仅删自己一侧） |
| `tg status <用户>` | 查看用户在线状态 |
| `tg common-chats <用户>` | 列出与该用户的共同群组 |

### 群组管理（v3）

| 命令 | 说明 |
|---|---|
| `tg new-group <标题> <用户...>` | 建基本群并拉入初始成员 |
| `tg new-channel <标题> [--about 简介]` | 建频道；`--group` 建超级群组 |
| `tg invite <会话> <用户...>` | 邀请用户（超级群组与基本群都支持） |
| `tg kick <会话> <用户...>` | 移出用户（超级群组的踢人 = 禁言封禁，`unban` 可恢复） |
| `tg leave <会话>` | 退出群组/频道 |
| `tg ban <会话> <用户> [天数]` | 封禁（不带天数 = 永久）；仅超级群组 |
| `tg unban <会话> <用户>` | 解除封禁 |
| `tg banned <会话>` | 封禁名单（支持 `--json`） |
| `tg admins <会话>` | 管理员列表（含头衔） |
| `tg promote <会话> <用户> [--title 头衔]` | 升级为管理员（标准权限集） |
| `tg demote <会话> <用户>` | 撤销管理员 |
| `tg admin-rights <会话> <用户> <权限...>` | 设置精确权限：`--change-info --post-messages --edit-messages --delete-messages --ban-users --invite-users --pin-messages --add-admins --anonymous --manage-call --other --manage-topics …`；`--rank` 定头衔 |
| `tg slow-mode <会话> [秒]` | 设置慢速模式（0 = 关闭）；仅超级群组 |
| `tg topics <会话>` | 列出论坛话题 |
| `tg topic-create <会话> <标题> [首条消息]` | 创建论坛话题 |
| `tg admin-log <会话> [-n]` | 近期管理操作日志 |

### 联系人、隐私与其他（v4）

| 命令 | 说明 |
|---|---|
| `tg contact add <用户> [姓名] [--phone]` | 新增/更新联系人 |
| `tg contact del <用户...>` | 删除联系人（按名称/id 或 `+手机号`） |
| `tg contact import <文件>` | 从 `.json` / `.csv` 批量导入（`phone,first_name,last_name`） |
| `tg contact export [文件]` | 导出为可再导入的 JSON（默认输出到终端） |
| `tg photo-del [--all]` | 删除最近一张头像（`--all` 删除全部） |
| `tg privacy get [键...]` | 查看隐私设置（默认全部） |
| `tg privacy set <键> all\|contacts\|nobody` | 修改隐私设置；`--allow 用户` / `--deny 用户` 精细化 |
| `tg block <用户>` / `tg unblock <用户>` / `tg blocked` | 封锁管理 |
| `tg folders` | 列出会话文件夹 |
| `tg folder-create <名称> --chat <会话>...` | 创建文件夹并加入会话 |
| `tg folder-assign <文件夹> <会话...>` | 向文件夹追加会话 |
| `tg folder-del <文件夹>` | 删除文件夹 |
| `tg folder-order <文件夹...>` | 重排文件夹（按想要的顺序全部列出） |
| `tg accounts` | 列出已配置的账号 |
| `tg login --account <标签>` | 登录额外账号 |
| `tg vtr <会话> <消息id>` | 语音转文字（需要 Telegram Premium） |

### 对齐补全（v5）

| 命令 | 说明 |
|---|---|
| `tg buttons <会话> <消息id>` | 列出消息的内联按钮（带按压序号） |
| `tg press <会话> <消息id> <序号\|文本>` | 点击内联按钮（显示 bot 应答） |
| `tg reactions <会话> <消息id>` | 查看消息反应（计数 + 最近反应者） |
| `tg members <会话> [-n]` | 完整成员列表（最近加入优先） |
| `tg chat-permissions <会话> [--no-send-stickers …]` | 查看/设置群默认成员权限 |
| `tg forum <会话> on\|off` | 开启/关闭论坛模式 |
| `tg chat-photo-del <会话>` | 删除群/频道头像 |
| `tg folder-rm <文件夹> <会话...>` | 从文件夹移出会话 |
| `tg upload <文件>` | 上传文件到 Telegram 但不发送（输出 id/md5） |
| `tg search-public <关键词>` | 按名称搜索公开群组/用户 |
| `tg resolve <@用户名>` | 把用户名解析为 id（不依赖会话列表） |
| `tg stickers` | 列出你的贴纸包 |
| `tg user-photos <用户> [-n]` | 列出用户的头像 |
| `tg bot-info <bot>` | 查看 bot 的简介与命令 |
| `tg bot-commands <命令> <描述>...` | 设置自己 bot 的命令（仅 bot 账号；`--clear`） |

全局选项：`--account`（v1 仅 default）、`--json`（原始 JSON 输出）。
退出码：`0` 成功、`1` 命令错误、`2` 配置/连接/会话错误、`130` 中断。

## 常见问题

- **`AuthKeyDuplicatedError`** —— 两个在线客户端共用了同一个会话。先
  `tg logout` 再 `tg login --qr` 生成新会话即可。
- **`FloodWaitError`** —— Telegram 限流；60 秒内自动等待，更长的会明确提示。
- **"cannot reach Telegram"** —— 检查代理是否存活（如 Clash 127.0.0.1:7890）
  以及 `.env` 里的 `TELEGRAM_PROXY_*`。

## 路线图

完整规划见 [ROADMAP.md](ROADMAP.md)（消息增强、聊天与群管理、联系人、
文件夹、多账号、语音转文字）。

## 协议与致谢

[Apache-2.0](LICENSE)。代理注入思路、会话生成流程与环境变量命名借鉴自
[chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp)（Apache-2.0）。
