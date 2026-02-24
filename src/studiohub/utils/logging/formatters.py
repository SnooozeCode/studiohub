# studiohub/utils/logging/formatters.py
"""Logging formatters for structured and standard output."""

from __future__ import annotations

import json
import logging

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