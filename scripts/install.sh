#!/bin/bash
# ── Agent Dropbox Server Installer ──────────────────────────────────
#
# One-command setup for Agent Dropbox sync server + AI agent.
# Works on Ubuntu/Debian, macOS, and most Linux distributions.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/jellyheadandrew/agent-dropbox/main/scripts/install.sh | bash
#
# Or download and run:
#   chmod +x install.sh && ./install.sh
# ────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_URL="https://github.com/jellyheadandrew/agent-dropbox"
INSTALL_DIR="${ADBOX_INSTALL_DIR:-$HOME/agent-dropbox}"

# ── Colors ──────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }
header() { echo -e "\n${BOLD}=== $1 ===${NC}\n"; }

# ── Detect OS ───────────────────────────────────────────────────────

detect_os() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    case "$OS" in
        Linux)
            if command -v apt-get &>/dev/null; then
                PKG_MGR="apt"
            elif command -v dnf &>/dev/null; then
                PKG_MGR="dnf"
            elif command -v yum &>/dev/null; then
                PKG_MGR="yum"
            elif command -v pacman &>/dev/null; then
                PKG_MGR="pacman"
            else
                PKG_MGR="unknown"
            fi
            INIT_SYS="systemd"
            if ! command -v systemctl &>/dev/null; then
                INIT_SYS="other"
            fi
            ;;
        Darwin)
            PKG_MGR="brew"
            INIT_SYS="launchd"
            ;;
        *)
            err "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    info "Detected: $OS ($ARCH), package manager: $PKG_MGR, init: $INIT_SYS"
}

# ── Install system dependencies ─────────────────────────────────────

install_python() {
    if command -v python3 &>/dev/null; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
        PY_MIN=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$PY_MAJ" -ge 3 ] && [ "$PY_MIN" -ge 10 ]; then
            ok "Python $PY_VER found"
            return
        fi
        warn "Python $PY_VER found, but 3.10+ is required"
    fi

    info "Installing Python 3..."
    case "$PKG_MGR" in
        apt)    sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv ;;
        dnf)    sudo dnf install -y python3 python3-pip ;;
        yum)    sudo yum install -y python3 python3-pip ;;
        pacman) sudo pacman -Sy --noconfirm python python-pip ;;
        brew)   brew install python@3.12 ;;
        *)      err "Cannot auto-install Python. Please install Python 3.10+ manually."; exit 1 ;;
    esac
    ok "Python installed"
}

install_docker() {
    if command -v docker &>/dev/null; then
        ok "Docker found"
        return
    fi

    info "Installing Docker..."
    case "$OS" in
        Linux)
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y -qq ca-certificates curl gnupg
                sudo install -m 0755 -d /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
                sudo chmod a+r /etc/apt/keyrings/docker.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                sudo apt-get update -qq
                sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io
            else
                curl -fsSL https://get.docker.com | sh
            fi
            sudo usermod -aG docker "$USER" 2>/dev/null || true
            ;;
        Darwin)
            err "Please install Docker Desktop for Mac from https://docker.com/products/docker-desktop"
            echo "  After installing, re-run this script."
            exit 1
            ;;
    esac
    ok "Docker installed"
}

# ── Download server code ────────────────────────────────────────────

