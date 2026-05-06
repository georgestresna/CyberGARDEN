#!/bin/bash

# --- Configuration Variables ---
REMOTE_USER="garden"
TARGET_HOST="garden.stresna.space"
SSH_DIR="$HOME/.ssh"
SSH_CONFIG="$SSH_DIR/config"

echo "========================================"
echo " Starting Cloudflare SSH Tunnel Setup"
echo "========================================"

# 1. Detect OS and Install cloudflared if missing
if ! command -v cloudflared &> /dev/null; then
    echo "[+] cloudflared not found. Detecting Operating System..."
    OS="$(uname -s)"
    
    if [ "$OS" = "Darwin" ]; then
        echo "[+] macOS detected. Installing via Homebrew..."
        # Check if Homebrew is installed first
        if ! command -v brew &> /dev/null; then
            echo "[-] Homebrew is required on Mac but not found. Please install it from https://brew.sh/"
            exit 1
        fi
        brew install cloudflare/cloudflare/cloudflared
        
    elif [ "$OS" = "Linux" ]; then
        echo "[+] Linux detected. Downloading Debian/Ubuntu package..."
        curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i /tmp/cloudflared.deb
        rm /tmp/cloudflared.deb
        
    else
        echo "[-] Unsupported Operating System: $OS. Please install cloudflared manually."
        exit 1
    fi
    echo "[+] cloudflared installed successfully."
else
    echo "[+] cloudflared is already installed. Skipping..."
fi

# 2. Ensure the .ssh directory and config file exist with correct permissions
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

# 3. Add the configuration if it doesn't already exist
if ! grep -q "Host $TARGET_HOST" "$SSH_CONFIG"; then
    echo "[+] Adding Cloudflare routing rules to $SSH_CONFIG..."
    
    cat <<EOF >> "$SSH_CONFIG"

Host $TARGET_HOST
    ProxyCommand cloudflared access ssh --hostname %h
EOF
    echo "[+] Rules added."
else
    echo "[+] Routing rules for $TARGET_HOST already exist in $SSH_CONFIG. Skipping..."
fi

# 4. Initiate the SSH connection
echo "========================================"
echo " Connecting to $REMOTE_USER@$TARGET_HOST..."
echo "========================================"

ssh "$REMOTE_USER@$TARGET_HOST"