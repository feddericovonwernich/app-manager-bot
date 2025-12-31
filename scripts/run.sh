#!/bin/bash
# Application Manager Bot - Startup Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/app-manager-bot.pid"
LOG_FILE="/tmp/app-manager-bot.log"

cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get running bot PIDs
get_bot_pids() {
    pgrep -f "python.*app_manager.main" 2>/dev/null
}

# Kill all running bot instances
kill_bot() {
    local pids=$(get_bot_pids)
    if [ -n "$pids" ]; then
        log_info "Stopping existing bot instances..."
        echo "$pids" | xargs kill 2>/dev/null
        sleep 1
        # Force kill if still running
        pids=$(get_bot_pids)
        if [ -n "$pids" ]; then
            log_warn "Force killing remaining instances..."
            echo "$pids" | xargs kill -9 2>/dev/null
            sleep 1
        fi
    fi
    # Clean up PID file
    rm -f "$PID_FILE"
}

# Check if bot is running
is_running() {
    local pids=$(get_bot_pids)
    [ -n "$pids" ]
}

# Show bot status
status() {
    local pids=$(get_bot_pids)
    if [ -n "$pids" ]; then
        log_ok "Bot is running (PIDs: $pids)"
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Recent logs:"
            tail -10 "$LOG_FILE" | grep -v "getUpdates\|receive_response\|send_request\|connect_tcp\|start_tls\|response_closed" | tail -5
        fi
        return 0
    else
        log_warn "Bot is not running"
        return 1
    fi
}

# Start the bot
start_bot() {
    # Check prerequisites
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_error ".env file not found. Copy from example:"
            echo "  cp .env.example .env"
            echo "  # Then edit .env with your bot token and user IDs"
            exit 1
        else
            log_error ".env file not found"
            exit 1
        fi
    fi

    if [ ! -f "apps.yaml" ]; then
        log_error "apps.yaml not found"
        exit 1
    fi

    # Kill any existing instances first
    kill_bot

    # Create/activate virtual environment
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv .venv
    fi

    source .venv/bin/activate

    # Install dependencies quietly
    log_info "Checking dependencies..."
    pip install -q -e . 2>/dev/null

    # Start the bot in background
    log_info "Starting Application Manager Bot..."
    nohup python -m app_manager.main > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"

    # Wait a moment and check if it started
    sleep 2
    if is_running; then
        log_ok "Bot started successfully (PID: $pid)"
        log_info "Logs: $LOG_FILE"
    else
        log_error "Bot failed to start. Check logs:"
        tail -20 "$LOG_FILE"
        exit 1
    fi
}

# Show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE" | grep -v "getUpdates\|receive_response\|send_request\|connect_tcp\|start_tls\|response_closed"
    else
        log_error "Log file not found: $LOG_FILE"
        exit 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "Commands:"
    echo "  start   - Start the bot (kills existing instances first)"
    echo "  stop    - Stop the bot"
    echo "  restart - Restart the bot"
    echo "  status  - Show bot status"
    echo "  logs    - Tail the bot logs"
    echo ""
}

# Main
case "${1:-start}" in
    start)
        start_bot
        ;;
    stop)
        kill_bot
        log_ok "Bot stopped"
        ;;
    restart)
        kill_bot
        start_bot
        ;;
    status)
        status
        ;;
    logs)
        show_logs
        ;;
    *)
        usage
        exit 1
        ;;
esac
