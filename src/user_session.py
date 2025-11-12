"""User session management for persistent user identification across CLI sessions"""

import os
import re
from pathlib import Path
from typing import Optional
from src.logging_config import get_logger

logger = get_logger(__name__)


class UserSessionManager:
    """Manages user sessions with persistent memory of last user"""

    SESSION_DIR = Path.home() / ".agent_memory"
    LAST_USER_FILE = SESSION_DIR / "last_user"

    @classmethod
    def _ensure_session_dir(cls) -> None:
        """Create session directory if it doesn't exist"""
        cls.SESSION_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_last_user(cls) -> Optional[str]:
        """Get the last used user ID from persistent storage"""
        try:
            if cls.LAST_USER_FILE.exists():
                with open(cls.LAST_USER_FILE, "r") as f:
                    user = f.read().strip()
                    return user if user else None
        except Exception as e:
            logger.warning(f"Could not read last user: {e}")
        return None

    @classmethod
    def save_user(cls, user_id: str) -> None:
        """Save the current user ID to persistent storage"""
        try:
            cls._ensure_session_dir()
            with open(cls.LAST_USER_FILE, "w") as f:
                f.write(user_id.strip())
            logger.debug(f"Saved user session: {user_id}")
        except Exception as e:
            logger.error(f"Could not save user session: {e}")

    @classmethod
    def validate_user_id(cls, user_id: str) -> bool:
        """Validate user ID format (alphanumeric and underscore, 1-50 chars)"""
        if not user_id:
            return False
        # Allow letters, numbers, underscores, hyphens
        pattern = r"^[a-zA-Z0-9_\-]{1,50}$"
        return bool(re.match(pattern, user_id))

    @classmethod
    def prompt_for_user(cls) -> str:
        """Interactively prompt for user ID with optional default"""
        last_user = cls.get_last_user()

        while True:
            if last_user:
                prompt = f"Enter your name (default: {last_user}): "
            else:
                prompt = "Enter your name: "

            user_input = input(prompt).strip()

            # Use last user if input is empty and last_user exists
            if not user_input and last_user:
                user_id = last_user
            else:
                user_id = user_input

            # Validate and return
            if cls.validate_user_id(user_id):
                cls.save_user(user_id)
                return user_id
            else:
                print("❌ Invalid name. Use only letters, numbers, hyphens, and underscores (1-50 characters).")
