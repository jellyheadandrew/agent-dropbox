# Agent Dropbox

![Agent Dropbox](teaser.png)

Sync files between your devices and the computer where your AI agents run.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Laptop  │────▶│          │◀────│ Desktop  │
└──────────┘     │  Server  │     └──────────┘
                 │  (sync)  │     ┌──────────┐
                 │          │────▶│  Agent   │
                 └──────────┘     │Container │
                  Your VPS /       └──────────┘
                  EC2 / Mac Mini    reads & writes
                                    /shared_data/
```

Your devices sync files to a central server. An AI agent container mounts those files at `/shared_data/` and can read and write them.

For a step-by-step walkthrough (creating an EC2 instance, pairing, syncing), see [HOW_TO_TEST.md](HOW_TO_TEST.md).

## 1. Install the server

On any always-on Linux server or Mac Mini (EC2, VPS, home box):

```bash
curl -fsSL https://raw.githubusercontent.com/jellyheadandrew/agent-dropbox/main/scripts/install.sh | bash
```

The installer asks a few questions, sets everything up, and prints your server URL and a pairing token at the end.

## 2. Install the desktop app

Download for your OS from the [latest release](https://github.com/jellyheadandrew/agent-dropbox/releases/latest):

| OS      | File |
|---------|------|
| Windows | `Agent-Dropbox_x64-setup.msi` — double-click to install |
| macOS   | `Agent-Dropbox_aarch64.dmg` (Apple Silicon) or `Agent-Dropbox_x64.dmg` (Intel) — drag to Applications |
| Linux   | `agent-dropbox_amd64.deb` (`sudo apt install ./agent-dropbox_amd64.deb`) or the `.AppImage` |

## 3. Pair

Open Agent Dropbox. Paste the **Server URL** and **Token** from step 1. Click **Connect**.

That's it. Click **Add Folder** to start syncing.

## Managing the server

After install, you have an `agent-dropbox` command on your server box:

```bash
agent-dropbox token --device-name "My Phone"   # add another device
agent-dropbox status                           # is it running?
agent-dropbox logs                             # tail the log
agent-dropbox restart
agent-dropbox stop
agent-dropbox uninstall                        # remove the service (keeps your files)
```

## Project structure

```
server/      FastAPI sync server (Python)
desktop/     Tauri desktop app (Rust + React)
agent/       AI agent Docker container
scripts/     Installer + agent-dropbox CLI
website/     Project website (GitHub Pages)
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
