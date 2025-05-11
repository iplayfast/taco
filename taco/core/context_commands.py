"""
TACO Context Project Commands
Handles project-related context commands
"""
from typing import List
from taco.context.enhanced_engine import get_enhanced_context_manager

def handle_context_project_command(command: str, args: List[str]) -> str:
    """Handle project-related context commands"""
    context_manager = get_enhanced_context_manager()
    
    if command == '/project':
        if not args:
            # Show current project info
            project_info = context_manager.get_project_info()
            if project_info:
                result = f"Current project: {project_info['name']}\n"
                result += f"Working directory: {project_info['workingdir']}\n"
                result += f"Language: {project_info['language']}\n"
                if project_info['defaults']:
                    result += "\nProject defaults:\n"
                    for key, value in project_info['defaults'].items():
                        result += f"  {key}: {value}\n"
                return result
            else:
                return "No active project. Use '/project new <name>' to create one."
        
        subcommand = args[0]
        
        if subcommand == 'new':
            if len(args) < 2:
                return "Usage: /project new <name> [workingdir]"
            
            project_name = args[1]
            workingdir = args[2] if len(args) > 2 else f"~/projects/{project_name}"
            
            # Additional optional parameters
            kwargs = {}
            if len(args) > 3:
                # Parse additional key=value pairs
                for arg in args[3:]:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        kwargs[key] = value
            
            success = context_manager.create_project_context(project_name, workingdir, **kwargs)
            if success:
                return f"Created project '{project_name}' in {workingdir}"
            else:
                return f"Failed to create project '{project_name}'"
        
        elif subcommand == 'switch' or subcommand == 'use':
            if len(args) < 2:
                return "Usage: /project switch <name>"
            
            project_name = args[1]
            context_name = f"project_{project_name}"
            
            # Check if project exists
            contexts = context_manager.list_contexts()
            if not any(ctx['name'] == context_name for ctx in contexts):
                return f"Project '{project_name}' not found"
            
            success = context_manager.set_active_context(context_name)
            if success:
                return f"Switched to project '{project_name}'"
            else:
                return f"Failed to switch to project '{project_name}'"
        
        elif subcommand == 'set':
            if len(args) < 3:
                return "Usage: /project set <key> <value>"
            
            key = args[1]
            value = ' '.join(args[2:])
            
            # Special handling for defaults
            if not key.endswith('_default'):
                key = f"{key}_default"
            
            context_manager.update_project_setting(key, value)
            return f"Updated project setting: {key} = {value}"
        
        elif subcommand == 'info':
            project_info = context_manager.get_project_info()
            if project_info:
                import json
                return json.dumps(project_info, indent=2)
            else:
                return "No active project"
        
        else:
            return f"Unknown project subcommand: {subcommand}"
    
    return "Unknown command"

# Add these commands to the chat command handler
def add_project_commands(command_handler):
    """Add project commands to the command handler"""
    original_handle = command_handler.handle_command
    
    def enhanced_handle_command(command: str) -> str:
        # Check for project commands first
        if command.startswith('/project'):
            parts = command.split()
            return handle_context_project_command(parts[0], parts[1:])
        
        # Fall back to original handler
        return original_handle(command)
    
    command_handler.handle_command = enhanced_handle_command