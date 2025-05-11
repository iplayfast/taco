"""
TACO Command Handler
Handles chat commands (e.g., /help, /status, /clear).
Enhanced with project commands and simplified debug command.
"""
from typing import Optional

class CommandHandler:
    """Handles slash commands in the chat interface"""
    
    def __init__(self, chat_session):
        """Initialize with reference to chat session"""
        self.chat = chat_session
    
    def handle_command(self, command: str) -> str:
        """Handle a chat command"""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == '/help':
            return self._help_command()
        elif cmd == '/status':
            return self._status_command()
        elif cmd == '/cancel':
            return self._cancel_command()
        elif cmd == '/debug':
            return self._debug_command(cmd_parts)
        elif cmd == '/model':
            return self._model_command(cmd_parts)
        elif cmd == '/clear':
            return self._clear_command()
        elif cmd == '/tools':
            return self._tools_command()
        elif cmd == '/context':
            return self._context_command()
        elif cmd == '/tool':
            return self._tool_info_command(cmd_parts)
        elif cmd == '/list':
            return self._list_command(cmd_parts)
        elif cmd == '/project':
            # This will be handled by the enhanced chat session
            return f"Project command should be handled by chat session"
        else:
            return f"Unknown command: {cmd}"
    
    def _help_command(self) -> str:
        """Show help message"""
        return """
Available commands:
/help - Show this help message
/bye - Exit the chat session (also: /exit, /quit)
/debug [on|off] - Turn debug mode on or off
/model [name] - Show or switch the current model
/clear - Clear the chat history and tool stack
/tools - List available tools
/tool <n> - Show detailed information about a specific tool
/context - Show active context
/list model - List all available models from Ollama
/list tools - List all registered TACO tools
/status - Show current tool stack and workflow status
/cancel - Cancel current tool workflow
/project - Project management commands
  /project new <n> [dir] - Create a new project
  /project switch <n> - Switch to a project
  /project set <key> <value> - Set a project setting
  /project info - Show project information

Debug mode: """ + ("ON" if self.chat.debug_mode else "OFF")
    
    def _status_command(self) -> str:
        """Show tool stack status"""
        return self.chat.tool_stack.format_stack()
    
    def _cancel_command(self) -> str:
        """Cancel current tool workflow"""
        if self.chat.tool_stack.stack:
            self.chat.tool_stack.clear()
            return "Tool workflow cancelled."
        else:
            return "No active tool workflow to cancel."
    
    def _debug_command(self, cmd_parts: list) -> str:
        """Turn debug mode on or off"""
        if len(cmd_parts) > 1:
            mode = cmd_parts[1].lower()
            if mode == 'on':
                self.chat.debug_mode = True
                return "Debug mode ON - you'll see detailed communication trees"
            elif mode == 'off':
                self.chat.debug_mode = False
                return "Debug mode OFF"
            else:
                return "Invalid debug setting. Use: /debug on or /debug off"
        else:
            return f"Debug mode is {'ON' if self.chat.debug_mode else 'OFF'}. Use /debug on or /debug off to change."
    
    def _model_command(self, cmd_parts: list) -> str:
        """Show or switch the current model"""
        if len(cmd_parts) > 1:
            model_name = cmd_parts[1]
            if self.chat.model_manager.set_default_model(model_name):
                self.chat.model_name = model_name
                return f"Switched to model: {model_name}"
            else:
                return f"Error: Model '{model_name}' not found"
        else:
            return f"Current model: {self.chat.model_name}"
    
    def _clear_command(self) -> str:
        """Clear chat history and tool stack"""
        self.chat.history = []
        self.chat.tool_stack.clear()
        return "Chat history and tool stack cleared"
    
    def _tools_command(self) -> str:
        """List available tools"""
        tools = self.chat.tool_registry.list_tools()
        result = "Available tools:\n"
        for tool in tools:
            result += f"• {tool['name']}\n"
        return result
    
    def _context_command(self) -> str:
        """Show active context"""
        active = self.chat.context_manager.get_active_context()
        if active:
            return f"Active context: {active}"
        else:
            return "No active context"
    
    def _tool_info_command(self, cmd_parts: list) -> str:
        """Show detailed information about a specific tool"""
        if len(cmd_parts) < 2:
            return "Usage: /tool <tool_name>"
        
        tool_name = cmd_parts[1]
        tool_info = self.chat.tool_registry.get_tool_info(tool_name)
        
        if tool_info:
            result = f"Tool: {tool_info['name']}\n"
            result += f"Description: {tool_info['description']}\n\n"
            result += "Parameters:\n"
            for param in tool_info['parameters']:
                required_str = " (required)" if param.get('required', False) else ""
                result += f"• {param['name']} ({param['type']}){required_str} - {param['description']}\n"
            
            # Add usage instructions if available
            if tool_info.get('usage_instructions'):
                result += f"\nUsage Instructions:\n{tool_info['usage_instructions']}"
            
            return result
        else:
            return f"Error: Tool '{tool_name}' not found"
    
    def _list_command(self, cmd_parts: list) -> str:
        """List models or tools"""
        if len(cmd_parts) < 2:
            return "Please specify what to list. Options: 'model' or 'tools'"
        
        list_type = cmd_parts[1].lower()
        
        if list_type == 'model':
            models = self.chat.model_manager.list_models()
            if not models:
                return "No models found. Make sure Ollama is running."
            
            result = "Available Ollama models:\n"
            for model in models:
                result += f"• {model['name']} - {model['description']}\n"
            return result
        
        elif list_type == 'tools':
            tools = self.chat.tool_registry.list_tools()
            if not tools:
                return "No tools registered."
            
            result = "Registered TACO tools:\n"
            for tool in tools:
                result += f"• {tool['name']} - {tool['description']}\n"
            return result
        
        else:
            return f"Unknown list type: {list_type}. Options are: 'model' or 'tools'"