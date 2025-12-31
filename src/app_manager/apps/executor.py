"""Application executor - runs commands via subprocess."""

import asyncio
from pathlib import Path

import structlog

from app_manager.apps.models import AppConfig

logger = structlog.get_logger()

# Default timeouts in seconds
DEFAULT_COMMAND_TIMEOUT = 60
GIT_PULL_TIMEOUT = 120
LOG_LINES_DEFAULT = 50
MAX_OUTPUT_LENGTH = 3500  # Telegram message limit is ~4096, leave room for formatting


class ExecutionResult:
    """Result of a command execution."""

    def __init__(
        self,
        success: bool,
        output: str,
        return_code: int | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.output = output
        self.return_code = return_code
        self.error = error

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error}\n\n{self.output}" if self.output else f"Error: {self.error}"


class AppExecutor:
    """Execute application management commands via subprocess."""

    def __init__(self, command_timeout: int = DEFAULT_COMMAND_TIMEOUT):
        self.command_timeout = command_timeout

    async def run(
        self,
        app: AppConfig,
        action: str,
        extra_args: list[str] | None = None,
    ) -> ExecutionResult:
        """Run a management script command for an app."""
        script_path = app.script_path
        cmd_arg = app.get_command(action)

        # Build command
        cmd = [str(script_path), cmd_arg]
        if extra_args:
            cmd.extend(extra_args)

        logger.info(
            "Executing command",
            app=app.name,
            action=action,
            cmd=" ".join(cmd),
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(app.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=None,  # Inherit environment
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self.command_timeout,
            )

            output = stdout.decode("utf-8", errors="replace")
            output = self._truncate_output(output)

            success = process.returncode == 0

            logger.info(
                "Command completed",
                app=app.name,
                action=action,
                success=success,
                return_code=process.returncode,
            )

            return ExecutionResult(
                success=success,
                output=output,
                return_code=process.returncode,
            )

        except asyncio.TimeoutError:
            logger.error(
                "Command timed out",
                app=app.name,
                action=action,
                timeout=self.command_timeout,
            )
            return ExecutionResult(
                success=False,
                output="",
                error=f"Command timed out after {self.command_timeout} seconds",
            )

        except FileNotFoundError:
            logger.error(
                "Script not found",
                app=app.name,
                script=str(script_path),
            )
            return ExecutionResult(
                success=False,
                output="",
                error=f"Script not found: {script_path}",
            )

        except Exception as e:
            logger.exception(
                "Command execution failed",
                app=app.name,
                action=action,
            )
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    async def git_pull(self, app: AppConfig) -> ExecutionResult:
        """Run git pull in app directory."""
        logger.info("Running git pull", app=app.name, path=str(app.path))

        try:
            process = await asyncio.create_subprocess_exec(
                "git", "pull",
                cwd=str(app.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=GIT_PULL_TIMEOUT,
            )

            output = stdout.decode("utf-8", errors="replace")
            success = process.returncode == 0

            logger.info(
                "Git pull completed",
                app=app.name,
                success=success,
                return_code=process.returncode,
            )

            return ExecutionResult(
                success=success,
                output=output,
                return_code=process.returncode,
            )

        except asyncio.TimeoutError:
            logger.error("Git pull timed out", app=app.name)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Git pull timed out after {GIT_PULL_TIMEOUT} seconds",
            )

        except Exception as e:
            logger.exception("Git pull failed", app=app.name)
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    async def get_logs(
        self,
        app: AppConfig,
        service: str = "backend",
        lines: int = LOG_LINES_DEFAULT,
    ) -> ExecutionResult:
        """Read recent log lines from log file."""
        log_file = Path(app.log_backend if service == "backend" else app.log_frontend)

        logger.info(
            "Reading logs",
            app=app.name,
            service=service,
            log_file=str(log_file),
            lines=lines,
        )

        if not log_file.exists():
            return ExecutionResult(
                success=False,
                output="",
                error=f"Log file not found: {log_file}",
            )

        try:
            process = await asyncio.create_subprocess_exec(
                "tail", "-n", str(lines), str(log_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=10,
            )

            output = stdout.decode("utf-8", errors="replace")
            output = self._truncate_output(output)

            return ExecutionResult(
                success=True,
                output=output,
                return_code=process.returncode,
            )

        except Exception as e:
            logger.exception("Failed to read logs", app=app.name, service=service)
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    def _truncate_output(self, output: str) -> str:
        """Truncate output to fit Telegram message limits."""
        if len(output) <= MAX_OUTPUT_LENGTH:
            return output

        # Keep the end of the output (most recent/relevant)
        truncated = output[-MAX_OUTPUT_LENGTH:]

        # Find first newline to avoid cutting mid-line
        first_newline = truncated.find("\n")
        if first_newline > 0:
            truncated = truncated[first_newline + 1:]

        return f"...(truncated)...\n{truncated}"
