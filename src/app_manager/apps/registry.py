"""Application registry for managing multiple apps."""

from pathlib import Path

import structlog
import yaml

from app_manager.apps.models import AppConfig

logger = structlog.get_logger()


class AppNotFoundError(Exception):
    """Raised when an app is not found in the registry."""

    pass


class AppRegistry:
    """Registry of managed applications."""

    def __init__(self):
        self.apps: dict[str, AppConfig] = {}
        self.default_app: str | None = None

    def load_from_yaml(self, config_path: str | Path) -> None:
        """Load apps from YAML configuration file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Apps config file not found: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config:
            raise ValueError("Empty apps configuration file")

        self.default_app = config.get("default_app")

        for app_data in config.get("apps", []):
            app = AppConfig(
                name=app_data["name"],
                path=Path(app_data["path"]),
                script=app_data.get("script", "scripts/dev.sh"),
                description=app_data.get("description", ""),
                cmd_start=app_data.get("cmd_start", "start"),
                cmd_stop=app_data.get("cmd_stop", "stop"),
                cmd_restart=app_data.get("cmd_restart", "restart"),
                cmd_status=app_data.get("cmd_status", "status"),
                cmd_logs=app_data.get("cmd_logs", "logs"),
                cmd_build=app_data.get("cmd_build", "build"),
                log_backend=app_data.get("log_backend", "/tmp/bot.log"),
                log_frontend=app_data.get("log_frontend", "/tmp/frontend.log"),
            )

            # Validate app configuration
            is_valid, error_msg = app.validate()
            if not is_valid:
                logger.warning(
                    "Invalid app configuration",
                    app=app.name,
                    error=error_msg,
                )

            self.apps[app.name] = app
            logger.info("Registered app", app=app.name, path=str(app.path))

        if not self.apps:
            raise ValueError("No apps configured")

        # Set default app if not specified
        if self.default_app is None:
            self.default_app = next(iter(self.apps.keys()))
            logger.info("Using first app as default", default_app=self.default_app)

    def get(self, name: str | None = None) -> AppConfig:
        """Get app by name or return default."""
        if name is None:
            name = self.default_app

        if name not in self.apps:
            available = ", ".join(self.apps.keys())
            raise AppNotFoundError(
                f"Unknown app: '{name}'. Available apps: {available}"
            )

        return self.apps[name]

    def list_apps(self) -> list[AppConfig]:
        """List all registered apps."""
        return list(self.apps.values())

    def get_app_names(self) -> list[str]:
        """Get list of app names."""
        return list(self.apps.keys())

    def __len__(self) -> int:
        return len(self.apps)

    def __contains__(self, name: str) -> bool:
        return name in self.apps
