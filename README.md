# Agent Dropbox

**Agent가 다양한 기기의 파일에 안전하게 접근할 수 있도록 dropbox같은 기능을 agent에게 제공합니다.**

Provide Dropbox-like file access to your AI agents across heterogeneous devices, securely.

---

## What is Agent Dropbox?

Agent Dropbox is an open-source, cross-platform file sync tool designed for AI agent workflows. Install the server on any computer where you run your agents (EC2, Mac Mini, home server), pair your devices, and keep designated folders automatically synchronized.

- **Bidirectional sync** — Changes on any device propagate to all others
- **Cross-platform** — Windows, macOS, Linux
- **Self-hosted** — Your server, your data, your rules
- **3-way diff** — Intelligent conflict detection with manual resolution UI
- **AI agent integration** — OpenClaw or Hermes agents access synced files at `/shared_data/`
- **No cloud account needed** — Files stored locally on the server (no AWS/S3 required)

## Quick Start

### 1. Set up the server (any computer)

```bash
curl -fsSL https://raw.githubusercontent.com/jellyheadandrew/agent-dropbox/main/scripts/install.sh | bash
```

The interactive installer will:
- Set up the sync server
- Optionally install an AI agent (OpenClaw or Hermes)
- Generate your first pairing token

### 2. Install the desktop app

Download from [GitHub Releases](https://github.com/jellyheadandrew/agent-dropbox/releases) for your platform.

### 3. Pair your device

1. Open Agent Dropbox
2. Enter your server URL and pairing token
3. Click "Connect"

### 4. Add folders to sync

Click "Add Folder", enter a name and local path. Files sync automatically.

## Architecture

```
Desktop App (Tauri)          Sync Server (FastAPI)         Local Storage
     │                            │                          │
     ├─ POST /sync/scan ────────►│  List files ────────────►│
     │◄── Remote manifest ───────┤                          │
     │                            │                          │
     │  (3-way diff on client)    │                          │
     │                            │                          │
     ├─ POST /sync/resolve ─────►│  Signed URLs ────────────│
     │◄── Upload/download URLs ──┤                          │
     │                            │                          │
     ├─ PUT/GET (signed URL) ───►│  Proxy file transfer ───►│
     │◄── File data ─────────────┤◄─────────────────────────┤
     │                            │                          │
     │                       AI Agent Container              │
     │                       (OpenClaw / Hermes)             │
     │                            │   mounts local storage ──┤
     │                            │   reads/writes files     │
```

Files are stored on the server's local disk. The server proxies all file transfers via HMAC-signed URLs.

## Project Structure

```
agent-dropbox-open-source/
├── server/          # FastAPI sync server (Python)
├── desktop/         # Tauri v2 desktop app (Rust + React)
├── agent/           # AI agent container (OpenClaw/Hermes)
├── website/         # Static website (HTML/CSS)
├── scripts/         # Setup and deployment scripts
└── .github/         # CI/CD workflows
```

## Generating Pairing Tokens

```bash
~/agent-dropbox/scripts/generate-token.sh --device-name "My Laptop"
```

## Cloud Service

설정이 귀찮으시면 저희 클라우드를 사용하실 수 있습니다. 1% 수수료를 받습니다.

We do host a cloud service for users who don't want to set up their own server. We take 1% commission. If you don't like that, use the open source version.

## About Us

We tried to profit off of this when we made it, but we decided not to and focus on our main robotics and semiconductor research.

Bio: [https://jellyheadandrew.github.io](https://jellyheadandrew.github.io)

## Contributing

Contributions are welcome! Please open an issue or pull request.
