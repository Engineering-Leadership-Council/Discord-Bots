# Raspberry Pi Setup Guide

This folder contains the Discord Bots service for the Engineering Leadership Council.

## 🚀 Easy Setup

1.  **Clone the Repository** (or your fork):
    ```bash
    git clone https://github.com/Engineering-Leadership-Council/Discord-Bots.git
    cd Discord-Bots
    ```

2.  **Run the Interactive Setup Script**:
    ```bash
    chmod +x scripts/setup.sh
    ./scripts/setup.sh
    ```
    
    The script will ask you:
    -   Whether to use the **Main ELC Repo** (requires Admin Code) or a **Custom Fork**.
    -   To set up your `.env` file (it provides a template).
    -   To install the **Systemd Service** for auto-updates.

## 🔑 Post-Setup

If you chose to edit the `.env` file during setup, paste your tokens there.
If not, you can edit it manually:

```bash
nano .env
```

After updating `.env`, restart the service to apply changes:
```bash
sudo systemctl restart discord-bots
```

## 🔄 Auto-Update

The installed service uses `scripts/start_and_update.sh`, which performs a `git pull` every time the service starts or restarts.
To force an update immediately:

```bash
sudo systemctl restart discord-bots
```