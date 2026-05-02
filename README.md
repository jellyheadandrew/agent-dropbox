# Agent Dropbox

**Agent가 다양한 기기의 파일에 안전하게 접근할 수 있도록 dropbox같은 기능을 agent에게 제공합니다.**

Provide Dropbox-like file access to your AI agents across heterogeneous devices, securely.

---

## What is Agent Dropbox?

Agent Dropbox is an open-source, cross-platform file sync tool designed for AI agent workflows. Set up your own sync server on AWS, pair your devices, and keep designated folders automatically synchronized.

- **Bidirectional sync** — Changes on any device propagate to all others via S3
- **Cross-platform** — Windows, macOS, Linux
- **Self-hosted** — Your server, your data, your rules
- **3-way diff** — Intelligent conflict detection with manual resolution UI
- **Presigned URLs** — Files transfer directly to/from S3, server never touches your data

## Quick Start

### 1. Set up the server

On your EC2 instance (Ubuntu 22.04+):

```bash
git clone https://github.com/jellyheadandrew/agent-dropbox.git
cd agent-dropbox/scripts
chmod +x setup-server.sh
./setup-server.sh
```

This installs the sync server, creates an S3 bucket, and generates your first pairing token.

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
Desktop App (Tauri)          Sync Server (FastAPI)         AWS S3
     │                            │                          │
     ├─ POST /sync/scan ────────►│  List S3 objects ───────►│
     │◄── Remote manifest ───────┤                          │
     │                            │                          │
     │  (3-way diff on client)    │                          │
     │                            │                          │
     ├─ POST /sync/resolve ─────►│  Presigned URLs ─────────│
     │◄── Upload/download URLs ──┤                          │
     │                            │                          │
     ├─ PUT/GET (presigned) ─────┼───── Direct transfer ───►│
     │◄── File data ─────────────┼──────────────────────────┤
```

**The server never touches your file data.** It only issues presigned URLs and manages metadata.

## Project Structure

```
agent-dropbox-open-source/
├── server/          # FastAPI sync server (Python)
├── desktop/         # Tauri v2 desktop app (Rust + React)
├── website/         # Static website (HTML/CSS)
├── scripts/         # Setup and deployment scripts
└── .github/         # CI/CD workflows
```

## Generating Pairing Tokens

```bash
cd server
python ../scripts/generate-token.py --device-name "My Laptop"
```

## Cloud Service

설정이 귀찮으시면 저희 클라우드를 사용하실 수 있습니다. 1% 수수료를 받습니다.

We do host a cloud service for users who don't want to set up their own server. We take 1% commission. If you don't like that, use the open source version.

## About Us

We tried to profit off of this when we made it, but we decided not to and focus on our main robotics and semiconductor research.

Bio: [https://jellyheadandrew.github.io](https://jellyheadandrew.github.io)

## Contributing

Contributions are welcome! Please open an issue or pull request.
