#!/bin/bash

# Configuration
REPO_URL="https://github.com/Engineering-Leadership-Council/Discord-Bots.git"
INSTALL_DIR="$HOME/Discord-Bots"
SERVICE_NAME="discord-bots"
CURRENT_USER=$(whoami)

echo "-----------------------------------"
echo "  ELC Discord Bots - Pi Installer  "
echo "-----------------------------------"

# 1. Install Dependencies
echo "[1/5] Installing System Dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-venv python3-pip

# 2. Clone Repository
echo "[2/5] Setting up Repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists. Pulling latest..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Python Environment
echo "[3/5] Setting up Python Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created venv."
fi
source venv/bin/activate
pip install -r requirements.txt

# 4. Service Setup
echo "[4/5] Configuring Systemd Service..."
# Dynamically create the service file with correct paths/user
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
sudo cp "$INSTALL_DIR/raspberry_pi/discord-bots.service" "$SERVICE_FILE"

# Replace placeholders in the installed service file
sudo sed -i "s|{{USER}}|$CURRENT_USER|g" "$SERVICE_FILE"
sudo sed -i "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" "$SERVICE_FILE"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"
echo "Service started!"

# 5. Auto-Update Setup (Cron)
echo "[5/5] Setting up Hourly Auto-Update..."
CRON_CMD="/bin/bash $INSTALL_DIR/raspberry_pi/update_bots.sh"
CRON_JOB="0 * * * * $CRON_CMD"

# Check if job already exists to avoid duplicates
( crontab -l | grep -v -F "$CRON_CMD" ; echo "$CRON_JOB" ) | crontab -

# Make scripts executable
chmod +x "$INSTALL_DIR/raspberry_pi/run_bot.sh"
chmod +x "$INSTALL_DIR/raspberry_pi/update_bots.sh"

echo "-----------------------------------"
echo "  Installation Complete!  "
echo "-----------------------------------"
echo "Please ensure you create your .env file at $INSTALL_DIR/.env"
echo "Then restart the service: sudo systemctl restart $SERVICE_NAME"
