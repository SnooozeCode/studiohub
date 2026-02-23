"""
Structured logging for StudioHub.

Provides:
- Rotating file logs (prevents unlimited growth)
- Different log levels (DEBUG, INFO, WARNING, ERROR)
- Context-aware logging (source file, function, line)
- Sensitive data redaction
- Performance tracking
"""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from datetime import datetime
import json
import re

# Sensitive data patterns to redact
SENSITIVE_PATTERNS = [
    (re.compile(r'(password["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
    (re.compile(r'(token["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
    (re.compile(r'(api[_-]?key["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
    (re.compile(r'(secret["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
]

# Log format with context
LOG_FORMAT = '%(asctime)s | %(levelname)8s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Structured JSON format for machine parsing
JSON_LOG_FORMAT = {
    "timestamp": "%(asctime)s",
    "level": "%(levelname)s",
    "logger": "%(name)s",
    "module": "%(module)s",
    "function": "%(funcName)s",
    "line": "%(lineno)d",
    "message": "%(message)s",
}

class SensitiveDataFilter(logging.Filter):
    """Filter that redacts sensitive information from logs."""
    
    def __init__(self, patterns=None):
        super().__init__()
        self.patterns = patterns or SENSITIVE_PATTERNS
    
    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)
        
        # Also redact in args if they're strings
        if hasattr(record, 'args'):
            args = list(record.args)
            for i, arg in enumerate(args):
                if isinstance(arg, str):
                    for pattern, replacement in self.patterns:
                        args[i] = pattern.sub(replacement, arg)
            record.args = tuple(args)
        
        return True

class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages."""
    
    def __init__(self, logger, context=None):
        super().__init__(logger, context or {})
    
    def process(self, msg, kwargs):
        # Add context to message
        if self.extra:
            context_str = ' '.join(f'[{k}={v}]' for k, v in self.extra.items())
            msg = f'{context_str} {msg}'
        
        # Add extra context to kwargs for structured logging
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs

class JsonFormatter(logging.Formatter):
    """Format logs as JSON for machine parsing."""
    
    def __init__(self, fmt_dict=None, datefmt=None):
        super().__init__(datefmt=datefmt)
        self.fmt_dict = fmt_dict if fmt_dict else JSON_LOG_FORMAT
    
    def format(self, record):
        record.message = record.getMessage()
        
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        
        # Build JSON object
        log_entry = {}
        for key, value in self.fmt_dict.items():
            if value == '%(asctime)s':
                log_entry[key] = getattr(record, 'asctime', '')
            elif value == '%(message)s':
                log_entry[key] = record.message
            else:
                # Handle other format strings like %(levelname)s
                fmt_key = value[2:-2]  # Remove %( and )s
                log_entry[key] = getattr(record, fmt_key, '')
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

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
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger("studiohub")
    root_logger.setLevel(numeric_level)
    
    # Remove any existing handlers
    root_logger.handlers.clear()
    
    # File handler with rotation (always enabled)
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
    
    # Separate error log for errors only
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
    if sys.stderr.isatty():  # Only if running in terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(logging.Formatter(
            '%(levelname)s: %(message)s'
        ))
        console_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(console_handler)
    
    # Log startup
    root_logger.info("=" * 60)
    root_logger.info("StudioHub starting up")
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Log file: {log_dir / 'studiohub.log'}")
    root_logger.info("=" * 60)
    
    return root_logger

# Global logger instance
_logger = None

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
        # This should be set by the application during startup
        _logger = logging.getLogger("studiohub")
    
    if name:
        logger = _logger.getChild(name)
    else:
        logger = _logger
    
    if context:
        return ContextAdapter(logger, context)
    
    return logger

def set_root_logger(logger: logging.Logger):
    """Set the root logger instance (called from __main__)."""
    global _logger
    _logger = logger

# Performance tracking decorator
def log_performance(logger=None):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance to use (uses default if None)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            log = logger or get_logger(func.__module__)
            start = datetime.now()
            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                log.debug(f"{func.__name__} completed in {elapsed:.2f}ms")
                return result
            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds() * 1000
                log.error(f"{func.__name__} failed after {elapsed:.2f}ms: {e}")
                raise
        return wrapper
    return decorator


def log_critical_operation(logger=None):
    """
    Decorator for critical operations that should always be logged.
    Logs at INFO level normally, ERROR level on failure.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            log = logger or get_logger(func.__module__)
            log.info(f"Starting critical operation: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                log.info(f"Completed critical operation: {func.__name__}")
                return result
            except Exception as e:
                log.error(
                    f"Critical operation failed: {func.__name__}",
                    exc_info=True,
                    extra={
                        "function": func.__name__,
                        "error": str(e),
                        "args": str(args),
                        "kwargs": str(kwargs)
                    }
                )
                raise
        return wrapper
    return decorator

def get_log_stats(appdata_root: Path) -> dict:
    """Get statistics about log files."""
    log_dir = appdata_root / "logs"
    stats = {
        "total_size": 0,
        "file_count": 0,
        "files": []
    }
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.name.endswith('.zip'):
            continue
        size = log_file.stat().st_size
        stats["total_size"] += size
        stats["file_count"] += 1
        stats["files"].append({
            "name": log_file.name,
            "size": size,
            "size_mb": size / (1024 * 1024),
            "modified": datetime.fromtimestamp(log_file.stat().st_mtime)
        })
    
    stats["total_size_mb"] = stats["total_size"] / (1024 * 1024)
    return stats

def archive_old_logs(appdata_root: Path, days: int = 30):
    """Archive logs older than specified days."""
    import zipfile
    from datetime import timedelta
    
    log_dir = appdata_root / "logs"
    archive_dir = log_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    cutoff = datetime.now() - timedelta(days=days)
    logger = get_logger(__name__)
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.name.endswith('.zip'):
            continue
        
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff:
            # Compress old log
            zip_name = archive_dir / f"{log_file.stem}_{mtime.strftime('%Y%m%d')}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(log_file, log_file.name)
            
            # Remove original
            log_file.unlink()
            logger.info(f"Archived old log: {log_file.name}")