# Application Manager Bot

A Telegram bot for managing applications - start, stop, restart, update, and monitor your apps remotely.

## Features

- **Start/Stop/Restart** applications via Telegram commands
- **Status** monitoring with real-time output
- **Logs** viewing (backend and frontend)
- **Update** capability (git pull + restart) for admins
- **Multi-app** support with YAML configuration
- **Authorization** via admin + whitelist system

## Quick Start

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Get Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID

### 3. Configure the Bot

```bash
cd app-manager-bot

# Copy example configuration
cp .env.example .env

# Edit with your settings
nano .env
```

Set these values in `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=your_user_id_here
```

### 4. Configure Apps

Edit `apps.yaml` to add your applications:

```yaml
default_app: my-app

apps:
  - name: my-app
    path: /path/to/your/app
    script: scripts/dev.sh
    description: My awesome application
```

### 5. Run the Bot

```bash
./scripts/run.sh
```

Or manually:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app_manager.main
```

## Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Welcome message | Anyone |
| `/help` | Show available commands | Anyone |
| `/apps` | List managed applications | Authorized |
| `/status [app]` | Show app status | Authorized |
| `/app_start [app]` | Start application | Authorized |
| `/app_stop [app]` | Stop application | Authorized |
| `/app_restart [app]` | Restart application | Authorized |
| `/logs [app] [backend\|frontend]` | Show recent logs | Authorized |
| `/build [app]` | Build application | Authorized |
| `/update [app]` | Git pull + restart | **Admin only** |

**Note:** If `[app]` is omitted, the default app from `apps.yaml` is used.

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Your Telegram bot token |
| `ADMIN_USER_IDS` | Yes | Comma-separated admin user IDs |
| `ALLOWED_USER_IDS` | No | Additional authorized user IDs |
| `APPS_CONFIG_PATH` | No | Path to apps.yaml (default: `apps.yaml`) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

### Apps Configuration (`apps.yaml`)

```yaml
default_app: my-app

apps:
  - name: my-app
    path: /path/to/app
    script: scripts/dev.sh
    description: App description

    # Optional: Custom command mappings
    cmd_start: start
    cmd_stop: stop
    cmd_restart: restart
    cmd_status: status
    cmd_logs: logs
    cmd_build: build

    # Optional: Log file paths
    log_backend: /tmp/bot.log
    log_frontend: /tmp/frontend.log
```

## Security

### Authorization Levels

1. **Admin** (`ADMIN_USER_IDS`): Full access to all commands including `/update`
2. **Authorized** (`ALLOWED_USER_IDS`): Access to all commands except `/update`
3. **Unauthorized**: No access (receives error message)

### Best Practices

- Keep `ADMIN_USER_IDS` limited to trusted users
- Never commit `.env` to version control
- Use strong, unique bot tokens
- Monitor bot logs for unauthorized access attempts

## Development

### Project Structure

```
app-manager-bot/
├── src/app_manager/
│   ├── main.py           # Entry point
│   ├── config.py         # Settings management
│   ├── bot/
│   │   ├── handlers.py   # Command handlers
│   │   └── auth.py       # Authorization decorators
│   ├── apps/
│   │   ├── models.py     # App configuration
│   │   ├── registry.py   # Multi-app registry
│   │   └── executor.py   # Subprocess execution
│   └── utils/
│       └── logging.py    # Structured logging
├── apps.yaml             # App configurations
├── .env                  # Environment variables
└── pyproject.toml        # Dependencies
```

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

## Troubleshooting

### Bot not responding
- Check that `TELEGRAM_BOT_TOKEN` is correct
- Verify the bot is running (`./scripts/run.sh`)
- Check logs for errors

### "Not authorized" message
- Verify your Telegram user ID is in `ADMIN_USER_IDS` or `ALLOWED_USER_IDS`
- User IDs are numbers, not usernames

### Command times out
- Default timeout is 60 seconds
- Check if the underlying script is hanging
- Review app logs with `/logs`

### App not found
- Verify app path exists in `apps.yaml`
- Check that the management script exists and is executable

## License

MIT
