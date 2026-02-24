# studiohub/utils/logging/core.py (updated)
"""Core logging setup and configuration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from studiohub.utils.logging.filters import SensitiveDataFilter
from studiohub.utils.logging.formatters import JsonFormatter, LOG_FORMAT, DATE_FORMAT
from studiohub.utils.logging.adapters import ContextAdapter

# Global logger instance
_logger = None


def setup_logging(
    appdata_root: Path,
    *,
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    json_format: bool = False,
) -> logging.Logger:
    """
    Setup application-wide logging.
    
    Args:
        appdata_root: Root directory for application data
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        json_format: Whether to use JSON format for logs
    
    Returns:
        Root logger instance
    """
    log_dir = appdata_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    root_logger = logging.getLogger("studiohub")
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_dir / "studiohub.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    if json_format:
        file_formatter = JsonFormatter()
    else:
        file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(file_handler)
    
    # Separate error log
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    error_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(error_handler)
    
    # Console handler (development only)
    if sys.stderr.isatty():
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        console_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(console_handler)
    
    # Log startup
    root_logger.info("=" * 60)
    root_logger.info("StudioHub starting up")
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Log file: {log_dir / 'studiohub.log'}")
    root_logger.info("=" * 60)
    
    global _logger
    _logger = root_logger
    
    return root_logger


def get_logger(name: str = None, context: dict = None) -> logging.Logger:
    """
    Get a logger instance with optional context.
    
    Args:
        name: Logger name (usually __name__)
        context: Additional context to include in all log messages
    
    Returns:
        Logger instance
    """
    global _logger
    if _logger is None:
        _logger = logging.getLogger("studiohub")
    
    if name:
        logger = _logger.getChild(name)
    else:
        logger = _logger
    
    if context:
        return ContextAdapter(logger, context)
    
    return logger


def set_root_logger(logger: logging.Logger):
    """Set the root logger instance."""
    global _logger
    _logger = logger