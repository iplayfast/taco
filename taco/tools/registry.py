"""
TACO Tool Registry - Adapted from tools_engine.py

Manages the registration and execution of tools.
"""
import os
import sys
import inspect
import importlib.util
import json
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints
from dataclasses import dataclass
import traceback

from taco.core.config import get_config
from taco.utils.debug import debug_print

@dataclass
class ToolCall:
    """Represents a tool call with arguments and response"""
    name: str
    arguments: Dict[str, Any]
    response: Any = None

class Tool:
    """Wrapper for a callable function that can be used as a tool"""
    
    def __init__(self, func: Callable):
        """Initialize a tool from a function"""
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__ or "No description provided"
        self.type_hints = get_type_hints(func)
        self.sig = inspect.signature(func)
        self.type_map = {
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "string": str,
            "array": list,
            "object": dict
        }
        self.parameters = self._get_parameters(self.sig)
    
    def _get_parameters(self, sig: inspect.Signature) -> Dict[str, Any]:
        """Extract parameter information from function signature"""
        params = {}
        for name, param in sig.parameters.items():
            param_type = self.type_hints.get(name, Any)
            if param_type == inspect.Parameter.empty:
                param_type = Any
            
            params[name] = {
                "type": self._get_json_type(param_type),
                "description": f"Parameter {name}",
                "required": param.default == inspect.Parameter.empty
            }
        return params
    
    def _get_json_type(self, typ: type) -> str:
        """Convert Python type to JSON schema type"""
        if typ in (int, float):
            return "number"
        for key, value in self.type_map.items():
            if typ in value if isinstance(value, tuple) else typ == value:
                return key
        return "string"
    
    def convert_argument(self, name: str, value: Any) -> Any:
        """Convert argument to the correct type based on type hints"""
        target_type = self.type_hints.get(name, Any)
        
        # Handle tuple conversion
        if isinstance(value, str) and value.startswith('(') and value.endswith(')'):
            try:
                numbers = [int(x.strip()) for x in value.strip('()').split(',')]
                return tuple(numbers)
            except (ValueError, SyntaxError):
                pass
        
        # Handle special cases
        if target_type == bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'y')
            return bool(value)
        elif target_type in (int, float):
            if isinstance(value, str):
                cleaned_value = ''.join(c for c in value if c.isdigit() or c in '.-')
                return target_type(cleaned_value)
            return target_type(value)
        
        # Default case: try direct conversion
        try:
            return target_type(value)
        except (TypeError, ValueError):
            return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

class ToolRegistry:
    """Registry for tools that can be called by TACO"""
    
    def __init__(self):
        """Initialize the tool registry"""
        self.tools: Dict[str, Tool] = {}
        self._load_default_tools()
        self._load_config_tools()
    
    def _load_default_tools(self):
        """Load the default built-in tools"""
        # Import examples
        from taco.tools.examples import basic, code, explainer, parameter_collector
        
        # Inspect modules for functions
        for module in [basic, code, explainer, parameter_collector]:
            for name, func in inspect.getmembers(module, inspect.isfunction):
                self.add_tool(func)
                
    def _load_config_tools(self):
        """Load tools from paths in config"""
        config = get_config()
        paths = config.get('tools', {}).get('paths', [])
        
        for path in paths:
            try:
                self.add_tool_file(path)
            except Exception as e:
                debug_print(f"Error loading tool from {path}: {str(e)}")
    
    def add_tool(self, func: Callable) -> bool:
        """Add a tool from a function"""
        try:
            tool = Tool(func)
            self.tools[tool.name] = tool
            return True
        except Exception as e:
            debug_print(f"Error adding tool {func.__name__}: {str(e)}")
            return False
    
    def add_tool_file(self, file_path: str) -> Dict[str, Any]:
        """Add tools from a Python file"""
        result = {
            "success": False,
            "tools": [],
            "error": None
        }
        
        try:
            # Get the module name from file path
            module_name = os.path.basename(file_path).replace('.py', '')
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                result["error"] = f"Could not load module from {file_path}"
                return result
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find all functions
            functions = inspect.getmembers(module, inspect.isfunction)
            
            # Add each function as a tool
            for name, func in functions:
                if self.add_tool(func):
                    result["tools"].append(name)
            
            # Add to config
            self._add_path_to_config(file_path)
            
            result["success"] = True
            return result
            
        except Exception as e:
            result["error"] = str(e)
            debug_print(f"Error adding tool file {file_path}: {traceback.format_exc()}")
            return result
    
    def _add_path_to_config(self, path: str):
        """Add tool path to config"""
        from taco.core.config import get_config, save_config
        
        config = get_config()
        paths = config.get('tools', {}).get('paths', [])
        
        if path not in paths:
            if 'tools' not in config:
                config['tools'] = {}
            if 'paths' not in config['tools']:
                config['tools']['paths'] = []
            
            config['tools']['paths'].append(path)
            save_config(config)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools"""
        return [
            {
                "name": name,
                "description": tool.description
            }
            for name, tool in self.tools.items()
        ]
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tool"""
        tool = self.tools.get(name)
        
        if not tool:
            return None
        
        params = []
        for name, details in tool.parameters.items():
            params.append({
                "name": name,
                "type": details["type"],
                "description": details["description"],
                "required": details.get("required", False)
            })
        
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": params
        }
    
    def run_tool(self, name: str, args: List[str]) -> Any:
        """Run a tool with the provided arguments"""
        tool = self.tools.get(name)
        
        if not tool:
            return {"error": f"Tool not found: {name}"}
        
        try:
            # Convert arguments
            sig_params = list(tool.sig.parameters.keys())
            parsed_args = {}
            
            # Map positional arguments
            for i, arg in enumerate(args):
                if i < len(sig_params):
                    param_name = sig_params[i]
                    parsed_args[param_name] = tool.convert_argument(param_name, arg)
            
            # Execute the tool
            result = tool.func(**parsed_args)
            
            return result
        except Exception as e:
            debug_print(f"Error running tool {name}: {traceback.format_exc()}")
            return {"error": str(e)}