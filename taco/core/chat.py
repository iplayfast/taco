"""
TACO Chat Session Management
Main orchestrator for chat sessions, coordinating between components.
Enhanced with context-aware parameter handling and comprehensive debugging.
"""
import os
import json
import sys
from typing import Optional, Dict, List, Any
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from taco.core.model import ModelManager
from taco.tools.registry import ToolRegistry
from taco.context.engine import ContextManager
from taco.utils.display import display_thinking, display_system_message
from taco.utils.debug_logger import debug_logger

# Import core components
from taco.core.tool_stack import ToolStack
from taco.core.message_handler import MessageHandler
from taco.core.command_handler import CommandHandler
from taco.core.debug_display import DebugDisplay

console = Console()

class ChatSession:
    """Manages interactive chat sessions with the LLM"""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize chat session"""
        print("DEBUG: ChatSession initialization starting", file=sys.stderr)
        try:
            self.model_manager = ModelManager()
            print("DEBUG: ModelManager initialized", file=sys.stderr)
            self.tool_registry = ToolRegistry()
            print("DEBUG: ToolRegistry initialized", file=sys.stderr)
            self.context_manager = ContextManager()
            print("DEBUG: ContextManager initialized", file=sys.stderr)
            
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
            
            # Debug tree data
            self._debug_tree_data = None
            
            # Add project command handling
            self._add_project_commands()
            
            # History file path for prompt_toolkit
            history_dir = os.path.expanduser("~/.config/taco")
            os.makedirs(history_dir, exist_ok=True)
            self.history_file = os.path.join(history_dir, "chat_history")
            
            print("DEBUG: ChatSession initialization complete", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: Exception during initialization: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise
    
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
                
                success = self.context_manager.create_project_context(project_name, workingdir, **kwargs)
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
                contexts = self.context_manager.list_contexts()
                if not any(ctx['name'] == context_name for ctx in contexts):
                    return f"Project '{project_name}' not found"
                
                success = self.context_manager.set_active_context(context_name)
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
                
                self.context_manager.update_project_setting(key, value)
                return f"Updated project setting: {key} = {value}"
            
            elif subcommand == 'info':
                project_info = self.context_manager.get_project_info()
                if project_info:
                    import json
                    return json.dumps(project_info, indent=2)
                else:
                    return "No active project"
            
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

    def _communicate_with_ollama(self, messages: List[Dict[str, str]], 
                               context_name: str = "Request",
                               previous_tool_results: List[Dict] = None) -> str:
        """
        Send a request to Ollama and handle debug information.
        
        Args:
            messages: The messages to send to Ollama
            context_name: Name for this request (e.g., "First Request", "Follow-up Request")
            previous_tool_results: Tool results to include in debug info
        
        Returns:
            The response from Ollama
        """
        # Store debug information for the tree view
        if self.debug_mode:
            # Create debug tree data if not already present
            if not hasattr(self, '_debug_tree_data') or self._debug_tree_data is None:
                self._debug_tree_data = {
                    'user_input': None,
                    'requests': [],
                    'responses': [],
                    'tool_calls': [],
                    'tool_results': []
                }
            
            # Add this request to the debug data
            self._debug_tree_data['requests'].append({
                'name': context_name,
                'messages': messages
            })
        
        # Log the request if in debug mode
        if self.debug_mode:
            debug_logger.log(f"== {context_name} to Ollama ==", "REQUEST", "bright_magenta")
            debug_logger.log(f"Sending {len(messages)} messages", "REQUEST", "magenta")
            if len(messages) > 0:
                last_msg = messages[-1]['content']
                preview = last_msg[:200] + "..." if len(last_msg) > 200 else last_msg
                debug_logger.log(f"Last message: {preview}", "REQUEST", "magenta")
        
        # Send the request to Ollama
        with display_thinking():
            response = self.model_manager.generate_response(
                self.model_name, 
                messages
            )
        
        # Log the response if in debug mode
        if self.debug_mode:
            debug_logger.log(f"== {context_name} Response from Ollama ==", "RESPONSE", "bright_blue")
            preview = response[:200] + "..." if len(response) > 200 else response
            debug_logger.log(f"Response: {preview}", "RESPONSE", "blue")
            
            # Add this response to the debug data
            self._debug_tree_data['responses'].append({
                'name': f"{context_name} Response",
                'content': response
            })
            
            # Parse tool calls if needed
            tool_calls = self.message_handler.parse_tool_calls(response)
            if tool_calls:
                debug_logger.log(f"Found {len(tool_calls)} tool calls in response", "RESPONSE", "green")
                self._debug_tree_data['tool_calls'].append({
                    'context': context_name,
                    'calls': tool_calls
                })
            else:
                debug_logger.log("No tool calls found in response", "RESPONSE", "yellow")
        
        return response

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and return results with details"""
        results = []
        
        if self.debug_mode:
            debug_logger.log(f"Processing {len(tool_calls)} tool calls", "CHAT", "blue")
            debug_logger.log(f"Current tool stack: {len(self.tool_stack.stack)} items", "CHAT", "blue")
            if self.tool_stack.stack:
                for i, item in enumerate(self.tool_stack.stack):
                    debug_logger.log(f"Stack item {i}: {item['tool']}", "CHAT", "blue")
        
        for call in tool_calls:
            tool_name = call['tool_name']
            params = call['parameters']
            
            if self.debug_mode:
                debug_logger.log(f"Processing tool call: {tool_name}", "TOOL_CALL", "cyan")
                debug_logger.log_json(params, "Parameters")
            
            # Special handling for create_code tool that receives 'code' instead of 'prompt'
            if tool_name == 'create_code' and 'prompt' not in params and 'code' in params:
                if self.debug_mode:
                    debug_logger.log(f"Remapping 'code' parameter to 'prompt' for create_code tool", "TOOL_CALL", "yellow")
                params['prompt'] = params.pop('code')
            
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
                
                if self.debug_mode:
                    debug_logger.log(f"Getting usage instructions for {tool_name}", "TOOL_CALL", "blue")
                    debug_logger.log(f"Usage instructions:", "TOOL_CALL", "magenta")
                    # Print the full instructions to see what we're sending to Ollama
                    debug_logger.log(usage_instructions, "TOOL_USAGE", "magenta")
                
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
                
                # Get function signature for debugging
                if self.debug_mode:
                    import inspect
                    sig = inspect.signature(func)
                    debug_logger.log(f"Tool function signature: {sig}", "TOOL_CALL", "blue")
                    debug_logger.log(f"Expected parameters: {list(sig.parameters.keys())}", "TOOL_CALL", "blue")
                
                updated_params, missing_params = self.context_manager.check_missing_parameters(func, params)
                
                if self.debug_mode:
                    debug_logger.log(f"Original params: {json.dumps(params)}", "TOOL_CALL", "blue")
                    debug_logger.log(f"Updated params: {json.dumps(updated_params)}", "TOOL_CALL", "blue")
                    if missing_params:
                        debug_logger.log(f"Missing params: {missing_params}", "TOOL_CALL", "yellow")
                    else:
                        debug_logger.log(f"No missing params", "TOOL_CALL", "green")
                
                # Convert parameters based on tool signature
                converted_params = {}
                for param_name, param_value in updated_params.items():
                    if param_name in tool.type_hints:
                        converted_value = tool.convert_argument(param_name, param_value)
                        converted_params[param_name] = converted_value
                    else:
                        converted_params[param_name] = param_value
                
                if self.debug_mode:
                    debug_logger.log(f"Converted params: {json.dumps(converted_params)}", "TOOL_CALL", "blue")
                
                # Execute with properly typed parameters
                result = tool.execute(**converted_params)
                
                if self.debug_mode:
                    debug_logger.log(f"Tool execution result:", "TOOL_RESULT", "green")
                    debug_logger.log_json(result, "Result")
                    
                    if isinstance(result, dict) and result.get('status') == 'needs_parameters':
                        debug_logger.log(f"Tool needs parameters collection!", "TOOL_RESULT", "green")
                        debug_logger.log(f"Questions: {result.get('questions', [])}", "TOOL_RESULT", "green")
                        debug_logger.log(f"Parameter names: {result.get('parameter_names', [])}", "TOOL_RESULT", "green")
                
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
                if self.debug_mode:
                    debug_logger.log(f"Tool execution error: {str(e)}", "TOOL_ERROR", "red")
                    import traceback
                    debug_logger.log(traceback.format_exc(), "TOOL_ERROR", "red")
                
                results.append({
                    'tool': tool_name,
                    'parameters': params,
                    'error': str(e),
                    'success': False
                })
        
        if self.debug_mode:
            debug_logger.log(f"Final tool stack after execution: {len(self.tool_stack.stack)} items", "CHAT", "blue")
            if self.tool_stack.stack:
                for i, item in enumerate(self.tool_stack.stack):
                    debug_logger.log(f"Stack item {i}: {item['tool']}", "CHAT", "blue")
        
        return results

    def _show_debug_tree(self):
        """Show the debug tree with all communication data"""
        # Call debug display with all the collected information
        if hasattr(self, '_debug_tree_data') and self._debug_tree_data:
            # Prepare data for the tree view
            user_input = self._debug_tree_data.get('user_input', '')
            requests = self._debug_tree_data.get('requests', [])
            responses = self._debug_tree_data.get('responses', [])
            tool_calls = self._debug_tree_data.get('tool_calls', [])
            tool_results = self._debug_tree_data.get('tool_results', [])
            
            # Find the first request/response pair
            first_request = requests[0]['messages'] if requests else []
            first_response = responses[0]['content'] if responses else ''
            
            # Find tool calls from first response
            first_tool_calls = []
            if tool_calls and len(tool_calls) > 0:
                first_tool_calls = tool_calls[0]['calls']
            
            # Create follow-up data if available
            follow_up_data = None
            if len(requests) > 1 and len(responses) > 1:
                follow_up_data = {
                    'messages': requests[1]['messages'],
                    'response': responses[1]['content']
                }
                
                # Check for tool calls in second response
                second_tool_calls = []
                if len(tool_calls) > 1:
                    second_tool_calls = tool_calls[1]['calls']
                follow_up_data['tool_calls'] = second_tool_calls
            
            # Call debug display
            self.debug_display.display_debug_tree(
                user_input,
                first_request,
                first_response,
                first_tool_calls,
                tool_results,
                self.tool_stack,
                follow_up_data
            )

    def ask(self, question: str) -> str:
        """Ask a question to the model"""
        # If debug mode is enabled, enable the debug logger
        if self.debug_mode:
            debug_logger.enable()
            # Reset debug tree data for each new question
            self._debug_tree_data = {
                'user_input': question,
                'requests': [],
                'responses': [],
                'tool_calls': [],
                'tool_results': []
            }
        else:
            debug_logger.disable()
        
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
        
        # Send first request to Ollama
        response = self._communicate_with_ollama(messages, "First Request")
        
        # Clean up the response for processing
        cleaned_response = self.message_handler.clean_response_content(response)
        
        # Check for tool calls in the response
        tool_calls = self.message_handler.parse_tool_calls(cleaned_response)
        tool_results = []
        
        if tool_calls:
            if self.debug_mode:
                debug_logger.log(f"Found {len(tool_calls)} tool calls", "CHAT", "green")
            
            # Execute tool calls
            tool_results = self._execute_tool_calls(tool_calls)
            
            if self.debug_mode:
                debug_logger.log(f"Got {len(tool_results)} tool results", "CHAT", "green")
                for i, result in enumerate(tool_results):
                    debug_logger.log(f"Result {i+1}: {result['tool']} - Success: {result['success']}", "CHAT", "green")
                
                # Store tool results for debug tree
                self._debug_tree_data['tool_results'] = tool_results

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
                    if self.debug_mode:
                        debug_logger.log(f"Detected usage instructions for {result['tool']}", "TOOL_FLOW", "yellow")
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

