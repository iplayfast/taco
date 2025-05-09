"""
TACO Model Management - Robust version for various Ollama API formats
"""
import os
import json
from typing import List, Dict, Any, Optional
import ollama
import requests

from taco.core.config import get_config, set_config_value
from taco.utils.debug import debug_print

class ModelManager:
    """Manages Ollama model selection and interaction"""
    
    def __init__(self):
        """Initialize the model manager"""
        self.config = get_config().get('model', {})
        self.host = self.config.get('host', 'http://localhost:11434')
        self.client = ollama.Client(host=self.host)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models from Ollama using direct API call for reliability"""
        try:
            debug_print(f"Attempting to list models from Ollama at {self.host}")
            
            # Try direct API call first for reliability
            try:
                response = requests.get(f"{self.host}/api/tags")
                data = response.json()
                debug_print(f"Direct API response: {json.dumps(data)[:200]}...")
                
                models = []
                
                # Check if 'models' exists in response
                if 'models' in data and isinstance(data['models'], list):
                    for model in data['models']:
                        # Handle different possible formats
                        model_name = model.get('name', None)
                        if model_name is None and 'tag' in model:
                            model_name = model.get('tag')
                        
                        if not model_name:
                            debug_print(f"Could not find name for model: {model}")
                            continue
                            
                        size = model.get('size', model.get('modelsize', 'Unknown'))
                        modified = model.get('modified_at', model.get('modified', 'Unknown'))
                        
                        models.append({
                            'name': model_name,
                            'description': f"Size: {size}, Modified: {modified}"
                        })
                else:
                    debug_print("No 'models' field found in API response")
                
                debug_print(f"Processed {len(models)} models")
                return models
            except Exception as e:
                debug_print(f"Direct API call failed: {str(e)}")
                # Fall back to ollama client
                
            # Fallback to ollama client
            debug_print("Trying ollama client as fallback")
            response = self.client.list()
            debug_print(f"Ollama client response: {response}")
            
            models = []
            
            # Handle different possible formats
            if 'models' in response:
                for model in response['models']:
                    # Extract name from different possible locations
                    model_name = None
                    if isinstance(model, dict):
                        model_name = model.get('name', model.get('tag', None))
                    elif isinstance(model, str):
                        model_name = model
                    
                    if not model_name:
                        continue
                        
                    models.append({
                        'name': model_name,
                        'description': f"Size: {model.get('size', 'Unknown')}, Modified: {model.get('modified_at', 'Unknown')}"
                    })
            
            return models
        except Exception as e:
            debug_print(f"Error listing models: {str(e)}")
            return []
    
    def get_default_model(self) -> str:
        """Get the default model name"""
        return self.config.get('default', 'llama3')
    
    def set_default_model(self, model_name: str) -> bool:
        """Set the default model"""
        try:
            # Set in config without verification for now
            set_config_value('model.default', model_name)
            self.config['default'] = model_name
            return True
        except Exception as e:
            debug_print(f"Error setting default model: {str(e)}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model"""
        try:
            # Try direct API call
            try:
                response = requests.get(f"{self.host}/api/show?name={model_name}")
                data = response.json()
                
                if data:
                    return {
                        'name': model_name,
                        'description': f"Model information",
                        'parameters': data.get('parameters', 'Unknown'),
                        'context_length': data.get('context_length', 'Unknown'),
                    }
            except Exception:
                pass
                
            # Fallback to simple info
            return {
                'name': model_name,
                'description': f"Model: {model_name}",
                'parameters': 'Unknown',
                'context_length': 'Unknown',
            }
        except Exception as e:
            debug_print(f"Error getting model info: {str(e)}")
            return None
    
    def generate_response(self, model_name: str, messages: List[Dict[str, str]]) -> str:
        """Generate a response from the model"""
        try:
            debug_print(f"Generating response with model: {model_name}")
            debug_print(f"Messages: {json.dumps(messages)[:200]}...")
            
            response = self.client.chat(
                model=model_name,
                messages=messages
            )
            
            debug_print(f"Response type: {type(response)}")
            
            # Handle various response formats
            if isinstance(response, dict):
                # New format
                if 'message' in response and isinstance(response['message'], dict):
                    return response['message'].get('content', str(response))
                # Another possible format
                elif 'response' in response:
                    return response['response']
                # Direct content
                elif 'content' in response:
                    return response['content']
            
            # Fallback: convert to string
            return str(response)
        except Exception as e:
            debug_print(f"Error generating response: {str(e)}")
            return f"Error: Could not generate response - {str(e)}"
