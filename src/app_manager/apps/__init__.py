"""Apps module - Application configuration and execution."""

from app_manager.apps.executor import AppExecutor
from app_manager.apps.models import AppConfig
from app_manager.apps.registry import AppRegistry

__all__ = ["AppConfig", "AppRegistry", "AppExecutor"]
