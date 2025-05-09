"""
TACO Code Executor - Simplified from code_executor.py
"""
import sys
from io import StringIO
import ast
from typing import Dict, Any, Optional

def execute_code(code: str) -> Dict[str, Any]:
    """
    Execute Python code in a controlled environment.
    
    Args:
        code: Python code to execute
        
    Returns:
        Dict containing:
            - success: Whether execution was successful (bool)
            - output: Output from the code execution (str)
            - error: Error message if execution failed (str)
    """
    # Capture original stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    # Create string buffers for output capture
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    
    # Results dictionary
    results = {
        "success": False,
        "output": "",
        "error": ""
    }
    
    try:
        # Redirect output
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer
        
        # Create namespace for execution
        namespace = {'__name__': '__main__'}
        
        # Add builtins to namespace
        namespace.update({
            name: getattr(__builtins__, name)
            for name in ['abs', 'all', 'any', 'bin', 'bool', 'chr', 'dict', 
                       'dir', 'divmod', 'enumerate', 'filter', 'float', 'format',
                       'frozenset', 'hash', 'hex', 'int', 'isinstance', 'issubclass',
                       'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct',
                       'ord', 'pow', 'print', 'range', 'repr', 'reversed', 'round',
                       'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip']
        })
        
        # Execute the code in a single namespace
        exec(code, namespace)
        
        # Capture output
        results["output"] = stdout_buffer.getvalue()
        results["success"] = True
        
    except Exception as e:
        results["error"] = f"{type(e).__name__}: {str(e)}"
        results["success"] = False
        
    finally:
        # Restore original stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
    return results

def validate_code(code: str) -> Dict[str, Any]:
    """
    Validate Python code without executing it.
    
    Args:
        code: Python code to validate
        
    Returns:
        Dict containing:
            - valid: Whether code is syntactically valid (bool)
            - errors: List of syntax errors found (List[str])
            - warnings: List of potential issues (List[str])
    """
    results = {
        "valid": False,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Parse the code to check syntax
        ast.parse(code)
        results["valid"] = True
        
        # Basic code checks
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Check for potential infinite recursion
            if isinstance(node, ast.FunctionDef):
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call) and hasattr(subnode.func, 'id') and subnode.func.id == node.name:
                        if not any(isinstance(n, ast.If) for n in ast.walk(node)):
                            results["warnings"].append(f"Function {node.name} may have infinite recursion - no base case found")
            
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                results["warnings"].append("Bare except clause used - consider catching specific exceptions")
                
    except SyntaxError as e:
        results["errors"].append(f"Syntax error: {str(e)}")
    except Exception as e:
        results["errors"].append(f"Validation error: {str(e)}")
    
    return results
