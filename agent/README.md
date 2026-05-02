# Agent Dropbox — Agent Container

A pre-configured agent container (OpenClaw or Hermes) that has access to files synced by Agent Dropbox.

## Prerequisites

- Agent Dropbox server running (see [HOW_TO_TEST.md](../HOW_TO_TEST.md))
- Docker installed

## Setup

If you used `install.sh`, the agent container is already set up. Otherwise:

### 1. Build the agent container

```bash
cd agent-dropbox-open-source/agent
docker build -t agent-dropbox-agent .
```

### 2. Run

```bash
docker run -it -v ~/agent-dropbox/storage:/shared_data agent-dropbox-agent
```

The agent can now read and write files in `/shared_data/`. Any changes will be picked up by the sync server and synced to connected desktop clients.

## Using Hermes Agent Instead

Edit the first line of `Dockerfile`:

```dockerfile
FROM ghcr.io/nousresearch/hermes-agent:latest
```

Then rebuild: `docker build -t agent-dropbox-agent .`

## Files

| File | Purpose |
|------|---------|
| `AGENT.md` | Behavioral guidelines — tells the agent about `/shared_data/` and file access rules |
| `MEMORY.md` | Persistent knowledge — synced file conventions and constraints |
| `Dockerfile` | Container definition — OpenClaw base with AGENT.md/MEMORY.md baked in |
