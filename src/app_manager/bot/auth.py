"""Authorization decorators for bot commands."""

from functools import wraps
from typing import Callable

import structlog
from telegram import Update
from telegram.ext import ContextTypes

logger = structlog.get_logger()


def require_auth(func: Callable) -> Callable:
    """Decorator requiring user to be authorized (admin or whitelist)."""

    @wraps(func)
    async def wrapper(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        try:
            user = update.effective_user
            if not user:
                logger.warning("No effective user in update")
                return

            user_id = user.id

            logger.debug(
                "Auth check",
                user_id=user_id,
                admin_ids=self.settings.admin_ids,
                is_authorized=self.settings.is_authorized(user_id),
            )

            if not self.settings.is_authorized(user_id):
                logger.warning(
                    "Unauthorized access attempt",
                    user_id=user_id,
                    username=user.username,
                    command=update.message.text if update.message else None,
                )
                await update.message.reply_text(
                    "You are not authorized to use this bot.\n"
                    "Contact an administrator if you need access."
                )
                return

            logger.info(
                "Authorized command",
                user_id=user_id,
                username=user.username,
                command=update.message.text if update.message else None,
            )

            return await func(self, update, context)
        except Exception as e:
            logger.exception("Error in auth decorator", error=str(e))
            raise

    return wrapper


def require_admin(func: Callable) -> Callable:
    """Decorator requiring user to be an admin."""

    @wraps(func)
    async def wrapper(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        if not self.settings.is_admin(user_id):
            logger.warning(
                "Non-admin attempted admin command",
                user_id=user_id,
                username=user.username,
                command=update.message.text if update.message else None,
            )
            await update.message.reply_text(
                "This command requires admin privileges."
            )
            return

        logger.info(
            "Admin command executed",
            user_id=user_id,
            username=user.username,
            command=update.message.text if update.message else None,
        )

        return await func(self, update, context)

    return wrapper
