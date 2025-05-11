"""
TACO Chat Session Management
Main orchestrator for chat sessions, coordinating between components.
"""
import os
import json
from typing import Optional, Dict, List, Any
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from taco.core.model import ModelManager
from taco.tools.registry import ToolRegistry
from taco.context.engine import ContextManager
from taco.utils.display import display_thinking, display_system_message

# Import new modules
from taco.core.tool_stack import ToolStack
from taco.core.message_handler import MessageHandler
from taco.core.command_handler import CommandHandler
from taco.core.debug_display import DebugDisplay

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
        
        # Session modes
        self.debug_mode = False
        
        # Initialize components
        self.tool_stack = ToolStack()
        self.message_handler = MessageHandler()
        self.command_handler = CommandHandler(self)
        self.debug_display = DebugDisplay(self.message_handler)
        
        # History file path for prompt_toolkit
        history_dir = os.path.expanduser("~/.config/taco")
        os.makedirs(history_dir, exist_ok=True)
        self.history_file = os.path.join(history_dir, "chat_history")
    
    def _get_tools_prompt(self) -> str:
        """Generate a prompt that describes available tools to the LLM"""
        tools = self.tool_registry.list_tools()
        if not tools:
            return ""
        
        tools_description = """You have access to various tools to help answer questions.

Available tools:
"""
    
        for tool_name, tool in self.tool_registry.tools.items():
            tools_description += f"\n{tool.get_description()}"
            
            # Add usage instructions if available
            usage_instructions = tool.get_usage_instructions()
            if usage_instructions:
                tools_description += f"\nUsage Instructions:\n{usage_instructions}\n"
        
        tools_description += """
Tool call format:
```json
{
  "tool_call": {
    "name": "tool_name",
    "parameters": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}
```

When you need to use a tool:
1. First check if the tool provides usage instructions by calling it with mode="get_usage_instructions"
2. Follow the specific workflow described in the usage instructions
3. Use collect_tool_parameters when you need to gather information from the user
4. Maintain context about which tool you're working with throughout the workflow

Remember: Tools may require multiple steps. Follow their usage instructions carefully.
"""
        return tools_description

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and return results with details"""
        results = []
        
        for call in tool_calls:
            tool_name = call['tool_name']
            params = call['parameters']
            
            # Check stack depth before executing
            if not self.tool_stack.check_depth_limit():
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': "Tool stack depth limit reached",
                    'success': False
                })
                continue
            
            # Get the tool to properly convert parameters
            tool = self.tool_registry.tools.get(tool_name)
            if not tool:
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': f"Tool '{tool_name}' not found",
                    'success': False
                })
                continue
            
            try:
                # Convert parameters based on tool signature
                converted_params = {}
                for param_name, param_value in params.items():
                    if param_name in tool.type_hints:
                        converted_value = tool.convert_argument(param_name, param_value)
                        converted_params[param_name] = converted_value
                    else:
                        converted_params[param_name] = param_value
                
                # Execute with properly typed parameters
                result = tool.execute(**converted_params)
                
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'result': result,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def ask(self, question: str) -> str:
        """Ask a question to the model"""
        # Check if the question is a command
        if question.startswith('/'):
            return self.command_handler.handle_command(question)
        
        # Check for context switch
        if self.tool_stack.is_context_switch(question):
            console.print("[yellow]Context switch detected. Abandoning current tool workflow.[/yellow]")
            self.tool_stack.clear()
        
        # Check for empty response during tool workflow
        if not question and self.tool_stack.stack:
            cancel_response = self.tool_stack.handle_empty_response()
            if cancel_response:
                return cancel_response
        
        # If this is the start of a new workflow, save the original prompt
        if not self.tool_stack.stack and question:
            self.tool_stack.set_original_prompt(question)
        
        # Check for manual tool usage
        tool_result = self._check_for_tool_usage(question)
        if tool_result:
            return tool_result
        
        # Add to history
        self.history.append({"role": "user", "content": question})
        
        # Get active context
        context = self.context_manager.get_active_context_content()
        
        # Prepare system message with tools description and tool stack context
        tools_prompt = self._get_tools_prompt()
        tool_stack_context = self.tool_stack.get_system_context()
        system_content = ""
        
        if context:
            system_content += context + "\n\n"
        
        if tools_prompt:
            system_content += tools_prompt
        
        if tool_stack_context:
            system_content += tool_stack_context
        
        # Prepare messages
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        
        messages.extend(self.history)
        
        # Display thinking animation
        with display_thinking():
            # Call Ollama API
            response = self.model_manager.generate_response(
                self.model_name, 
                messages
            )
        
        # Clean up the response for processing
        cleaned_response = self.message_handler.clean_response_content(response)
        
        # Check for tool calls in the response
        tool_calls = self.message_handler.parse_tool_calls(cleaned_response)
        tool_results = []
        
        if tool_calls:
            # Execute tool calls
            tool_results = self._execute_tool_calls(tool_calls)
            
            # Process tool results and update stack
            for i, result in enumerate(tool_results):
                tool_name = result['tool']
                params = result['parameters']
                success = result['success']
                tool_result = result.get('result', {})
                
                # Let the tool stack process the result
                self.tool_stack.process_tool_result(tool_name, tool_result, success)
            
            # Format results for display
            tool_results_text = self.message_handler.format_tool_results(tool_results)
            
            # Remove tool call blocks from the response
            response_without_tools = self.message_handler.strip_tool_calls_from_response(cleaned_response, tool_calls)
            
            # Add the response (without tool calls) to history
            self.history.append({"role": "assistant", "content": cleaned_response})
            
            # Add tool results as context
            if tool_results_text:
                tool_context = f"The following tool was executed:\n{tool_results_text}\n\nPlease provide a natural language response explaining these results to the user."
                self.history.append({"role": "system", "content": tool_context})
                
                # Get another response from the model to interpret the results
                interpretation_messages = []
                if system_content:
                    interpretation_messages.append({"role": "system", "content": system_content})
                interpretation_messages.extend(self.history)
                
                with display_thinking():
                    interpretation_response = self.model_manager.generate_response(
                        self.model_name, 
                        interpretation_messages
                    )
                
                cleaned_interpretation = self.message_handler.clean_response_content(interpretation_response)
                
                # Add the interpretation to history
                self.history.append({"role": "assistant", "content": cleaned_interpretation})
                
                # Show debug tree if in debug mode
                if self.debug_mode:
                    self.debug_display.display_debug_tree(question, messages, response, 
                                                         tool_calls, tool_results, self.tool_stack)
                
                # Return the natural language response without JSON in normal mode
                if response_without_tools:
                    # Combine the original response (without JSON) with the interpretation
                    return response_without_tools + "\n\n" + cleaned_interpretation
                else:
                    return cleaned_interpretation
            else:
                # No tool results, just return cleaned response without JSON
                if self.debug_mode:
                    self.debug_display.display_debug_tree(question, messages, response, 
                                                         tool_calls, tool_results, self.tool_stack)
                return response_without_tools
        else:
            # No tool calls, normal response
            self.history.append({"role": "assistant", "content": cleaned_response})
            
            # Show debug tree if in debug mode
            if self.debug_mode:
                self.debug_display.display_debug_tree(question, messages, response, 
                                                     tool_calls, tool_results, self.tool_stack)
            
            return cleaned_response

    def start_interactive(self, save_path: Optional[str] = None):
        """Start an interactive chat session"""
        # Create prompt session with history
        session = PromptSession(history=FileHistory(self.history_file))
        
        # Display welcome message
        display_system_message(f"Chat session started with model: {self.model_name}")
        display_system_message("Type /help for commands, /bye to quit")
        display_system_message("Mode: Normal (use /mode debug for debug mode)")
        
        try:
            while True:
                # Get user input
                user_input = session.prompt("\n[You]: ").strip()
                
                # Check for exit command
                if user_input.lower() in ['/bye', '/exit', '/quit', '/q']:
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
            
            display_system_message("Chat session ended. Goodbye!")
    
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
    
    def _check_for_tool_usage(self, question: str) -> Optional[str]:
        """Check if the question should be routed to a tool"""
        # Manual tool invocation still supported
        if question.startswith('/tools run '):
            parts = question.split(' ', 3)
            if len(parts) >= 4:
                tool_name = parts[2]
                args = parts[3].split()
                result = self.tool_registry.run_tool(tool_name, args)
                return f"Tool {tool_name} result: {json.dumps(result, indent=2)}"
        
        return None