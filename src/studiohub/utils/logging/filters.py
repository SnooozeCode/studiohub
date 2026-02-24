# studiohub/utils/logging/filters.py
"""Logging filters for redacting sensitive information."""

from __future__ import annotations

import logging
import re

# Sensitive data patterns to redact
SENSITIVE_PATTERNS = [
    (re.compile(r'(password["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
    (re.compile(r'(token["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
    (re.compile(r'(api[_-]?key["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
    (re.compile(r'(secret["\s]*[:=]["\s]*)[^"\s]+'), r'\1[REDACTED]'),
]


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