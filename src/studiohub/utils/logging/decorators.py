# studiohub/utils/logging/decorators.py
"""Performance and operation logging decorators."""

from __future__ import annotations

from datetime import datetime

from studiohub.utils.logging.core import get_logger


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