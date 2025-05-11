"""
TACO Context-Aware Tool Decorator
Makes tools automatically use context for parameter defaults
"""
import inspect
from typing import Callable, Dict, Any, List
from functools import wraps
from taco.utils.debug import debug_print

def with_context_aware_parameters(questions: Dict[str, str] = None):
    """
    Decorator that makes tools context-aware for parameter collection
    
    Args:
        questions: Dict mapping parameter names to their collection questions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get context manager
            context_manager = get_enhanced_context_manager()
            
            # Check for missing parameters and fill from context
            updated_kwargs, missing_params = context_manager.check_missing_parameters(func, kwargs)
            
            # If parameters still missing, request collection
            if missing_params:
                debug_print(f"Missing parameters for {func.__name__}: {missing_params}")
                
                # Build questions for missing parameters
                param_questions = []
                for param in missing_params:
                    if questions and param in questions:
                        param_questions.append(questions[param])
                    else:
                        # Default question format
                        param_questions.append(f"Please provide {param}:")
                
                return {
                    'status': 'needs_parameters',
                    'tool_name': func.__name__,
                    'parameters_needed': missing_params,
                    'questions': param_questions,
                    'parameter_names': missing_params,
                    'next_tool': 'collect_tool_parameters',
                    'context': {
                        'original_function': func.__name__,
                        'provided_params': kwargs,
                        'filled_params': updated_kwargs
                    }
                }
            
            # All parameters available, execute the function
            result = func(*args, **updated_kwargs)
            
            # Update context with used values (non-persistent)
            # This allows the session to remember recent values
            sig = inspect.signature(func)
            for param_name, value in updated_kwargs.items():
                if param_name in sig.parameters and value not in [None, ""]:
                    context_manager.update_parameter_default(param_name, value, persist=False)
            
            return result
        
        # Attach metadata to the wrapper
        wrapper._is_context_aware = True
        wrapper._parameter_questions = questions or {}
        wrapper._original_func = func
        
        return wrapper
    return decorator

def update_tool_descriptions(func: Callable) -> Callable:
    """Update tool descriptions to indicate context awareness"""
    if hasattr(func, '_is_context_aware'):
        # Get the original description
        if hasattr(func, '_get_tool_description'):
            original_desc = func._get_tool_description()
        else:
            original_desc = func.__doc__ or ""
        
        # Add context awareness note
        context_note = "\n\nThis tool is context-aware and will use project defaults when available."
        
        def new_description():
            return original_desc + context_note
        
        func._get_tool_description = new_description
    
    return func