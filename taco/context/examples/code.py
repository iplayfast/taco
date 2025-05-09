"""
TACO Code Context Templates
"""
from typing import Dict

# Python code context template
PYTHON_TEMPLATE = """
You are working with Python {version} code.
Libraries available: {libraries}
Coding style: {style}
Include comments: {comments}
Error handling: {error_handling}
"""

# Default Python variables
PYTHON_VARIABLES = {
    "version": "3.10",
    "libraries": "standard library",
    "style": "PEP 8 compliant",
    "comments": "docstrings and inline comments",
    "error_handling": "use try-except for expected errors"
}

def get_default_code_context() -> Dict[str, Dict[str, str]]:
    """Get default context templates for code"""
    return {
        "python": {
            "template": PYTHON_TEMPLATE,
            "variables": PYTHON_VARIABLES
        }
    }
