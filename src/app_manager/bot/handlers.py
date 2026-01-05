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

    @require_auth
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

    @require_auth
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
/branch <branch> [app] - Switch git branch (admin only)
/rollback <n> [app] - Reset n commits and restart (admin only)
/self\\_rollback <n> - Reset n commits on this bot (admin only)
/self\\_logs - Show this bot's logs (admin only)
/self\\_restart - Restart this bot (admin only)
/self\\_update - Update and restart this bot (admin only)

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
            f"Updating `{app.name}`...\n\n1️⃣ Running git fetch...",
            parse_mode="Markdown",
        )

        # Git fetch
        fetch_result = await self.executor.git_fetch(app)

        if not fetch_result.success:
            await update.message.reply_text(
                f"❌ *Git fetch failed:*\n\n```\n{fetch_result}\n```",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"✅ Git fetch complete\n\n2️⃣ Running git pull...",
            parse_mode="Markdown",
        )

        # Git pull
        pull_result = await self.executor.git_pull(app)

        if not pull_result.success:
            await update.message.reply_text(
                f"❌ *Git pull failed:*\n\n```\n{pull_result}\n```",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"✅ Git pull complete:\n```\n{pull_result.output}\n```\n\n3️⃣ Restarting...",
            parse_mode="Markdown",
        )

        # Restart
        restart_result = await self.executor.run(app, "restart")

        status_icon = "✅" if restart_result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Update complete: {app.name}*\n\n```\n{restart_result}\n```",
            parse_mode="Markdown",
        )

    @require_admin
    async def branch_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /branch command - switch git branch (admin only)."""
        args = context.args or []

        if len(args) < 1:
            await update.message.reply_text(
                "Usage: /branch <branch_name> [app]\n\n"
                "Example: /branch main\n"
                "Example: /branch develop myapp"
            )
            return

        # First arg is branch, second (optional) is app name
        branch_name = args[0]
        app_name = args[1] if len(args) > 1 else None

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(
            f"Fetching and switching `{app.name}` to branch `{branch_name}`...",
            parse_mode="Markdown",
        )

        # Fetch first to ensure we have the latest remote branches
        await self.executor.git_fetch(app)

        result = await self.executor.git_checkout(app, branch_name)

        status_icon = "✅" if result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Branch switch: {app.name}*\n\n```\n{result}\n```",
            parse_mode="Markdown",
        )

    @require_admin
    async def rollback_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /rollback - reset X commits and restart app (admin only)."""
        args = context.args or []

        if len(args) < 1:
            await update.message.reply_text(
                "Usage: /rollback <number_of_commits> [app]\n\n"
                "Example: /rollback 1\n"
                "Example: /rollback 2 myapp\n"
                "This will run `git reset --hard HEAD~X` and restart the app."
            )
            return

        try:
            commits = int(args[0])
            if commits < 1:
                raise ValueError("Must be at least 1")
        except ValueError:
            await update.message.reply_text("Error: Please provide a valid positive number.")
            return

        app_name = args[1] if len(args) > 1 else None

        try:
            app = self.app_registry.get(app_name)
        except AppNotFoundError as e:
            await update.message.reply_text(f"Error: {e}")
            return

        await update.message.reply_text(
            f"Rolling back `{app.name}` by {commits} commit(s)...\n\n"
            f"1️⃣ Running `git reset --hard HEAD~{commits}`...",
            parse_mode="Markdown",
        )

        result = await self.executor.git_reset(app.path, commits)

        if not result.success:
            await update.message.reply_text(
                f"❌ *Git reset failed:*\n\n```\n{result}\n```",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"✅ Git reset complete:\n```\n{result.output}\n```\n\n"
            "2️⃣ Restarting...",
            parse_mode="Markdown",
        )

        restart_result = await self.executor.run(app, "restart")

        status_icon = "✅" if restart_result.success else "❌"
        await update.message.reply_text(
            f"{status_icon} *Rollback complete: {app.name}*\n\n```\n{restart_result}\n```",
            parse_mode="Markdown",
        )

    @require_admin
    async def self_rollback_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /self_rollback - reset X commits and restart (admin only)."""
        args = context.args or []

        if len(args) < 1:
            await update.message.reply_text(
                "Usage: /self_rollback <number_of_commits>\n\n"
                "Example: /self_rollback 1\n"
                "This will run `git reset --hard HEAD~1` and restart the bot."
            )
            return

        try:
            commits = int(args[0])
            if commits < 1:
                raise ValueError("Must be at least 1")
        except ValueError:
            await update.message.reply_text("Error: Please provide a valid positive number.")
            return

        await update.message.reply_text(
            f"Rolling back {commits} commit(s)...\n\n"
            f"1️⃣ Running `git reset --hard HEAD~{commits}`...",
            parse_mode="Markdown",
        )

        result = await self.executor.git_reset(self.settings.bot_dir, commits)

        if not result.success:
            await update.message.reply_text(
                f"❌ *Git reset failed:*\n\n```\n{result}\n```",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"✅ Git reset complete:\n```\n{result.output}\n```\n\n"
            "2️⃣ Restarting in 2 seconds...",
            parse_mode="Markdown",
        )

        self.executor.self_restart(self.settings.bot_script)

    @require_admin
    async def self_logs_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /self_logs - show this bot's logs (admin only)."""
        await update.message.reply_text(
            "Fetching bot logs...",
            parse_mode="Markdown",
        )

        result = await self.executor.read_log_file(self.settings.bot_log)

        if result.success:
            await update.message.reply_text(
                f"*Bot Logs:*\n\n```\n{result.output}\n```",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"❌ Error: {result.error}")

    @require_admin
    async def self_restart_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /self_restart - restart this bot (admin only)."""
        await update.message.reply_text(
            "Restarting bot in 2 seconds...",
            parse_mode="Markdown",
        )

        self.executor.self_restart(self.settings.bot_script)

    @require_admin
    async def self_update_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /self_update - git pull and restart this bot (admin only)."""
        await update.message.reply_text(
            "Updating bot...\n\n1️⃣ Running git pull...",
            parse_mode="Markdown",
        )

        result = await self.executor.self_update(
            self.settings.bot_dir,
            self.settings.bot_script,
        )

        if result.success:
            await update.message.reply_text(
                f"✅ Git pull complete:\n```\n{result.output}\n```\n\n"
                "2️⃣ Restarting in 2 seconds...",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"❌ *Git pull failed:*\n\n```\n{result}\n```",
                parse_mode="Markdown",
            )
