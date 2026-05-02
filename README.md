# Agent Dropbox

Sync files from your devices to the computer where your AI agents run.

## How it works

1. **Install the server** on any computer (EC2, Mac Mini, home server)
2. **Install the client app** on your devices (Windows, Mac, Linux)
3. **Pair and sync** — files flow bidirectionally between devices and your agent

Your agent reads and writes synced files at `/shared_data/`.

## Server setup

```bash
curl -fsSL https://raw.githubusercontent.com/jellyheadandrew/agent-dropbox/main/scripts/install.sh | bash
```

## Client app

Download from [Releases](https://github.com/jellyheadandrew/agent-dropbox/releases).

## Generate more pairing tokens

```bash
~/agent-dropbox/scripts/generate-token.sh --device-name "My Phone"
```
