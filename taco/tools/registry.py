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
    
    def get_description(self) -> str:
        """Get tool description in a standard format"""
        # Check if the function has a custom description method
        if hasattr(self.func, '_get_tool_description'):
            return self.func._get_tool_description()
        
        # Extract just the first line of the docstring
        if self.func.__doc__:
            first_line = self.func.__doc__.strip().split('\n')[0]
            return f"{self.name}: {first_line}"
        
        return f"{self.name}: No description provided"

    def get_usage_instructions(self) -> str:
        """Get specific usage instructions for this tool"""
        # Check if the function has custom usage instructions
        if hasattr(self.func, '_get_usage_instructions'):
            return self.func._get_usage_instructions()
        
        # Check if there's a special "get_usage_instructions" mode
        if 'mode' in self.parameters:
            # This tool supports get_usage_instructions mode
            try:
                result = self.func(mode="get_usage_instructions")
                if isinstance(result, dict) and 'instructions' in result:
                    return result['instructions']
            except:
                pass
        
        # Default: No special instructions
        return ""
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments"""
        # Special handling for get_usage_instructions mode
        if kwargs.get('mode') == 'get_usage_instructions':
            instructions = self.get_usage_instructions()
            if instructions:
                return {
                    'status': 'success',
                    'instructions': instructions,
                    'tool_name': self.name
                }
            else:
                return {
                    'status': 'error',
                    'message': f"Tool {self.name} does not provide usage instructions"
                }
        
        # Normal execution
        try:
            result = self.func(**kwargs)
            return result
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def convert_argument(self, name: str, value: Any) -> Any:
        """Convert argument to the correct type based on type hints"""
        target_type = self.type_hints.get(name, Any)
        
        # Handle empty string or None values - don't convert
        if value == "" or value is None:
            return value
        
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
                # Don't try to convert empty strings or special values
                if value in ["", "none", "default"]:
                    return value
                cleaned_value = ''.join(c for c in value if c.isdigit() or c in '.-')
                if cleaned_value:
                    return target_type(cleaned_value)
                return value
            return target_type(value)
        
        # Default case: return value as-is if can't convert
        if target_type == str or target_type == Any:
            return value
        
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
        # Import builtin tools with new directory structure
        from taco.tools.builtin import basic, code
        
        # Load basic tools
        for name, func in inspect.getmembers(basic, inspect.isfunction):
            if not name.startswith('_'):  # Skip private functions
                self.add_tool(func)
        
        # Load code tools
        for name, func in inspect.getmembers(code, inspect.isfunction):
            if not name.startswith('_'):  # Skip private functions
                self.add_tool(func)
        
        # Import create_code tool
        try:
            from taco.tools.builtin import create_code
            for name, func in inspect.getmembers(create_code, inspect.isfunction):
                if not name.startswith('_'):  # Skip private functions
                    self.add_tool(func)
        except ImportError:
            debug_print("create_code tool not found")
        
        # Import other builtin tools if they exist
        try:
            from taco.tools.builtin import explainer
            for name, func in inspect.getmembers(explainer, inspect.isfunction):
                if not name.startswith('_'):  # Skip private functions
                    self.add_tool(func)
        except ImportError:
            pass
        
        try:
            from taco.tools.builtin import parameter_collector
            for name, func in inspect.getmembers(parameter_collector, inspect.isfunction):
                if not name.startswith('_'):  # Skip private functions
                    self.add_tool(func)
        except ImportError:
            pass
        
        try:
            from taco.tools.builtin import save_file
            for name, func in inspect.getmembers(save_file, inspect.isfunction):
                if not name.startswith('_'):  # Skip private functions
                    self.add_tool(func)
        except ImportError:
            pass
    
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
                if not name.startswith('_') and self.add_tool(func):
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
        for param_name, details in tool.parameters.items():
            params.append({
                "name": param_name,
                "type": details["type"],
                "description": details["description"],
                "required": details.get("required", False)
            })
        
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": params,
            "usage_instructions": tool.get_usage_instructions()
        }
    
    def run_tool(self, name: str, args: List[str] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Run a tool with the provided arguments"""
        tool = self.tools.get(name)
        
        if not tool:
            return {"error": f"Tool not found: {name}"}
        
        try:
            if kwargs:
                # Use keyword arguments directly
                converted_kwargs = {}
                for param_name, param_value in kwargs.items():
                    if param_name in tool.type_hints:
                        converted_value = tool.convert_argument(param_name, param_value)
                        converted_kwargs[param_name] = converted_value
                    else:
                        converted_kwargs[param_name] = param_value
                
                result = tool.execute(**converted_kwargs)
            else:
                # Convert positional arguments
                sig_params = list(tool.sig.parameters.keys())
                parsed_args = {}
                
                if args:
                    for i, arg in enumerate(args):
                        if i < len(sig_params):
                            param_name = sig_params[i]
                            parsed_args[param_name] = tool.convert_argument(param_name, arg)
                
                result = tool.execute(**parsed_args)
            
            return result
        except Exception as e:
            debug_print(f"Error running tool {name}: {traceback.format_exc()}")
            return {"error": str(e)}