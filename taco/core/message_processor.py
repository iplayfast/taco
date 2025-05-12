# taco/core/message_processor.py
"""
TACO Message Processor
Handles message processing, formatting, and interpretation.
"""
from typing import Dict, List, Any, Optional
from taco.utils.debug_logger import debug_logger

class MessageProcessor:
    """Processes messages between the user, LLM, and tools"""
    
    def __init__(self, model_manager, message_handler, tool_stack):
        """Initialize with required components"""
        self.model_manager = model_manager
        self.message_handler = message_handler
        self.tool_stack = tool_stack
    
    def prepare_messages(self, history: List[Dict[str, str]], 
                        system_content: str, 
                        tool_mode: bool = False) -> List[Dict[str, str]]:
        """Prepare messages for sending to the LLM"""
        messages = []
        
        # Add system content if available
        if system_content:
            messages.append({"role": "system", "content": system_content})
        
        # If in tool mode, modify the user's question for tool selection
        modified_history = history.copy()
        if tool_mode and not self.tool_stack.stack and modified_history:
            last_message = modified_history[-1]
            if last_message["role"] == "user":
                # Modify the question to force tool selection
                modified_history[-1] = {
                    "role": "user", 
                    "content": f"Select the best tool to handle this request: {last_message['content']}"
                }
                debug_logger.log("Modified user query for tool selection", "MESSAGE_PREP")
        
        messages.extend(modified_history)
        debug_logger.log(f"Prepared {len(messages)} messages for LLM", "MESSAGE_PREP")
        
        return messages
    
    def create_tool_context(self, tool_results: List[Dict[str, Any]], 
                          tool_results_text: str, 
                          got_usage_instructions: bool) -> Optional[str]:
        """Create context message after tool execution"""
        if not tool_results_text:
            return None
            
        if got_usage_instructions and self.tool_stack.original_prompt:
            # Special handling for post-usage-instructions
            tool_context = f"""The tool has provided its usage instructions. 

Now you should use the {tool_results[0]['tool']} tool to handle the user's original request: "{self.tool_stack.original_prompt}"

Follow the usage instructions you just received, and apply them to create: "{self.tool_stack.original_prompt}"

Tool results:
{tool_results_text}"""
            
            debug_logger.log("Created special context for tool usage instructions", "TOOL_CONTEXT")
            debug_logger.log_dataflow("TOOL_CONTEXT", tool_context)
        else:
            # Normal tool results handling
            tool_context = f"The following tool was executed:\n{tool_results_text}\n\nPlease provide a natural language response explaining these results to the user."
            debug_logger.log("Created standard context for tool results", "TOOL_CONTEXT")
        
        return tool_context
    
    def process_response(self, response: str) -> Dict[str, Any]:
        """Process a response from the LLM"""
        # Clean up the response for processing
        cleaned_response = self.message_handler.clean_response_content(response)
        debug_logger.log("Cleaned LLM response", "RESPONSE_PROC")
        
        # Check for tool calls in the response
        tool_calls = self.message_handler.parse_tool_calls(cleaned_response)
        
        if tool_calls:
            debug_logger.log(f"Found {len(tool_calls)} tool calls in response", "RESPONSE_PROC")
        else:
            debug_logger.log("No tool calls found in response", "RESPONSE_PROC")
        
        return {
            "cleaned_response": cleaned_response,
            "tool_calls": tool_calls
        }