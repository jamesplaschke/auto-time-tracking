#!/bin/bash
# Full setup for auto-time-tracking — run once on a new machine.
# Usage: bash setup.sh --user kevin
#
# What this does:
#   1. Installs uv (Python package manager) if not already installed
#   2. Clones the repo if not already downloaded
#   3. Prompts you to add credentials.json (sent by James)
#   4. Prompts you to enter your API keys (creates .env automatically)
#   5. Installs dependencies
#   6. Trains the classifier on your last 30 days of data
#   7. Runs your first time pull

set -e

REPO_URL="https://github.com/jamesplaschke/auto-time-tracking.git"
REPO_DIR="$HOME/auto-time-tracking"

# ── Parse / prompt for user ID ───────────────────────────────────────────────
USER_ID=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --user) USER_ID="$2"; shift ;;
        *) echo "Unknown option: $1"; echo "Usage: bash setup.sh --user <your_name>"; exit 1 ;;
    esac
    shift
done

if [ -z "$USER_ID" ]; then
    echo ""
    read -rp "Enter your user ID (e.g. kevin, james, laura): " USER_ID
fi
USER_ID=$(echo "$USER_ID" | tr '[:upper:]' '[:lower:]')
USER_UPPER=$(echo "$USER_ID" | tr '[:lower:]' '[:upper:]')

echo ""
echo "Setting up auto-time-tracking for: $USER_ID"
echo ""

# Ensure Homebrew is on PATH regardless of shell profile state (Intel + Apple Silicon)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# ── Step 1: Check git ────────────────────────────────────────────────────────
if ! command -v git &> /dev/null; then
    echo "Git is not installed. Run this first, then re-run setup.sh:"
    echo "  xcode-select --install"
    exit 1
fi

# ── Step 2: Install Homebrew + uv ────────────────────────────────────────────
if ! command -v brew &> /dev/null; then
    echo "=== Installing Homebrew ==="
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon Macs
    export PATH="/opt/homebrew/bin:$PATH"
    echo ""
fi

if ! command -v uv &> /dev/null; then
    echo "=== Installing uv ==="
    brew install uv
    echo ""
fi

# ── Step 3: Clone repo ───────────────────────────────────────────────────────
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "=== Downloading auto-time-tracking ==="
    git clone "$REPO_URL" "$REPO_DIR"
    echo ""
fi
cd "$REPO_DIR"

# ── Step 4: credentials.json ─────────────────────────────────────────────────
if [ ! -f "credentials.json" ]; then
    echo "=================================================="
    echo " ACTION NEEDED: Add credentials.json"
    echo "=================================================="
    echo ""
    echo " James sent you a file called credentials.json."
    echo " Move it into this folder:"
    echo "   $REPO_DIR"
    echo ""
    echo " In Finder: press Cmd+Shift+G and paste that path."
    echo ""
    read -rp " Press Enter once you've added credentials.json... "
    echo ""
    if [ ! -f "credentials.json" ]; then
        echo "credentials.json still not found. Add it and run setup.sh again."
        exit 1
    fi
fi

# ── Step 5: Create .env ──────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "=================================================="
    echo " ACTION NEEDED: Enter your API keys"
    echo "=================================================="
    echo ""
    echo " You need 4 keys:"
    echo "   - Rocketlane key: go to app.rocketlane.com → Settings → API"
    echo "   - The other 3 keys: James sent them over Slack"
    echo ""
    echo " (your typing will be invisible — that's normal, just keep going)"
    echo ""
    read -rsp " Rocketlane API key:  " RL_KEY;      echo ""
    read -rsp " SLACK_BOT_TOKEN:     " SLACK_BOT;   echo ""
    read -rsp " SLACK_APP_TOKEN:     " SLACK_APP;   echo ""
    read -rsp " ANTHROPIC_API_KEY:   " ANTHROPIC;   echo ""
    echo ""

    cat > .env <<EOF
ROCKETLANE_API_KEY_${USER_UPPER}=${RL_KEY}

SLACK_BOT_TOKEN=${SLACK_BOT}
SLACK_APP_TOKEN=${SLACK_APP}
ANTHROPIC_API_KEY=${ANTHROPIC}
EOF
    echo " .env saved."
    echo ""
fi

# ── Step 6: Install dependencies ─────────────────────────────────────────────
echo "=== [1/3] Installing dependencies ==="
uv sync
echo ""

# ── Step 7: Train on historical data ─────────────────────────────────────────
echo "=== [2/3] Training on your last 30 days of data ==="
echo "This will open a browser window so you can connect your Google Calendar."
echo ""
read -rp " Press Enter to open the browser (then sign in with your @ketryx.com account)... "
echo ""
uv run time-tracking-train --user "$USER_ID"
echo ""

# ── Step 8: First pull ───────────────────────────────────────────────────────
echo "=== [3/3] Running your first time pull ==="
echo ""
uv run pull-my-time-for --user "$USER_ID"

echo ""
echo "=================================================="
echo " Setup complete!"
echo "=================================================="
echo ""
echo " Day-to-day, run this:"
echo "   cd ~/auto-time-tracking && uv run pull-my-time-for --user $USER_ID"
echo ""
