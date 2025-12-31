"""Application executor - runs commands via subprocess."""

import asyncio
import subprocess
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

    async def git_checkout(self, app: AppConfig, branch: str) -> ExecutionResult:
        """Switch to a different git branch in app directory."""
        logger.info("Switching branch", app=app.name, branch=branch, path=str(app.path))

        try:
            process = await asyncio.create_subprocess_exec(
                "git", "checkout", "--force", branch,
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
                "Branch switch completed",
                app=app.name,
                branch=branch,
                success=success,
                return_code=process.returncode,
            )

            return ExecutionResult(
                success=success,
                output=output,
                return_code=process.returncode,
            )

        except asyncio.TimeoutError:
            logger.error("Branch switch timed out", app=app.name, branch=branch)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Branch switch timed out after {GIT_PULL_TIMEOUT} seconds",
            )

        except Exception as e:
            logger.exception("Branch switch failed", app=app.name, branch=branch)
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    async def git_fetch(self, app: AppConfig) -> ExecutionResult:
        """Run git fetch in app directory."""
        logger.info("Running git fetch", app=app.name, path=str(app.path))

        try:
            process = await asyncio.create_subprocess_exec(
                "git", "fetch",
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
                "Git fetch completed",
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
            logger.error("Git fetch timed out", app=app.name)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Git fetch timed out after {GIT_PULL_TIMEOUT} seconds",
            )

        except Exception as e:
            logger.exception("Git fetch failed", app=app.name)
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
                "git", "pull", "--stat",
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

    async def read_log_file(
        self,
        log_path: Path,
        lines: int = LOG_LINES_DEFAULT,
    ) -> ExecutionResult:
        """Read recent log lines from any log file."""
        logger.info("Reading log file", log_file=str(log_path), lines=lines)

        if not log_path.exists():
            return ExecutionResult(
                success=False,
                output="",
                error=f"Log file not found: {log_path}",
            )

        try:
            process = await asyncio.create_subprocess_exec(
                "tail", "-n", str(lines), str(log_path),
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
            logger.exception("Failed to read log file", log_file=str(log_path))
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    async def git_reset(self, repo_dir: Path, commits: int = 1) -> ExecutionResult:
        """Reset git repo by X commits (git reset --hard HEAD~X)."""
        logger.info("Resetting git repo", repo_dir=str(repo_dir), commits=commits)

        try:
            process = await asyncio.create_subprocess_exec(
                "git", "reset", "--hard", f"HEAD~{commits}",
                cwd=str(repo_dir),
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
                "Git reset completed",
                repo_dir=str(repo_dir),
                commits=commits,
                success=success,
                return_code=process.returncode,
            )

            return ExecutionResult(
                success=success,
                output=output,
                return_code=process.returncode,
            )

        except asyncio.TimeoutError:
            logger.error("Git reset timed out", repo_dir=str(repo_dir))
            return ExecutionResult(
                success=False,
                output="",
                error=f"Git reset timed out after {GIT_PULL_TIMEOUT} seconds",
            )

        except Exception as e:
            logger.exception("Git reset failed", repo_dir=str(repo_dir))
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    def self_restart(self, script_path: Path) -> None:
        """Trigger a self-restart via detached subprocess.

        Spawns a background process that waits 2 seconds, then calls
        the restart script. This allows the current process to exit
        gracefully while ensuring a new instance starts.
        """
        logger.info("Triggering self-restart", script=str(script_path))

        # Spawn detached process: sleep 2 && /path/to/run.sh restart
        subprocess.Popen(
            ["bash", "-c", f"sleep 2 && {script_path} restart"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    async def self_update(self, bot_dir: Path, script_path: Path) -> ExecutionResult:
        """Git pull the bot repo and trigger restart.

        Returns the git pull result. If successful, also triggers
        a self-restart after a 2-second delay.
        """
        logger.info("Self-updating bot", bot_dir=str(bot_dir))

        try:
            process = await asyncio.create_subprocess_exec(
                "git", "pull", "--stat",
                cwd=str(bot_dir),
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
                "Self-update git pull completed",
                success=success,
                return_code=process.returncode,
            )

            if success:
                # Trigger restart after successful pull
                self.self_restart(script_path)

            return ExecutionResult(
                success=success,
                output=output,
                return_code=process.returncode,
            )

        except asyncio.TimeoutError:
            logger.error("Self-update git pull timed out")
            return ExecutionResult(
                success=False,
                output="",
                error=f"Git pull timed out after {GIT_PULL_TIMEOUT} seconds",
            )

        except Exception as e:
            logger.exception("Self-update failed")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )
