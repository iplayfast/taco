"""
TACO Chat Session Management
Main orchestrator for chat sessions, coordinating between components.
Enhanced with context-aware parameter handling.
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
        
        # Add project command handling
        self._add_project_commands()
        
        # History file path for prompt_toolkit
        history_dir = os.path.expanduser("~/.config/taco")
        os.makedirs(history_dir, exist_ok=True)
        self.history_file = os.path.join(history_dir, "chat_history")
    
    def _add_project_commands(self):
        """Add project commands to the command handler"""
        original_handle = self.command_handler.handle_command
        
        def enhanced_handle_command(command: str) -> str:
            # Check for project commands first
            if command.startswith('/project'):
                parts = command.split()
                return self._handle_project_command(parts[0], parts[1:])
            
            # Fall back to original handler
            return original_handle(command)
        
        self.command_handler.handle_command = enhanced_handle_command
    
    def _handle_project_command(self, command: str, args: List[str]) -> str:
        """Handle project-related commands"""
        if command == '/project':
            if not args:
                # Show current project info
                project_info = self.context_manager.get_project_info()
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
                    return "No active project. Use '/project new <n>' to create one."
            
            subcommand = args[0]
            
            if subcommand == 'new':
                if len(args) < 2:
                    return "Usage: /project new <n> [workingdir]"
                
                project_name = args[1]
                workingdir = args[2] if len(args) > 2 else f"~/projects/{project_name}"
                
                success = self.context_manager.create_project_context(project_name, workingdir)
                if success:
                    return f"Created project '{project_name}' in {workingdir}"
                else:
                    return f"Failed to create project '{project_name}'"
            
            elif subcommand == 'switch' or subcommand == 'use':
                if len(args) < 2:
                    return "Usage: /project switch <n>"
                
                project_name = args[1]
                context_name = f"project_{project_name}"
                
                success = self.context_manager.set_active_context(context_name)
                if success:
                    return f"Switched to project '{project_name}'"
                else:
                    return f"Project '{project_name}' not found"
            
            elif subcommand == 'set':
                if len(args) < 3:
                    return "Usage: /project set <key> <value>"
                
                key = args[1]
                value = ' '.join(args[2:])
                
                # Special handling for defaults
                if not key.endswith('_default'):
                    key = f"{key}_default"
                
                self.context_manager.update_project_setting(key, value)
                return f"Updated project setting: {key} = {value}"
            
            else:
                return f"Unknown project subcommand: {subcommand}"
        
        return "Unknown command"
    
    def _get_tools_prompt(self) -> str:
        """Generate a prompt that describes available tools to the LLM"""
        tools_description = """Find the best tool to match the question. If no tool matches well, answer the question directly.

    Available tools:
    """
        
        for tool_name, tool in self.tool_registry.tools.items():
            tools_description += f"- {tool.get_description()}\n"
        
        tools_description += """
    To use a tool, specify it in JSON format:
    ```json
    {
    "tool_call": {
        "name": "<tool_name>",
        "parameters": {
            // tool-specific parameters
        }
    }
    }
    ```
    
    When selecting a tool for the user's request:
    1. Choose the most appropriate tool
    2. The system will provide usage instructions
    3. Apply the tool to the user's original request using those instructions
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
            
            # Get the tool
            tool = self.tool_registry.tools.get(tool_name)
            if not tool:
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': f"Tool '{tool_name}' not found",
                    'success': False
                })
                continue
            
            # NEW: If this is the initial tool selection, get usage instructions directly
            if not self.tool_stack.stack:
                # Get usage instructions directly from the tool
                usage_instructions = tool.get_usage_instructions()
                
                # REMOVED: Push tool onto stack - this will be handled by process_tool_result
                # self.tool_stack.push(tool_name, {'status': 'initialized', 'instructions': usage_instructions})
                
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
                
                updated_params, missing_params = self.context_manager.check_missing_parameters(func, params)
                
                # Convert parameters based on tool signature
                converted_params = {}
                for param_name, param_value in updated_params.items():
                    if param_name in tool.type_hints:
                        converted_value = tool.convert_argument(param_name, param_value)
                        converted_params[param_name] = converted_value
                    else:
                        converted_params[param_name] = param_value
                
                # Execute with properly typed parameters
                result = tool.execute(**converted_params)
                
                # Check if tool needs parameter collection
                if isinstance(result, dict) and result.get('status') == 'needs_parameters':
                    # Push parameter collection onto stack
                    self.tool_stack.push('collect_tool_parameters', {
                        'collecting_for': tool_name,
                        'original_params': params,
                        'questions': result.get('questions', []),
                        'parameter_names': result.get('parameter_names', [])
                    })
                
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
        
        # For the initial tool selection, modify the user's question
        modified_history = self.history.copy()
        if not self.tool_stack.stack and modified_history:  # Only on initial call
            last_message = modified_history[-1]
            if last_message["role"] == "user":
                # Modify the question to force tool selection
                modified_history[-1] = {
                    "role": "user", 
                    "content": f"Select the best tool to handle this request: {last_message['content']}"
                }
        
        messages.extend(modified_history)
        
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
            console.print(f"[blue]DEBUG: Found {len(tool_calls)} tool calls[/blue]")
            # Execute tool calls - no need to force usage instructions
            tool_results = self._execute_tool_calls(tool_calls)
            #debug check
            if not tool_results:
                console.print("[red]DEBUG: No tool results returned![/red]")
            else:
                console.print(f"[green]DEBUG: Got {len(tool_results)} tool results[/green]")

            for i, result in enumerate(tool_results):
                console.print(f"[cyan]DEBUG: Result {i+1}:[/cyan] {result['tool']} - Success: {result['success']}")
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
            
            # Check if we just got usage instructions
            got_usage_instructions = False
            for result in tool_results:
                if (result.get('success') and 
                    isinstance(result.get('result'), dict) and 
                    result['result'].get('status') == 'success' and 
                    'instructions' in result['result']):
                    got_usage_instructions = True
                    break
            
            # Remove tool call blocks from the response
            response_without_tools = self.message_handler.strip_tool_calls_from_response(cleaned_response, tool_calls)
            
            # Add the response (without tool calls) to history
            self.history.append({"role": "assistant", "content": cleaned_response})
            
            # Add tool results as context
            if tool_results_text:
                if got_usage_instructions and self.tool_stack.original_prompt:
                    # Special handling for post-usage-instructions
                    tool_context = f"""The tool has provided its usage instructions. 

Now you should use the {tool_results[0]['tool']} tool to handle the user's original request: "{self.tool_stack.original_prompt}"

Follow the usage instructions you just received, and apply them to create: "{self.tool_stack.original_prompt}"

Tool results:
{tool_results_text}"""
                else:
                    # Normal tool results handling
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
        display_system_message("Debug: OFF (use /debug on to enable)")
        
        # Check for active project
        project_info = self.context_manager.get_project_info()
        if project_info:
            display_system_message(f"Active project: {project_info['name']} ({project_info['workingdir']})")
        else:
            display_system_message("No active project. Use /project new <n> to create one.")
        
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