download_code() {
    if [ -d "$INSTALL_DIR/server" ] && [ -f "$INSTALL_DIR/server/main.py" ]; then
        ok "Server code already exists at $INSTALL_DIR"
        return
    fi

    info "Downloading Agent Dropbox to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"

    if command -v git &>/dev/null; then
        git clone --depth 1 "$REPO_URL.git" "$INSTALL_DIR.tmp" 2>/dev/null || {
            curl -fsSL "$REPO_URL/archive/refs/heads/main.tar.gz" | tar xz -C "$INSTALL_DIR" --strip-components=1
            return
        }
        cp -r "$INSTALL_DIR.tmp"/* "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$INSTALL_DIR.tmp"/.[!.]* "$INSTALL_DIR/" 2>/dev/null || true
        rm -rf "$INSTALL_DIR.tmp"
    else
        curl -fsSL "$REPO_URL/archive/refs/heads/main.tar.gz" | tar xz -C "$INSTALL_DIR" --strip-components=1
    fi

    ok "Downloaded to $INSTALL_DIR"
}

# ── Interactive setup ───────────────────────────────────────────────

prompt_choice() {
    local prompt="$1"
    local default="$2"
    shift 2
    local options=("$@")

    echo ""
    echo -e "${BOLD}$prompt${NC}"
    for i in "${!options[@]}"; do
        local num=$((i + 1))
        echo "  $num) ${options[$i]}"
    done
    echo -n "  Choose [$default]: "
    read -r choice
    choice="${choice:-$default}"
    echo "$choice"
}

prompt_input() {
    local prompt="$1"
    local default="$2"
    echo -n "  $prompt [$default]: "
    read -r input
    echo "${input:-$default}"
}

setup_interactive() {
    header "Agent Dropbox Server Setup"

    # ── Storage directory ───────────────────────────────────────────
    echo -e "\n${BOLD}[1/5] Storage${NC}"
    echo "  Where should synced files be stored on this machine?"
    STORAGE_DIR=$(prompt_input "Path" "$INSTALL_DIR/storage")
    mkdir -p "$STORAGE_DIR"
    ok "Storage directory: $STORAGE_DIR"

    # ── Network ─────────────────────────────────────────────────────
    echo -e "\n${BOLD}[2/5] Network${NC}"
    echo "  How will client devices connect to this server?"
    NETWORK_CHOICE=$(prompt_choice "Network mode:" "1" "Local network (home server, same WiFi)" "Public internet (EC2, VPS with public IP)")

    if [ "$NETWORK_CHOICE" = "2" ]; then
        PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 api.ipify.org 2>/dev/null || echo "YOUR_IP")
        SERVER_URL=$(prompt_input "Server URL" "http://$PUBLIC_IP:8000")
    else
        if [ "$OS" = "Darwin" ]; then
            LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
        else
            LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
        fi
        SERVER_URL=$(prompt_input "Server URL" "http://$LAN_IP:8000")
    fi
    ok "Server URL: $SERVER_URL"

    # ── Python environment ──────────────────────────────────────────
    echo -e "\n${BOLD}[3/5] Python environment${NC}"
    info "Creating virtual environment..."
    cd "$INSTALL_DIR/server"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    ok "Python environment ready"

    # ── AI Agent ────────────────────────────────────────────────────
    echo -e "\n${BOLD}[4/5] AI Agent${NC}"
    echo "  Which AI agent platform do you want to run?"
    AGENT_CHOICE=$(prompt_choice "Agent platform:" "1" "OpenClaw (default)" "Hermes" "Skip agent setup")

    AGENT_PLATFORM=""
    if [ "$AGENT_CHOICE" != "3" ]; then
        install_docker

        if [ "$AGENT_CHOICE" = "2" ]; then
            AGENT_PLATFORM="hermes"
            AGENT_BASE_IMAGE="ghcr.io/nousresearch/hermes-agent:latest"
        else
            AGENT_PLATFORM="openclaw"
            AGENT_BASE_IMAGE="ghcr.io/openclaw/openclaw:latest"
        fi

        AGENT_DOCKERFILE="$INSTALL_DIR/agent/Dockerfile"
        if [ -f "$AGENT_DOCKERFILE" ]; then
            sed -i.bak "s|^FROM .*|FROM $AGENT_BASE_IMAGE|" "$AGENT_DOCKERFILE" 2>/dev/null || \
            sed -i '' "s|^FROM .*|FROM $AGENT_BASE_IMAGE|" "$AGENT_DOCKERFILE"
            rm -f "${AGENT_DOCKERFILE}.bak"
        fi

        info "Building agent container..."
        if [ -d "$INSTALL_DIR/agent" ]; then
            cd "$INSTALL_DIR/agent"
            docker build -t agent-dropbox-agent . 2>/dev/null || {
                warn "Agent container build failed. You can build it later with:"
                echo "  cd $INSTALL_DIR/agent && docker build -t agent-dropbox-agent ."
                AGENT_PLATFORM=""
            }
            if [ -n "$AGENT_PLATFORM" ]; then
                ok "Agent container built ($AGENT_PLATFORM)"
            fi
        else
            warn "Agent directory not found at $INSTALL_DIR/agent"
            AGENT_PLATFORM=""
        fi
    else
        info "Skipping agent setup"
    fi

    # ── Configuration ───────────────────────────────────────────────
    echo -e "\n${BOLD}[5/5] Starting services${NC}"
    ENV_FILE="$INSTALL_DIR/.env"

    if [ ! -f "$ENV_FILE" ]; then
        SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        cat > "$ENV_FILE" <<EOF
ADBOX_SECRET_KEY=$SECRET
ADBOX_STORAGE_DIR=$STORAGE_DIR
ADBOX_SERVER_BASE_URL=$SERVER_URL
ADBOX_DATABASE_URL=sqlite+aiosqlite:///$INSTALL_DIR/agent_dropbox.db
EOF
        ok "Configuration saved to $ENV_FILE"
    else
        ok "Configuration already exists at $ENV_FILE"
    fi

    # ── Start server ────────────────────────────────────────────────
    start_server

    # ── Health check ────────────────────────────────────────────────
    info "Waiting for server to start..."
    sleep 2
    HEALTH_OK=false
    for i in $(seq 1 10); do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            HEALTH_OK=true
            break
        fi
        sleep 1
    done

    if [ "$HEALTH_OK" = true ]; then
        ok "Server health check passed"
    else
        warn "Server health check failed. Check logs:"
        if [ "$INIT_SYS" = "systemd" ]; then
            echo "  sudo journalctl -u agent-dropbox -n 50"
        else
            echo "  Check the server terminal for errors"
        fi
    fi

    # ── Start agent container ───────────────────────────────────────
    if [ -n "$AGENT_PLATFORM" ]; then
        info "Starting agent container..."
        docker stop agent-dropbox-agent 2>/dev/null || true
        docker rm agent-dropbox-agent 2>/dev/null || true
        docker run -d \
            --name agent-dropbox-agent \
            --restart unless-stopped \
            -v "$STORAGE_DIR:/shared_data" \
            agent-dropbox-agent 2>/dev/null && \
            ok "Agent container started (files mounted at /shared_data)" || \
            warn "Agent container failed to start. You may need to run: newgrp docker"
    fi

    # ── Generate first pairing token ────────────────────────────────
    info "Generating first pairing token..."
    cd "$INSTALL_DIR"
    source server/.venv/bin/activate
    set -a; source "$ENV_FILE"; set +a
    python3 scripts/generate-token.py --device-name "First Device" --env-file "$ENV_FILE"

    # ── Done ────────────────────────────────────────────────────────
    header "Setup Complete!"
    echo -e "  Server:  ${GREEN}$SERVER_URL${NC}"
    echo ""
    echo "  Install the Agent Dropbox app on your devices:"
    echo "  ${BLUE}$REPO_URL/releases${NC}"
    echo ""
    echo "  To generate more pairing tokens:"
    echo "  ${BOLD}$INSTALL_DIR/scripts/generate-token.sh --device-name \"My Phone\"${NC}"
    echo ""
}

# ── Service management ──────────────────────────────────────────────

start_server() {
    ENV_FILE="$INSTALL_DIR/.env"

    if [ "$INIT_SYS" = "systemd" ]; then
        info "Creating systemd service..."
        sudo tee /etc/systemd/system/agent-dropbox.service > /dev/null <<EOF
[Unit]
Description=Agent Dropbox Sync Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/server
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_DIR/server/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable agent-dropbox
        sudo systemctl restart agent-dropbox
        ok "Server started via systemd (port 8000)"

    elif [ "$INIT_SYS" = "launchd" ]; then
        PLIST_DIR="$HOME/Library/LaunchAgents"
        PLIST_FILE="$PLIST_DIR/com.agentdropbox.server.plist"
        mkdir -p "$PLIST_DIR"
        cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentdropbox.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/server/.venv/bin/uvicorn</string>
        <string>main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR/server</string>
    <key>EnvironmentVariables</key>
    <dict>
$(while IFS='=' read -r key value; do
    [ -z "$key" ] || [ "${key:0:1}" = "#" ] && continue
    echo "        <key>$key</key>"
    echo "        <string>$value</string>"
done < "$ENV_FILE")
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/server.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/server.err.log</string>
</dict>
</plist>
EOF
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        launchctl load "$PLIST_FILE"
        ok "Server started via launchd (port 8000)"
    else
        info "Starting server in background..."
        cd "$INSTALL_DIR/server"
        source .venv/bin/activate
        set -a; source "$ENV_FILE"; set +a
        nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "$INSTALL_DIR/server.log" 2>&1 &
        echo $! > "$INSTALL_DIR/server.pid"
        ok "Server started in background (PID: $(cat "$INSTALL_DIR/server.pid"), port 8000)"
        echo "  To stop: kill \$(cat $INSTALL_DIR/server.pid)"
    fi
}

# ── Main ────────────────────────────────────────────────────────────

main() {
    header "Agent Dropbox Installer"
    detect_os
    install_python
    download_code
    setup_interactive
}

main "$@"
