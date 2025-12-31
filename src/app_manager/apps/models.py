"""Application configuration models."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Configuration for a managed application."""

    name: str
    path: Path
    script: str = "scripts/dev.sh"
    description: str = ""

    # Command mappings - can be customized per app
    cmd_start: str = "start"
    cmd_stop: str = "stop"
    cmd_restart: str = "restart"
    cmd_status: str = "status"
    cmd_logs: str = "logs"
    cmd_build: str = "build"

    # Log file paths (for reading logs directly)
    log_backend: str = "/tmp/bot.log"
    log_frontend: str = "/tmp/frontend.log"

    def __post_init__(self):
        """Ensure path is a Path object."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    @property
    def script_path(self) -> Path:
        """Get full path to the management script."""
        return self.path / self.script

    def get_command(self, action: str) -> str:
        """Get the command argument for an action."""
        cmd_attr = f"cmd_{action}"
        return getattr(self, cmd_attr, action)

    def validate(self) -> tuple[bool, str]:
        """Validate the app configuration."""
        if not self.path.exists():
            return False, f"App path does not exist: {self.path}"

        if not self.script_path.exists():
            return False, f"Script does not exist: {self.script_path}"

        if not self.script_path.is_file():
            return False, f"Script is not a file: {self.script_path}"

        return True, "OK"
