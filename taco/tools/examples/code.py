"""
TACO Code Tools - Functions for code generation and execution
"""
from typing import Dict, Any, Optional
from taco.tools.executor import execute_code, validate_code

def run_python(code: str) -> Dict[str, Any]:
    """
    Execute Python code and return the result
    
    Args:
        code: Python code to execute
    
    Returns:
        Dict containing execution result
    """
    return execute_code(code)

def check_code(code: str) -> Dict[str, Any]:
    """
    Validate Python code without executing it
    
    Args:
        code: Python code to validate
    
    Returns:
        Dict containing validation result
    """
    return validate_code(code)
