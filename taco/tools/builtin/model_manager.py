"""
TACO Model Puller Tool - Handles model pulling for Ollama
"""
import ollama
from typing import Dict, Any, Optional
from taco.core.config import get_config

def pull_model(model_name: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Pull an Ollama model if it's not available.
    
    Args:
        model_name: Name of the model to pull
        confirm: Whether the user has confirmed they want to pull the model
    
    Returns:
        Dict containing the result of the operation
    """
    config = get_config()
    host = config.get('model', {}).get('host', 'http://localhost:11434')
    client = ollama.Client(host=host)
    
    # If no confirmation, ask for it
    if not confirm:
        return {
            'status': 'needs_confirmation',
            'model': model_name,
            'message': f"Model '{model_name}' is not available. Would you like to pull it? This may take some time and disk space.",
            'next_action': 'Please respond with yes/no'
        }
    
    try:
        # Check if model exists
        try:
            client.show(model_name)
            return {
                'status': 'already_exists',
                'model': model_name,
                'message': f"Model '{model_name}' is already available."
            }
        except ollama.ResponseError as e:
            if "not found" not in str(e).lower():
                raise e
        
        # Model doesn't exist, try to pull
        print(f"Pulling model '{model_name}'... This may take a while.")
        
        # Pull the model with progress updates
        progress_updates = []
        for progress in client.pull(model_name, stream=True):
            if 'status' in progress:
                progress_updates.append(progress['status'])
                print(f"Progress: {progress['status']}")
        
        return {
            'status': 'success',
            'model': model_name,
            'message': f"Successfully pulled model '{model_name}'",
            'progress': progress_updates[-5:] if progress_updates else []  # Last 5 status updates
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'model': model_name,
            'message': f"Failed to pull model '{model_name}': {str(e)}"
        }

def retry_with_model(original_tool: str, original_params: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """
    Retry a failed operation with a different or newly pulled model.
    
    Args:
        original_tool: The tool that failed due to missing model
        original_params: The parameters that were used
        model_name: The model to use for retry
    
    Returns:
        Dict containing retry instructions
    """
    # Update the model in parameters
    updated_params = original_params.copy()
    updated_params['model'] = model_name
    
    return {
        'status': 'retry_ready',
        'tool_to_retry': original_tool,
        'updated_parameters': updated_params,
        'message': f"Ready to retry {original_tool} with model '{model_name}'",
        'next_tool': original_tool
    }

def check_model_availability(model_name: str) -> Dict[str, Any]:
    """
    Check if a model is available locally or can be pulled.
    
    Args:
        model_name: Name of the model to check
    
    Returns:
        Dict containing availability information
    """
    config = get_config()
    host = config.get('model', {}).get('host', 'http://localhost:11434')
    client = ollama.Client(host=host)
    
    try:
        # Check if model exists locally
        client.show(model_name)
        return {
            'status': 'available',
            'model': model_name,
            'local': True,
            'message': f"Model '{model_name}' is available locally"
        }
    except:
        # Model not found locally, check if it's a valid model name
        # This is a simplified check - in reality, you'd want to query Ollama's model registry
        known_models = ['llama3', 'llama2', 'codellama', 'mistral', 'gemma', 'gemma2', 'vicuna', 'phi']
        
        if any(model_name.startswith(known) for known in known_models):
            return {
                'status': 'pullable',
                'model': model_name,
                'local': False,
                'message': f"Model '{model_name}' can be pulled from Ollama registry"
            }
        else:
            return {
                'status': 'not_found',
                'model': model_name,
                'local': False,
                'message': f"Model '{model_name}' is not recognized. Please check the model name."
            }

# Tool descriptions
def _get_tool_description():
    """Get description for model management tools"""
    return """Model management tools for Ollama

Available functions:
- pull_model: Pull a model from Ollama registry
- check_model_availability: Check if a model is available
- retry_with_model: Retry a failed operation with a different model
"""

def _get_usage_instructions():
    """Get usage instructions for model tools"""
    return """
Model management workflow:

1. When an operation fails due to missing model:
   - Use check_model_availability to verify the model name
   - If pullable, use pull_model to download it
   - Use retry_with_model to retry the original operation

Example workflow:
```json
// Check if model exists
{
  "tool_call": {
    "name": "check_model_availability",
    "parameters": {
      "model_name": "llama3"
    }
  }
}

// If not available but pullable, pull it
{
  "tool_call": {
    "name": "pull_model",
    "parameters": {
      "model_name": "llama3",
      "confirm": true
    }
  }
}

// Retry the original operation
{
  "tool_call": {
    "name": "retry_with_model",
    "parameters": {
      "original_tool": "create_code",
      "original_params": {...},
      "model_name": "llama3"
    }
  }
}
```
"""

# Attach descriptions to functions
pull_model._get_tool_description = _get_tool_description
pull_model._get_usage_instructions = _get_usage_instructions
check_model_availability._get_tool_description = _get_tool_description
retry_with_model._get_tool_description = _get_tool_description