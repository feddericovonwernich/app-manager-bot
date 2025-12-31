"""Telegram bot command handlers."""

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from app_manager.apps import AppExecutor, AppRegistry
from app_manager.apps.registry import AppNotFoundError
from app_manager.bot.auth import require_admin, require_auth
from app_manager.config import Settings

logger = structlog.get_logger()


class BotHandlers:
    """Telegram bot command handlers."""

    def __init__(
        self,
        settings: Settings,
        app_registry: AppRegistry,
        executor: AppExecutor | None = None,
    ):
        self.settings = settings
        self.app_registry = app_registry
        self.executor = executor or AppExecutor()

    def _get_app_name(self, args: list[str] | None) -> str | None:
        """Extract app name from command arguments."""
        if args and len(args) > 0:
            return args[0]
        return None

    def _format_app_list(self) -> str:
        """Format list of available apps."""
        apps = self.app_registry.list_apps()
        lines = ["*Available Applications:*\n"]

        for app in apps:
            default_marker = " (default)" if app.name == self.app_registry.default_app else ""
            lines.append(f"  `{app.name}`{default_marker}")
            if app.description:
                lines.append(f"    {app.description}")

        return "\n".join(lines)

    async def start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start command - welcome message."""
        user = update.effective_user
        welcome = (
            f"Hello {user.first_name}!\n\n"
            "I'm the Application Manager Bot.\n"
            "I can help you manage your applications.\n\n"
            "Use /help to see available commands.\n"
            "Use /apps to list managed applications."
        )
        await update.message.reply_text(welcome)

    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /help command - show available commands."""
        help_text = """*Application Manager Bot*

*Basic Commands:*
/start - Welcome message
/help - Show this help
/apps - List managed applications

*Application Management:*
/status [app] - Show application status
/app\\_start [app] - Start application
/app\\_stop [app] - Stop application
/app\\_restart [app] - Restart application
/logs [app] [backend|frontend] - Show recent logs
/build [app] - Build application

*Admin Commands:*
/update [app] - Git pull and restart (admin only)

_Note: If [app] is omitted, the default app is used._
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")

    @require_auth
    async def apps_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /apps command - list managed applications."""
        await update.message.reply_text(
            self._format_app_list(),
            parse_mode="Markdown",
        )

    @require_auth
    async def status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /status command - show application status."""
        app_name = self._get_app_name(context.args)

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(f"Checking status of `{app.name}`...", parse_mode="Markdown")

        result = await self.executor.run(app, "status")

        status_icon = "✅" if result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Status: {app.name}*\n\n```\n{result}\n```",
            parse_mode="Markdown",
        )

    @require_auth
    async def app_start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /app_start command - start application."""
        app_name = self._get_app_name(context.args)

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(f"Starting `{app.name}`...", parse_mode="Markdown")

        result = await self.executor.run(app, "start")

        status_icon = "✅" if result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Start: {app.name}*\n\n```\n{result}\n```",
            parse_mode="Markdown",
        )

    @require_auth
    async def app_stop_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /app_stop command - stop application."""
        app_name = self._get_app_name(context.args)

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(f"Stopping `{app.name}`...", parse_mode="Markdown")

        result = await self.executor.run(app, "stop")

        status_icon = "✅" if result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Stop: {app.name}*\n\n```\n{result}\n```",
            parse_mode="Markdown",
        )

    @require_auth
    async def app_restart_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /app_restart command - restart application."""
        app_name = self._get_app_name(context.args)

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(f"Restarting `{app.name}`...", parse_mode="Markdown")

        result = await self.executor.run(app, "restart")

        status_icon = "✅" if result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Restart: {app.name}*\n\n```\n{result}\n```",
            parse_mode="Markdown",
        )

    @require_auth
    async def logs_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /logs command - show recent logs."""
        args = context.args or []

        # Parse arguments: /logs [app] [backend|frontend]
        app_name = None
        service = "backend"

        for arg in args:
            if arg.lower() in ("backend", "frontend"):
                service = arg.lower()
            else:
                app_name = arg

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(
            f"Fetching {service} logs for `{app.name}`...",
            parse_mode="Markdown",
        )

        result = await self.executor.get_logs(app, service=service)

        if result.success:
            await update.message.reply_text(
                f"*Logs: {app.name} ({service})*\n\n```\n{result.output}\n```",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"❌ Error: {result.error}")

    @require_auth
    async def build_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /build command - build application."""
        app_name = self._get_app_name(context.args)

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(f"Building `{app.name}`...", parse_mode="Markdown")

        result = await self.executor.run(app, "build")

        status_icon = "✅" if result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Build: {app.name}*\n\n```\n{result}\n```",
            parse_mode="Markdown",
        )

    @require_admin
    async def update_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /update command - git pull and restart (admin only)."""
        app_name = self._get_app_name(context.args)

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(
            f"Updating `{app.name}`...\n\n1️⃣ Running git pull...",
            parse_mode="Markdown",
        )

        # Git pull
        git_result = await self.executor.git_pull(app)

        if not git_result.success:
            await update.message.reply_text(
                f"❌ *Git pull failed:*\n\n```\n{git_result}\n```",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"✅ Git pull complete:\n```\n{git_result.output}\n```\n\n2️⃣ Restarting...",
            parse_mode="Markdown",
        )

        # Restart
        restart_result = await self.executor.run(app, "restart")

        status_icon = "✅" if restart_result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Update complete: {app.name}*\n\n```\n{restart_result}\n```",
            parse_mode="Markdown",
        )
