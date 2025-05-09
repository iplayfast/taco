"""
TACO Context Engine - Simplified from original engine.py
"""
import os
import json
from typing import Dict, Any, Optional, List
from taco.context.template import ContextTemplate
from taco.core.config import get_config, save_config

class ContextManager:
    """Manages context templates and their application"""
    
    def __init__(self):
        """Initialize the context manager"""
        self.config = get_config().get('context', {})
        self.contexts: Dict[str, ContextTemplate] = {}
        self._load_contexts()
    
    def _get_contexts_path(self) -> str:
        """Get the path to the contexts directory"""
        config_dir = os.path.expanduser("~/.config/taco")
        contexts_dir = os.path.join(config_dir, "contexts")
        os.makedirs(contexts_dir, exist_ok=True)
        return contexts_dir
    
    def _load_contexts(self):
        """Load contexts from the contexts directory"""
        contexts_dir = self._get_contexts_path()
        
        # Load each JSON file in the contexts directory
        for filename in os.listdir(contexts_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(contexts_dir, filename), 'r') as f:
                        data = json.load(f)
                        
                    name = os.path.splitext(filename)[0]
                    template = data.get('template', '')
                    variables = data.get('variables', {})
                    
                    self.contexts[name] = ContextTemplate(template, variables)
                except Exception as e:
                    print(f"Error loading context {filename}: {str(e)}")
    
    def create_context(self, name: str, template: str) -> bool:
        """Create a new context template"""
        try:
            # Create an empty template
            self.contexts[name] = ContextTemplate(template, {})
            
            # Save to file
            self._save_context(name)
            return True
        except Exception as e:
            print(f"Error creating context: {str(e)}")
            return False
    
    def _save_context(self, name: str):
        """Save a context to file"""
        context = self.contexts.get(name)
        if not context:
            return
        
        contexts_dir = self._get_contexts_path()
        filename = os.path.join(contexts_dir, f"{name}.json")
        
        with open(filename, 'w') as f:
            json.dump({
                'template': context.template,
                'variables': context.variables
            }, f, indent=2)
    
    def list_contexts(self) -> List[Dict[str, str]]:
        """List all available contexts"""
        return [
            {
                'name': name,
                'description': self._get_context_description(context)
            }
            for name, context in self.contexts.items()
        ]
    
    def _get_context_description(self, context: ContextTemplate) -> str:
        """Generate a description for a context"""
        # Extract first line as description
        lines = context.template.strip().split('\n')
        if lines:
            return lines[0]
        return "Empty context"
    
    def get_active_context(self) -> Optional[str]:
        """Get the name of the active context"""
        return self.config.get('active')
    
    def set_active_context(self, name: str) -> bool:
        """Set the active context"""
        if name not in self.contexts:
            return False
        
        # Update config
        from taco.core.config import set_config_value
        set_config_value('context.active', name)
        self.config['active'] = name
        return True
    
    def get_active_context_content(self) -> Optional[str]:
        """Get the content of the active context"""
        active = self.get_active_context()
        if not active or active not in self.contexts:
            return None
        
        context = self.contexts[active]
        return context.generate()
    
    def add_to_context(self, name: str, content: str) -> bool:
        """Add content to a context variable"""
        if name not in self.contexts:
            return False
        
        context = self.contexts[name]
        
        # For now, simply add to the first variable
        if not context.variables:
            context.variables['content'] = content
        else:
            key = list(context.variables.keys())[0]
            context.variables[key] = content
        
        # Save to file
        self._save_context(name)
        return True
