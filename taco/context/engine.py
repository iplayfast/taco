"""
TACO Context Engine - Enhanced with parameter management
"""
import os
import json
import inspect
from typing import Dict, Any, Optional, List, Callable
from taco.context.template import ContextTemplate
from taco.core.config import get_config, save_config
from taco.utils.debug import debug_print

class ContextManager:
    """Manages context templates and their application with parameter support"""
    
    def __init__(self):
        """Initialize the context manager"""
        self.config = get_config().get('context', {})
        self.contexts: Dict[str, ContextTemplate] = {}
        self.parameter_defaults: Dict[str, Any] = {}
        self._load_contexts()
        self._load_default_contexts()
        self._load_parameter_defaults()
    
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
    
    def _load_default_contexts(self):
        """Load default context templates from the defaults directory"""
        try:
            from taco.context.defaults import chat, code
            
            # Load chat contexts
            chat_contexts = chat.get_default_chat_context()
            for name, data in chat_contexts.items():
                if name not in self.contexts:  # Don't override user configs
                    self.contexts[name] = ContextTemplate(
                        data['template'],
                        data['variables']
                    )
            
            # Load code contexts  
            code_contexts = code.get_default_code_context()
            for name, data in code_contexts.items():
                if name not in self.contexts:  # Don't override user configs
                    self.contexts[name] = ContextTemplate(
                        data['template'],
                        data['variables']
                    )
        except ImportError as e:
            debug_print(f"Could not load default contexts: {str(e)}")
    
    def _load_parameter_defaults(self):
        """Load parameter defaults from active context"""
        self.parameter_defaults = {}
        active_context = self.get_active_context()
        
        if active_context and active_context in self.contexts:
            context = self.contexts[active_context]
            # Extract parameter defaults from context variables
            for key, value in context.variables.items():
                if key.endswith('_default'):
                    param_name = key[:-8]  # Remove '_default' suffix
                    self.parameter_defaults[param_name] = value
                    debug_print(f"Loaded parameter default: {param_name} = {value}")
    
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
        
        # Reload parameter defaults
        self._load_parameter_defaults()
        
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
    
    # Enhanced methods for parameter management
    def get_parameter_default(self, param_name: str) -> Optional[Any]:
        """Get default value for a parameter from context"""
        return self.parameter_defaults.get(param_name)
    
    def update_parameter_default(self, param_name: str, value: Any, persist: bool = True):
        """Update a parameter default in the active context"""
        self.parameter_defaults[param_name] = value
        
        if persist:
            active_context = self.get_active_context()
            if active_context and active_context in self.contexts:
                context = self.contexts[active_context]
                context.variables[f"{param_name}_default"] = value
                self._save_context(active_context)
                debug_print(f"Persisted parameter default: {param_name} = {value}")
    
    def create_project_context(self, project_name: str, workingdir: str, **kwargs) -> bool:
        """Create a project-specific context"""
        template = """Project: {project_name}
Working Directory: {workingdir}
Language: {language}
Style: {style}

This is a {project_type} project.
Default parameters are configured for this project.
"""
        
        variables = {
            "project_name": project_name,
            "workingdir": workingdir,
            "language": kwargs.get("language", "Python"),
            "style": kwargs.get("style", "Clean and efficient"),
            "project_type": kwargs.get("project_type", "general"),
            # Parameter defaults
            "workingdir_default": workingdir,
            "requirements_default": kwargs.get("requirements", "requirements.txt"),
            "model_default": kwargs.get("model", "llama3")
        }
        
        # Add any additional parameter defaults from kwargs
        for key, value in kwargs.items():
            if key.endswith('_default') and key not in variables:
                variables[key] = value
        
        context_name = f"project_{project_name}"
        self.contexts[context_name] = ContextTemplate(template, variables)
        self._save_context(context_name)
        
        # Set as active context
        self.set_active_context(context_name)
        
        return True
    
    def update_project_setting(self, key: str, value: Any):
        """Update a setting in the active project context"""
        active_context = self.get_active_context()
        if active_context and active_context in self.contexts:
            context = self.contexts[active_context]
            context.variables[key] = value
            
            # Update parameter defaults cache
            if key.endswith('_default'):
                param_name = key[:-8]
                self.parameter_defaults[param_name] = value
            
            self._save_context(active_context)
            debug_print(f"Updated project setting: {key} = {value}")
    
    def get_project_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the active project context"""
        active_context = self.get_active_context()
        if active_context and active_context.startswith('project_'):
            context = self.contexts[active_context]
            return {
                'name': context.variables.get('project_name'),
                'workingdir': context.variables.get('workingdir'),
                'language': context.variables.get('language'),
                'defaults': {k[:-8]: v for k, v in context.variables.items() 
                           if k.endswith('_default')}
            }
        return None
    
    def check_missing_parameters(self, func: Callable, kwargs: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
        """
        Check for missing parameters and fill from context
        Returns: (updated kwargs, list of still missing parameters)
        """
        sig = inspect.signature(func)
        missing_params = []
        updated_kwargs = kwargs.copy()
        
        for param_name, param in sig.parameters.items():
            # Skip *args and **kwargs
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
                
            # Check if parameter is missing or empty
            if param_name not in kwargs or kwargs[param_name] in [None, ""]:
                # Try to get default from context
                default_value = self.get_parameter_default(param_name)
                
                if default_value is not None:
                    updated_kwargs[param_name] = default_value
                    debug_print(f"Using context default for {param_name}: {default_value}")
                elif param.default == param.empty:  # Required parameter
                    missing_params.append(param_name)
        
        return updated_kwargs, missing_params