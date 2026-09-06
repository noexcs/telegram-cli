# telegram-cli

[![CI](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/noexcs/telegram-cli/actions/workflows/ci.yml)

独立 Telegram 命令行客户端。通过 [Telethon](https://github.com/LonamiWebs/Telethon)
（MTProto userbot）直连 Telegram —— **不依赖 MCP、不依赖守护进程、不依赖任何外部服务**，
所有功能都在 CLI 内完成。

[English](README.md) · [Roadmap](ROADMAP.md)

## 特性

- 扫码登录（`tg login --qr`），使用独立会话
- 消息：发送 / 引用回复 / 编辑 / 删除 / 转发 / 投票
- 聊天：会话列表、历史记录、置顶消息、会话内搜索与全局搜索
- 媒体：下载、发文件 / 相册、语音条
- 联系人与个人资料管理
- 会话解析：名称模糊匹配、`@username`、数字 id、`me`（已保存消息），以及本地别名

## 安装

需要 Python >= 3.10 与 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/<user>/telegram-cli.git
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
