#!/bin/bash
set -euo pipefail

# ── Agent Dropbox Server Setup ───────────────────────────────────────
# Run on a fresh EC2 instance (Ubuntu 22.04+ recommended).
# Prerequisites: AWS CLI configured with S3 permissions.
#
# Usage: ./setup-server.sh
# ─────────────────────────────────────────────────────────────────────

DOMAIN="${ADBOX_DOMAIN:-}"
S3_BUCKET="${ADBOX_S3_BUCKET:-agent-dropbox}"
S3_REGION="${ADBOX_S3_REGION:-us-east-1}"

echo "=== Agent Dropbox Server Setup ==="
echo ""

# ── 1. System dependencies ───────────────────────────────────────────
echo "[1/7] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# ── 2. Create S3 bucket ─────────────────────────────────────────────
echo "[2/7] Creating S3 bucket: $S3_BUCKET ..."
if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "  Bucket already exists."
else
    aws s3api create-bucket \
        --bucket "$S3_BUCKET" \
        --region "$S3_REGION" \
        --create-bucket-configuration LocationConstraint="$S3_REGION" 2>/dev/null || \
    aws s3api create-bucket --bucket "$S3_BUCKET" --region "$S3_REGION"
    echo "  Bucket created."
fi

aws s3api put-bucket-versioning \
    --bucket "$S3_BUCKET" \
    --versioning-configuration Status=Enabled
echo "  Versioning enabled."

# ── 3. Clone / update repo ──────────────────────────────────────────
INSTALL_DIR="$HOME/agent-dropbox"
echo "[3/7] Setting up application in $INSTALL_DIR ..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  Directory exists, pulling latest..."
    cd "$INSTALL_DIR" && git pull || true
else
    echo "  Please copy the agent-dropbox-open-source/server directory to $INSTALL_DIR/server"
    mkdir -p "$INSTALL_DIR/server"
fi

# ── 4. Python environment ───────────────────────────────────────────
echo "[4/7] Setting up Python virtual environment..."
cd "$INSTALL_DIR/server"
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

# ── 5. Generate secrets ─────────────────────────────────────────────
echo "[5/7] Generating secrets..."
ENV_FILE="$INSTALL_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "$ENV_FILE" <<EOF
ADBOX_SECRET_KEY=$SECRET
ADBOX_S3_ACCESS_KEY=${AWS_ACCESS_KEY_ID:-CHANGE_ME}
ADBOX_S3_SECRET_KEY=${AWS_SECRET_ACCESS_KEY:-CHANGE_ME}
ADBOX_S3_REGION=$S3_REGION
ADBOX_S3_BUCKET=$S3_BUCKET
ADBOX_DATABASE_URL=sqlite+aiosqlite:///$INSTALL_DIR/agent_dropbox.db
EOF
    echo "  Created $ENV_FILE — edit S3 credentials if needed."
else
    echo "  $ENV_FILE already exists, skipping."
fi

# ── 6. Systemd service ──────────────────────────────────────────────
echo "[6/7] Creating systemd service..."
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
sudo systemctl start agent-dropbox
echo "  Service started on port 8000."

# ── 7. Generate first pairing token ─────────────────────────────────
echo "[7/7] Generating first pairing token..."
cd "$INSTALL_DIR/server"
source .venv/bin/activate
export $(cat "$ENV_FILE" | xargs)
python3 "$INSTALL_DIR/scripts/generate-token.py" \
    --device-name "First Device" \
    --db "$INSTALL_DIR/agent_dropbox.db"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Server running at: http://$(curl -s ifconfig.me):8000"
echo ""
if [ -n "$DOMAIN" ]; then
    echo "To enable HTTPS with domain $DOMAIN:"
    echo "  sudo certbot --nginx -d $DOMAIN"
fi
echo ""
echo "Next steps:"
echo "  1. Edit $ENV_FILE with your AWS credentials"
echo "  2. sudo systemctl restart agent-dropbox"
echo "  3. Enter the pairing token in the Agent Dropbox desktop app"
