# studiohub/utils/logging/adapters.py
"""Logger adapters for adding context to log messages."""

from __future__ import annotations

import logging


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