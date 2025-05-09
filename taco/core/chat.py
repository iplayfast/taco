"""
TACO Chat Session Management
"""
import os
import sys
import json
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from taco.core.model import ModelManager
from taco.tools.registry import ToolRegistry
from taco.context.engine import ContextManager
from taco.utils.display import display_thinking, display_system_message

console = Console()

class ChatSession:
    """Manages interactive chat sessions with the LLM"""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize chat session"""
        self.model_manager = ModelManager()
        self.tool_registry = ToolRegistry()
        self.context_manager = ContextManager()
        
        # Set model
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = self.model_manager.get_default_model()
        
        # Initialize history
        self.history = []
        
        # History file path for prompt_toolkit
        history_dir = os.path.expanduser("~/.config/taco")
        os.makedirs(history_dir, exist_ok=True)
        self.history_file = os.path.join(history_dir, "chat_history")
    
    def ask(self, question: str) -> str:
        """Ask a question to the model"""
        # Check if the question is a command
        if question.startswith('/'):
            return self._handle_command(question)
        
        # Add to history
        self.history.append({"role": "user", "content": question})
        
        # Check if the question requires a tool
        tool_result = self._check_for_tool_usage(question)
        if tool_result:
            return tool_result
        
        # Get active context
        context = self.context_manager.get_active_context_content()
        
        # Prepare message with context
        messages = self.history.copy()
        if context:
            system_message = {"role": "system", "content": context}
            messages.insert(0, system_message)
        
        # Display thinking animation
        with display_thinking():
            # Call Ollama API
            response = self.model_manager.generate_response(
                self.model_name, 
                messages
            )
        
        # Add to history
        self.history.append({"role": "assistant", "content": response})
        
        return response
    
    def start_interactive(self, save_path: Optional[str] = None):
        """Start an interactive chat session"""
        # Create prompt session with history
        session = PromptSession(history=FileHistory(self.history_file))
        
        # Display welcome message
        display_system_message(f"Chat session started with model: {self.model_name}")
        display_system_message("Type /help for commands, /exit to quit")
        
        try:
            while True:
                # Get user input
                user_input = session.prompt("\n[You]: ").strip()
                
                # Check for exit command
                if user_input.lower() in ['/exit', '/quit', '/q']:
                    break
                
                # Skip empty inputs
                if not user_input:
                    continue
                
                # Process the input
                response = self.ask(user_input)
                
                # Print the response
                console.print(f"\n[Assistant]: {response}")
        except KeyboardInterrupt:
            pass
        finally:
            # Save history if requested
            if save_path:
                self.save_history(save_path)
                display_system_message(f"Chat history saved to {save_path}")
            
            display_system_message("Chat session ended")
    
    def save_history(self, file_path: str):
        """Save chat history to a file"""
        with open(file_path, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def load_history(self, file_path: str):
        """Load chat history from a file"""
        try:
            with open(file_path, 'r') as f:
                self.history = json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading history: {str(e)}[/red]")
    
    def _handle_command(self, command: str) -> str:
        """Handle chat commands"""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == '/help':
            return """
Available commands:
/help - Show this help message
/exit, /quit - Exit the chat session
/model [name] - Show or switch the current model
/clear - Clear the chat history
/tools - List available tools
/context - Show active context
"""
        elif cmd == '/model':
            if len(cmd_parts) > 1:
                model_name = cmd_parts[1]
                if self.model_manager.set_default_model(model_name):
                    self.model_name = model_name
                    return f"Switched to model: {model_name}"
                else:
                    return f"Error: Model '{model_name}' not found"
            else:
                return f"Current model: {self.model_name}"
        
        elif cmd == '/clear':
            self.history = []
            return "Chat history cleared"
        
        elif cmd == '/tools':
            tools = self.tool_registry.list_tools()
            result = "Available tools:\n"
            for tool in tools:
                result += f"• {tool['name']} - {tool['description']}\n"
            return result
            
        elif cmd == '/context':
            active = self.context_manager.get_active_context()
            if active:
                return f"Active context: {active}"
            else:
                return "No active context"
        
        return f"Unknown command: {cmd}"
    
    def _check_for_tool_usage(self, question: str) -> Optional[str]:
        """Check if the question should be routed to a tool"""
        # Simple pattern matching - this could be enhanced with LLM-based detection
        if question.startswith('/tools run '):
            parts = question.split(' ', 3)
            if len(parts) >= 4:
                tool_name = parts[2]
                args = parts[3].split()
                result = self.tool_registry.run_tool(tool_name, args)
                return f"Tool {tool_name} result: {result}"
        
        return None
