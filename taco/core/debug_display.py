"""
TACO Debug Display
Handles debug visualization and formatting.
"""
from typing import List, Dict, Any
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel

console = Console()

class DebugDisplay:
    """Handles debug visualization for chat sessions"""
    
    def __init__(self, message_handler):
        """Initialize with reference to message handler"""
        self.message_handler = message_handler
    
    def display_debug_tree(self, user_input: str, messages: List[Dict], 
                          response: str, tool_calls: List[Dict], 
                          tool_results: List[Dict], tool_stack: Any):
        """Display debug information as a tree"""
        tree = Tree("🔍 Debug Communication Tree")
        
        # User input
        user_node = tree.add("👤 User Input")
        user_node.add(Panel(user_input, title="Question", border_style="blue"))
        
        # Tool stack status
        if tool_stack.stack:
            stack_node = tree.add("📚 Tool Stack")
            stack_node.add(Panel(tool_stack.format_stack(), title="Current Stack", border_style="magenta"))
        
        # Request to Ollama
        request_node = tree.add("📤 Request to Ollama")
        # Format the messages for display using custom formatter
        formatted_request = self.message_handler.format_json_for_display(messages)
        request_node.add(Panel(formatted_request, 
                              title="JSON Request", border_style="green"))
        
        # Response from Ollama
        response_node = tree.add("📥 Response from Ollama")
        formatted_response = self.message_handler.format_for_panel(response)
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
                formatted_call = self.message_handler.format_json_for_display(call_data)
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
                        formatted_json = self.message_handler.format_json_for_display(matching_result['result'])
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