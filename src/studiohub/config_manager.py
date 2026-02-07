"""
LEGACY SHIM — DO NOT ADD LOGIC HERE.

This file exists temporarily to preserve backwards compatibility
for imports like:

    from config_manager import ConfigManager

All real implementation now lives in:
    studiohub.config.manager
"""

from studiohub.config.manager import *