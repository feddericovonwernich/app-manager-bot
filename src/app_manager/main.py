"""Application Manager Bot - Main entry point."""

import asyncio
import sys
from pathlib import Path

import structlog
from telegram.ext import Application, CommandHandler

from app_manager.apps import AppRegistry
from app_manager.bot import BotHandlers
from app_manager.config import get_settings
from app_manager.utils import setup_logging

logger = structlog.get_logger()


def create_application(settings, app_registry) -> Application:
    """Create and configure the Telegram application."""
    # Create handlers
    handlers = BotHandlers(settings, app_registry)

    # Build application
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("apps", handlers.apps_command))
    app.add_handler(CommandHandler("status", handlers.status_command))
    app.add_handler(CommandHandler("app_start", handlers.app_start_command))
    app.add_handler(CommandHandler("app_stop", handlers.app_stop_command))
    app.add_handler(CommandHandler("app_restart", handlers.app_restart_command))
    app.add_handler(CommandHandler("logs", handlers.logs_command))
    app.add_handler(CommandHandler("build", handlers.build_command))
    app.add_handler(CommandHandler("update", handlers.update_command))
    app.add_handler(CommandHandler("branch", handlers.branch_command))
    app.add_handler(CommandHandler("self_logs", handlers.self_logs_command))
    app.add_handler(CommandHandler("self_restart", handlers.self_restart_command))
    app.add_handler(CommandHandler("self_update", handlers.self_update_command))

    return app


async def run_bot() -> None:
    """Initialize and run the bot."""
    # Load settings
    settings = get_settings()

    # Setup logging
    setup_logging(settings.log_level)

    logger.info(
        "Starting Application Manager Bot",
        admin_count=len(settings.admin_user_ids),
        allowed_count=len(settings.allowed_user_ids),
    )

    # Load app registry
    config_path = Path(settings.apps_config_path)
    if not config_path.is_absolute():
        # Relative to current working directory
        config_path = Path.cwd() / config_path

    app_registry = AppRegistry()
    try:
        app_registry.load_from_yaml(config_path)
    except FileNotFoundError:
        logger.error(
            "Apps configuration file not found",
            config_path=str(config_path),
        )
        sys.exit(1)
    except Exception as e:
        logger.exception("Failed to load apps configuration", error=str(e))
        sys.exit(1)

    logger.info(
        "Loaded apps",
        app_count=len(app_registry),
        apps=app_registry.get_app_names(),
        default_app=app_registry.default_app,
    )

    # Create and run application
    app = create_application(settings, app_registry)

    logger.info("Bot is ready, starting polling...")

    # Run the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Bot crashed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