Follow the usage instructions you just received.

Tool results:
{tool_results_text}"""
                    
                    if self.debug_mode:
                        debug_logger.log("Created follow-up context with usage instructions", "TOOL_FLOW", "cyan")
                        debug_logger.log(f"Instructing Ollama to use {tool_results[0]['tool']} tool", "TOOL_FLOW", "cyan")
                else:
                    # Normal tool results handling
                    tool_context = f"The following tool was executed:\n{tool_results_text}\n\nPlease provide a natural language response explaining these results to the user."
                
                self.history.append({"role": "system", "content": tool_context})
                
                # Get another response from the model to interpret the results
                interpretation_messages = []
                interpretation_messages.append({
                    "role": "system", 
                    "content": f"Use the {tool_results[0]['tool']} tool with the correct parameters to generate the code. Follow the usage instructions exactly."
                })
                #claude this area is the problem area
                # Include the original user question directly
                interpretation_messages.append({    "role": "user",    "content": question  })
                # Add the tool context as a focused system message
                interpretation_messages.append({    "role": "system",    "content": tool_context  })# This contains the usage instructions

                interpretation_response = self._communicate_with_ollama(messages, "First Request")
                
                cleaned_interpretation = self.message_handler.clean_response_content(interpretation_response)
                
                # Add the interpretation to history
                self.history.append({"role": "assistant", "content": cleaned_interpretation})
                
                # Show debug tree if in debug mode
                if self.debug_mode:
                    self._show_debug_tree()
                
                # Return the natural language response without JSON in normal mode
                if response_without_tools:
                    # Combine the original response (without JSON) with the interpretation
                    return response_without_tools + "\n\n" + cleaned_interpretation
                else:
                    return cleaned_interpretation
            else:
                # No tool results, just return cleaned response without JSON
                if self.debug_mode:
                    self._show_debug_tree()
                return response_without_tools
        else:
            # No tool calls, normal response
            self.history.append({"role": "assistant", "content": cleaned_response})
            
            # Show debug tree if in debug mode
            if self.debug_mode:
                self._show_debug_tree()
            
            return cleaned_response

    def start_interactive(self, save_path: Optional[str] = None):
        """Start an interactive chat session"""
        print("DEBUG: Starting interactive session", file=sys.stderr)
        try:
            # Create prompt session with history
            session = PromptSession(history=FileHistory(self.history_file))
            print("DEBUG: PromptSession created", file=sys.stderr)
            
            # Display welcome message
            display_system_message(f"Chat session started with model: {self.model_name}")
            display_system_message("Type /help for commands, /bye to quit")
            display_system_message("Debug: OFF (use /debug on to enable)")
            
            # Check for active project
            project_info = self.context_manager.get_project_info()
            if project_info:
                display_system_message(f"Active project: {project_info['name']} ({project_info['workingdir']})")
            else:
                display_system_message("No active project. Use /project new <name> to create one.")
            
            print("DEBUG: Welcome message displayed", file=sys.stderr)
            
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
                    
                    print(f"DEBUG: Processing user input: {user_input}", file=sys.stderr)
                    
                    # Process the input
                    response = self.ask(user_input)
                    
                    print("DEBUG: Got response, displaying to user", file=sys.stderr)
                    
                    # Print the response
                    console.print(f"\n[Assistant]: {response}")
            except KeyboardInterrupt:
                print("DEBUG: KeyboardInterrupt received", file=sys.stderr)
                pass
            finally:
                # Save history if requested
                if save_path:
                    self.save_history(save_path)
                    display_system_message(f"Chat history saved to {save_path}")
                
                display_system_message("Chat session ended. Goodbye!")
                print("DEBUG: Chat session ended", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: Exception during interactive session: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise
    
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