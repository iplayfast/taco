"""
TACO Debug Utilities - Simplified from debugprint.py
"""
import os
from enum import IntEnum
from typing import Any

class DebugLevel(IntEnum):
    NONE = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    VERBOSE = 5

# Get debug level from environment or config
def get_debug_level() -> DebugLevel:
    """Get the current debug level"""
    level_str = os.environ.get('TACO_DEBUG_LEVEL', 'INFO')
    try:
        return DebugLevel[level_str.upper()]
    except KeyError:
        return DebugLevel.INFO

def debug_print(*args: Any, level: DebugLevel = DebugLevel.DEBUG) -> None:
    """Print debug message if level is sufficient"""
    current_level = get_debug_level()
    
    if level <= current_level:
        print(f"[{level.name}]", *args)

def error(*args: Any) -> None:
    """Print error message"""
    debug_print(*args, level=DebugLevel.ERROR)

def warning(*args: Any) -> None:
    """Print warning message"""
    debug_print(*args, level=DebugLevel.WARNING)

def info(*args: Any) -> None:
    """Print info message"""
    debug_print(*args, level=DebugLevel.INFO)

def debug(*args: Any) -> None:
    """Print debug message"""
    debug_print(*args, level=DebugLevel.DEBUG)

def verbose(*args: Any) -> None:
    """Print verbose message"""
    debug_print(*args, level=DebugLevel.VERBOSE)
