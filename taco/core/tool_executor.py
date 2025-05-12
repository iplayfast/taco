# taco/core/tool_executor.py
"""
TACO Tool Executor
Handles tool execution and parameter processing.
"""
from typing import Dict, List, Any, Optional
import traceback
import json
import inspect
from taco.utils.debug_logger import debug_logger

class ToolExecutor:
    """Handles execution of tools with parameter processing"""
    
    def __init__(self, tool_registry, context_manager, tool_stack):
        """Initialize with required components"""
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.tool_stack = tool_stack
    
    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and return results with details"""
        results = []
        
        debug_logger.log(f"Processing {len(tool_calls)} tool calls", "TOOL_EXEC")
        debug_logger.log(f"Current tool stack: {len(self.tool_stack.stack)} items", "TOOL_EXEC")
        
        if self.tool_stack.stack:
            for i, item in enumerate(self.tool_stack.stack):
                debug_logger.log(f"Stack item {i}: {item['tool']}", "TOOL_EXEC")
        
        for call in tool_calls:
            tool_name = call['tool_name']
            params = call['parameters']
            
            debug_logger.log_tool_call(tool_name, params)
            
            # Special handling for create_code tool that receives 'code' instead of 'prompt'
            if tool_name == 'create_code' and 'prompt' not in params and 'code' in params:
                debug_logger.log(f"Remapping 'code' parameter to 'prompt' for create_code tool", "TOOL_EXEC", "yellow")
                params['prompt'] = params.pop('code')
            
            # Check stack depth before executing
            if not self.tool_stack.check_depth_limit():
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': "Tool stack depth limit reached",
                    'success': False
                })
                continue
            
            # Get the tool
            tool = self.tool_registry.tools.get(tool_name)
            if not tool:
                debug_logger.log_error(f"Tool '{tool_name}' not found")
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': f"Tool '{tool_name}' not found",
                    'success': False
                })
                continue
            
            # If this is the initial tool selection, get usage instructions directly
            if not self.tool_stack.stack:
                debug_logger.log(f"Getting usage instructions for {tool_name}", "TOOL_EXEC")
                
                # Get usage instructions directly from the tool
                usage_instructions = tool.get_usage_instructions()
                debug_logger.log(f"Usage instructions length: {len(usage_instructions)}", "TOOL_EXEC")
                
                # Return the usage instructions as a result
                results.append({
                    'tool': tool_name,
                    'parameters': {'mode': 'get_usage_instructions'},
                    'result': {
                        'status': 'success',
                        'instructions': usage_instructions,
                        'tool_name': tool_name
                    },
                    'success': True
                })
                continue
            
            # Normal tool execution follows...
            try:
                # Check for missing parameters using context
                func = tool.func
                if hasattr(func, '__wrapped__'):  # Get original function if wrapped
                    func = func.__wrapped__
                
                # Log function signature for debugging
                sig = inspect.signature(func)
                debug_logger.log(f"Tool function signature: {sig}", "TOOL_EXEC")
                debug_logger.log(f"Expected parameters: {list(sig.parameters.keys())}", "TOOL_EXEC")
                
                updated_params, missing_params = self.context_manager.check_missing_parameters(func, params)
                
                debug_logger.log(f"Original params: {json.dumps(params)}", "TOOL_EXEC")
                debug_logger.log(f"Updated params: {json.dumps(updated_params)}", "TOOL_EXEC")
                
                if missing_params:
                    debug_logger.log(f"Missing params: {missing_params}", "TOOL_EXEC", "yellow")
                else:
                    debug_logger.log("No missing params", "TOOL_EXEC", "green")
                
                # Convert parameters based on tool signature
                converted_params = {}
                for param_name, param_value in updated_params.items():
                    if param_name in tool.type_hints:
                        converted_value = tool.convert_argument(param_name, param_value)
                        converted_params[param_name] = converted_value
                    else:
                        converted_params[param_name] = param_value
                
                debug_logger.log(f"Converted params: {json.dumps(converted_params)}", "TOOL_EXEC")
                
                # Execute with properly typed parameters
                result = tool.execute(**converted_params)
                
                # Log tool execution result
                if isinstance(result, dict):
                    debug_logger.log(f"Tool execution result status: {result.get('status', 'N/A')}", "TOOL_EXEC")
                    
                    if result.get('status') == 'needs_parameters':
                        debug_logger.log_success("Tool needs parameters collection!")
                        debug_logger.log(f"Questions: {result.get('questions', [])}", "TOOL_EXEC", "green")
                        debug_logger.log(f"Parameter names: {result.get('parameter_names', [])}", "TOOL_EXEC", "green")
                
                # Check if tool needs parameter collection
                if isinstance(result, dict) and result.get('status') == 'needs_parameters':
                    # Push parameter collection onto stack
                    self.tool_stack.push('collect_tool_parameters', {
                        'collecting_for': tool_name,
                        'original_params': params,
                        'questions': result.get('questions', []),
                        'parameter_names': result.get('parameter_names', [])
                    })
                    
                    debug_logger.log_stack_update("push", "collect_tool_parameters", len(self.tool_stack.stack))
                
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'result': result,
                    'success': True
                })
                
                # Update context with used parameters (non-persistent)
                for param_name, value in converted_params.items():
                    if value not in [None, ""] and param_name != 'prompt':
                        self.context_manager.update_parameter_default(param_name, value, persist=False)
                        
            except Exception as e:
                debug_logger.log_error(f"Tool execution error: {str(e)}")
                debug_logger.log_error(traceback.format_exc())
                
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': str(e),
                    'success': False
                })
        
        debug_logger.log(f"Final tool stack after execution: {len(self.tool_stack.stack)} items", "TOOL_EXEC")
        if self.tool_stack.stack:
            for i, item in enumerate(self.tool_stack.stack):
                debug_logger.log(f"Stack item {i}: {item['tool']}", "TOOL_EXEC")
        
        return results