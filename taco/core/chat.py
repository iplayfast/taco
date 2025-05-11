"""
TACO Chat Session Management with Debug Mode
"""
import os
import sys
import json
import re
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt
from rich.tree import Tree
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
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
        
        # Session modes
        self.debug_mode = False
        
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
            tool_info = self.tool_registry.get_tool_info(tool_name)
            tools_description += f"\n- {tool_name}: {tool_info['description']}\n"
            
            if tool_info['parameters']:
                tools_description += "  Parameters:\n"
                for param in tool_info['parameters']:
                    tools_description += f"    - {param['name']} ({param['type']}): {param['description']}"
                    if param.get('required', False):
                        tools_description += " [REQUIRED]"
                    tools_description += "\n"
        
        tools_description += """
When you need to use a tool, follow these steps:

1. First, check if the user has provided all required parameters
2. If parameters are missing, use the collect_tool_parameters tool FIRST
3. Once you have all parameters, call the actual tool

IMPORTANT: When using collect_tool_parameters, you MUST provide both:
- tool_name: the name of the tool you want to collect parameters for
- questions: a list of questions to ask the user

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

Example workflow for calculating a mortgage when user doesn't provide parameters:

Step 1: User asks "can you calculate a mortgage for me?" (no parameters provided)
You should respond with:
```json
{
  "tool_call": {
    "name": "collect_tool_parameters",
    "parameters": {
      "tool_name": "calculate_mortgage",
      "questions": [
        "What is the loan amount (principal) in dollars?",
        "What is the annual interest rate (as a percentage, e.g., 5.5)?",
        "How many years is the loan term?"
      ]
    }
  }
}
```

Step 2: After collecting parameters, you'll receive them and can then call:
```json
{
  "tool_call": {
    "name": "calculate_mortgage",
    "parameters": {
      "principal": 300000,
      "annual_rate": 5.5,
      "years": 30
    }
  }
}
```

Example when user provides all parameters:
User: "Calculate mortgage for $300,000 at 5.5% for 30 years"
You can directly call:
```json
{
  "tool_call": {
    "name": "calculate_mortgage",
    "parameters": {
      "principal": 300000,
      "annual_rate": 5.5,
      "years": 30
    }
  }
}
```

Remember:
- Always check if parameters are provided first
- Use collect_tool_parameters with proper questions when parameters are missing
- The questions should be specific to the tool being used
- Questions should be in plain, user-friendly language
"""
        return tools_description

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls from the model's response"""
        tool_calls = []
        
        # Find all JSON blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.finditer(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                json_content = match.group(1).strip()
                data = json.loads(json_content)
                
                if 'tool_call' in data:
                    tool_call = data['tool_call']
                    if 'name' in tool_call and 'parameters' in tool_call:
                        tool_calls.append({
                            'tool_name': tool_call['name'],
                            'parameters': tool_call['parameters'],
                            'original_text': match.group(0)
                        })
            except json.JSONDecodeError:
                # Skip invalid JSON
                continue
        
        return tool_calls
    
    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and return results with details"""
        results = []
        
        for call in tool_calls:
            tool_name = call['tool_name']
            params = call['parameters']
            
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
                result = tool.func(**converted_params)
                
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
    
    def _format_tool_results(self, results: List[Dict[str, Any]]) -> str:
        """Format tool results for display"""
        if not results:
            return ""
            
        formatted_results = "\n\n**Tool Results:**\n"
        for r in results:
            formatted_results += f"\n**{r['tool']}**\n"
            if not r['success']:
                formatted_results += f"❌ Error: {r['error']}\n"
            else:
                formatted_results += "✅ Success\n"
                # Use custom formatting for better readability
                formatted_json = self._format_json_for_display(r['result'])
                formatted_results += f"```\n{formatted_json}\n```\n"
        
        return formatted_results
    
    def _format_json_for_display(self, data: Any, indent: int = 0) -> str:
        """Format JSON data with properly rendered strings for display"""
        spaces = "  " * indent
        if isinstance(data, dict):
            lines = ["{"]
            items = list(data.items())
            for i, (key, value) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                if isinstance(value, str):
                    # Format string values with actual newlines
                    formatted_value = value.encode().decode('unicode-escape')
                    # Add quotes and handle multiline strings
                    if '\n' in formatted_value:
                        lines.append(f'{spaces}  "{key}": """')
                        for line in formatted_value.split('\n'):
                            lines.append(f'{spaces}    {line}')
                        lines.append(f'{spaces}  """{comma}')
                    else:
                        lines.append(f'{spaces}  "{key}": "{formatted_value}"{comma}')
                else:
                    # Recursively format nested structures
                    formatted_value = self._format_json_for_display(value, indent + 1)
                    lines.append(f'{spaces}  "{key}": {formatted_value}{comma}')
            lines.append(f"{spaces}}}")
            return "\n".join(lines)
        elif isinstance(data, list):
            if not data:
                return "[]"
            lines = ["["]
            for i, item in enumerate(data):
                comma = "," if i < len(data) - 1 else ""
                formatted_item = self._format_json_for_display(item, indent + 1)
                lines.append(f"{spaces}  {formatted_item}{comma}")
            lines.append(f"{spaces}]")
            return "\n".join(lines)
        elif isinstance(data, str):
            # For standalone strings, decode escape sequences
            return f'"{data.encode().decode("unicode-escape")}"'
        elif isinstance(data, (int, float, bool)) or data is None:
            return json.dumps(data)
        else:
            return str(data)
    
    def _clean_response_content(self, content: str) -> str:
        """Clean up response content for display"""
        # Handle the Message object format
        if isinstance(content, str) and content.startswith("model=") and "message=Message(" in content:
            # Look for content with single or double quotes
            match = re.search(r'content=(["\'])(.*?)\1(?:,\s*images=|$)', content, re.DOTALL)
            if match:
                actual_content = match.group(2)
                content = actual_content.strip()
            else:
                # If pattern doesn't match, just use the original content
                pass
        
        # For all string content, fix Unicode issues
        if isinstance(content, str):
            # Common replacements for Unicode characters
            unicode_replacements = {
                '\u2018': "'",  # Left single quotation mark
                '\u2019': "'",  # Right single quotation mark
                '\u201c': '"',  # Left double quotation mark
                '\u201d': '"',  # Right double quotation mark
                '\u2013': '-',  # En dash
                '\u2014': '--', # Em dash
                '\u2026': '...', # Horizontal ellipsis
                '\u00a0': ' ',  # Non-breaking space
                '\u2022': '*',  # Bullet
                '\u25cf': '*',  # Black circle
                '\u2122': '(TM)', # Trademark
                '\u00ae': '(R)', # Registered trademark
                '\u00a9': '(C)', # Copyright
                '\u00b0': ' degrees', # Degree symbol
                '\u00b1': '+/-', # Plus-minus
                '\u00bc': '1/4', # One quarter
                '\u00bd': '1/2', # One half
                '\u00be': '3/4', # Three quarters
                '\u2190': '<-',  # Left arrow
                '\u2192': '->',  # Right arrow
                '\u2194': '<->', # Left-right arrow
                '\u2713': 'checkmark', # Check mark
                '\u2717': 'X',   # Ballot X
                '\u221e': 'infinity', # Infinity
                '\u2260': '!=',  # Not equal
                '\u2264': '<=',  # Less than or equal
                '\u2265': '>=',  # Greater than or equal
                '\u2248': '~=',  # Almost equal
            }
            
            # Apply all replacements
            for unicode_char, replacement in unicode_replacements.items():
                content = content.replace(unicode_char, replacement)
            
            # Try to decode any remaining escape sequences
            try:
                if '\\n' in content or '\\u' in content or '\\x' in content:
                    content = content.encode('utf-8').decode('unicode-escape')
            except Exception:
                # If decoding fails, just continue with what we have
                pass
            
            # Final cleanup - remove any remaining non-ASCII characters
            # that might cause display issues
            try:
                # Try to encode to ASCII and replace problematic characters
                content = content.encode('ascii', errors='replace').decode('ascii')
                # Replace the placeholder character with a space
                content = content.replace('?', ' ')
            except Exception:
                # If even this fails, just return the content as is
                pass
        
        return content

    def _format_for_panel(self, content: str, max_width: int = 80) -> str:
        """Format content for display in a panel with proper line wrapping"""
        # Clean up the content first
        cleaned = self._clean_response_content(content)
        
        # If it's JSON, format it nicely
        if cleaned.strip().startswith('{') or cleaned.strip().startswith('['):
            try:
                parsed = json.loads(cleaned)
                return json.dumps(parsed, indent=2)
            except:
                pass
        
        # For regular text, ensure proper line breaks
        lines = []
        for line in cleaned.split('\n'):
            if len(line) > max_width:
                # Wrap long lines
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_width:
                        current_line += word + " "
                    else:
                        if current_line:
                            lines.append(current_line.strip())
                        current_line = word + " "
                if current_line:
                    lines.append(current_line.strip())
            else:
                lines.append(line)
        
        return '\n'.join(lines)
    
    def _display_debug_tree(self, user_input: str, messages: List[Dict], 
                           response: str, tool_calls: List[Dict], 
                           tool_results: List[Dict]):
        """Display debug information as a tree"""
        tree = Tree("🔍 Debug Communication Tree")
        
        # User input
        user_node = tree.add("👤 User Input")
        user_node.add(Panel(user_input, title="Question", border_style="blue"))
        
        # Request to Ollama
        request_node = tree.add("📤 Request to Ollama")
        # Format the messages for display using custom formatter
        formatted_request = self._format_json_for_display(messages)
        request_node.add(Panel(formatted_request, 
                              title="JSON Request", border_style="green"))
        
        # Response from Ollama
        response_node = tree.add("📥 Response from Ollama")
        formatted_response = self._format_for_panel(response)
        response_node.add(Panel(formatted_response, title="Raw Response", border_style="yellow"))
        
        if tool_calls:
            # Tool calls found
            tools_node = response_node.add("🔧 Tool Calls Detected")
            for i, call in enumerate(tool_calls):
                tool_node = tools_node.add(f"Tool {i+1}: {call['tool_name']}")
                # Use custom formatter for tool calls too
                call_data = {
                    "name": call['tool_name'],
                    "parameters": call['parameters']
                }
                formatted_call = self._format_json_for_display(call_data)
                tool_node.add(Panel(formatted_call, 
                                   title="Tool Call", border_style="cyan"))
                
                # Find corresponding result
                matching_result = None
                for result in tool_results:
                    if result['tool'] == call['tool_name'] and result['parameters'] == call['parameters']:
                        matching_result = result
                        break
                
                if matching_result:
                    result_node = tool_node.add("📊 Tool Result")
                    if matching_result['success']:
                        # Use custom formatting for better display
                        formatted_json = self._format_json_for_display(matching_result['result'])
                        result_node.add(Panel(formatted_json, 
                                            title="Success", border_style="green"))
                    else:
                        result_node.add(Panel(matching_result['error'], 
                                            title="Error", border_style="red"))
                    
                    # Direction of result
                    direction_node = result_node.add("➡️ Direction")
                    direction_node.add(Panel("Back to Ollama for incorporation into response", 
                                          border_style="magenta"))
        
        # Final output to user
        output_node = tree.add("💬 Final Output to User")
        output_node.add(Panel("(Shown in main chat)", border_style="white"))
        
        console.print(tree)
    
    def ask(self, question: str) -> str:
        """Ask a question to the model"""
        # Check if the question is a command
        if question.startswith('/'):
            return self._handle_command(question)
        
        # Check for manual tool usage
        tool_result = self._check_for_tool_usage(question)
        if tool_result:
            return tool_result
        
        # Add to history
        self.history.append({"role": "user", "content": question})
        
        # Get active context
        context = self.context_manager.get_active_context_content()
        
        # Prepare system message with tools description
        tools_prompt = self._get_tools_prompt()
        system_content = ""
        
        if context:
            system_content += context + "\n\n"
        
        if tools_prompt:
            system_content += tools_prompt
        
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
        cleaned_response = self._clean_response_content(response)
        
        # Check for tool calls in the response
        tool_calls = self._parse_tool_calls(cleaned_response)
        tool_results = []
        
        if tool_calls:
            # Execute tool calls
            tool_results = self._execute_tool_calls(tool_calls)
            
            # Check if we just collected parameters successfully
            for i, result in enumerate(tool_results):
                if (result['tool'] == 'collect_tool_parameters' and 
                    result['success'] and 
                    'tool_name' in tool_calls[i]['parameters']):
                    
                    # Get the target tool name that we collected parameters for
                    target_tool = tool_calls[i]['parameters']['tool_name']
                    collected_params = result['result']
                    
                    # Immediately proceed to call the target tool
                    # Add the response to history first
                    self.history.append({"role": "assistant", "content": cleaned_response})
                    
                    # Create a new tool call for the target tool
                    auto_tool_call = {
                        "tool_call": {
                            "name": target_tool,
                            "parameters": collected_params
                        }
                    }
                    
                    # Add system instruction to proceed with the calculation
                    proceed_instruction = f"""The user has provided all necessary parameters. Please proceed immediately to calculate the {target_tool.replace('_', ' ')} with the following parameters:
{json.dumps(collected_params, indent=2)}

Respond with the appropriate tool call JSON block to execute the calculation."""
                    
                    self.history.append({"role": "system", "content": proceed_instruction})
                    
                    # Get the model to generate the tool call
                    proceed_messages = []
                    if system_content:
                        proceed_messages.append({"role": "system", "content": system_content})
                    proceed_messages.extend(self.history)
                    
                    with display_thinking():
                        proceed_response = self.model_manager.generate_response(
                            self.model_name,
                            proceed_messages
                        )
                    
                    # Process this new response recursively
                    return self.ask("")  # Empty question to process the new response
            
            # If not parameter collection, proceed with normal flow
            # Format results for display
            tool_results_text = self._format_tool_results(tool_results)
            
            # Remove tool call blocks from the response
            response_without_tools = cleaned_response
            for call in tool_calls:
                response_without_tools = response_without_tools.replace(call['original_text'], '')
            response_without_tools = response_without_tools.strip()
            
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
                
                cleaned_interpretation = self._clean_response_content(interpretation_response)
                
                # Add the interpretation to history
                self.history.append({"role": "assistant", "content": cleaned_interpretation})
                
                # Show debug tree if in debug mode
                if self.debug_mode:
                    self._display_debug_tree(question, messages, response, tool_calls, tool_results)
                
                # Return the natural language response without JSON in normal mode
                if response_without_tools:
                    # Combine the original response (without JSON) with the interpretation
                    return response_without_tools + "\n\n" + cleaned_interpretation
                else:
                    return cleaned_interpretation
            else:
                # No tool results, just return cleaned response without JSON
                if self.debug_mode:
                    self._display_debug_tree(question, messages, response, tool_calls, tool_results)
                return response_without_tools
        else:
            # No tool calls, normal response
            self.history.append({"role": "assistant", "content": cleaned_response})
            
            # Show debug tree if in debug mode
            if self.debug_mode:
                self._display_debug_tree(question, messages, response, tool_calls, tool_results)
            
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
    
    def _handle_command(self, command: str) -> str:
        """Handle chat commands"""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd == '/help':
            return """
Available commands:
/help - Show this help message
/bye - Exit the chat session (also: /exit, /quit)
/mode [normal|debug] - Switch between normal and debug modes
/model [name] - Show or switch the current model (default: gemma3)
/clear - Clear the chat history
/tools - List available tools
/context - Show active context
/list model - List all available models from Ollama
/list tools - List all registered TACO tools

Current mode: """ + ("Debug" if self.debug_mode else "Normal")
        
        elif cmd == '/mode':
            if len(cmd_parts) > 1:
                mode = cmd_parts[1].lower()
                if mode == 'debug':
                    self.debug_mode = True
                    return "Switched to Debug mode - you'll see detailed communication trees"
                elif mode == 'normal':
                    self.debug_mode = False
                    return "Switched to Normal mode"
                else:
                    return "Invalid mode. Options: normal, debug"
            else:
                return f"Current mode: {'Debug' if self.debug_mode else 'Normal'}"
        
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
        
        elif cmd == '/list':
            if len(cmd_parts) < 2:
                return "Please specify what to list. Options: 'model' or 'tools'"
            
            list_type = cmd_parts[1].lower()
            
            if list_type == 'model':
                models = self.model_manager.list_models()
                if not models:
                    return "No models found. Make sure Ollama is running."
                
                result = "Available Ollama models:\n"
                for model in models:
                    result += f"• {model['name']} - {model['description']}\n"
                return result
            
            elif list_type == 'tools':
                tools = self.tool_registry.list_tools()
                if not tools:
                    return "No tools registered."
                
                result = "Registered TACO tools:\n"
                for tool in tools:
                    result += f"• {tool['name']} - {tool['description']}\n"
                return result
            
            else:
                return f"Unknown list type: {list_type}. Options are: 'model' or 'tools'"
        
        return f"Unknown command: {cmd}"
    
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