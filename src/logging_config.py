"""Logging configuration for the agent system"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
) -> logging.Logger:
    """
    Set up logging configuration for the entire application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, only logs to console
        log_dir: Directory for log files (created if doesn't exist)

    Returns:
        Configured logger instance
    """
    # Create logs directory if needed
    if log_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

    # Create root logger
    logger = logging.getLogger("agent")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file_path = Path(log_dir) / log_file
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"agent.{name}")
