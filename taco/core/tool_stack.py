"""
TACO Tool Stack Management
Handles the orchestration of tool workflows and maintains execution context.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

class ToolStack:
    """Manages the tool execution stack for complex workflows"""
    
    def __init__(self):
        """Initialize the tool stack"""
        self.stack: List[Dict[str, Any]] = []
        self.original_prompt: Optional[str] = None
        self.max_stack_depth: int = 20
    
    def push(self, tool_name: str, context: Dict[str, Any] = None) -> None:
        """Push a tool onto the stack"""
        self.stack.append({
            'tool': tool_name,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def pop(self) -> Optional[Dict[str, Any]]:
        """Pop a tool from the stack"""
        if self.stack:
            return self.stack.pop()
        return None
    
    def clear(self) -> None:
        """Clear the tool stack and original prompt"""
        self.stack = []
        self.original_prompt = None
    
    def get_depth(self) -> int:
        """Get current stack depth"""
        return len(self.stack)
    
    def get_current_tool(self) -> Optional[str]:
        """Get the name of the currently active tool"""
        if self.stack:
            return self.stack[-1]['tool']
        return None
    
    def get_current_context(self) -> Optional[Dict[str, Any]]:
        """Get the context of the currently active tool"""
        if self.stack:
            return self.stack[-1]['context']
        return None
    
    def set_original_prompt(self, prompt: str) -> None:
        """Set the original user prompt for this workflow"""
        self.original_prompt = prompt
    
    def format_stack(self) -> str:
        """Format the tool stack for display"""
        if not self.stack:
            return "No active tool workflow"
        
        lines = ["Tool Stack:"]
        for i, item in enumerate(self.stack):
            indent = "  " * i
            tool_name = item['tool']
            context = item.get('context', {})
            status = context.get('status', 'active')
            lines.append(f"{indent}└─ {tool_name} [{status}]")
        
        if self.original_prompt:
            lines.append(f"\nOriginal request: {self.original_prompt}")
        
        return "\n".join(lines)
    
    def check_depth_limit(self) -> bool:
        """
        Check if stack depth is within limits.
        Returns True if OK to continue, False if limit reached and user cancelled.
        """
        depth = self.get_depth()
        
        if depth >= self.max_stack_depth:
            # Show status and ask for confirmation
            console.print(Panel(self.format_stack(), title="Tool Stack Status", border_style="yellow"))
            console.print(f"\n[yellow]Warning: Tool stack depth has reached {depth} levels.[/yellow]")
            
            response = Prompt.ask("Continue for another 20 levels? [y/N]", default="n")
            if response.lower() == 'y':
                self.max_stack_depth += 20
                return True
            else:
                self.clear()
                return False
        
        return True
    
    def get_system_context(self) -> str:
        """Get tool stack context for system prompt"""
        if not self.stack:
            return ""
        
        context = "\n\nCurrent tool workflow context:\n"
        context += f"- Active tool: {self.get_current_tool()}\n"
        
        tool_context = self.get_current_context()
        if tool_context:
            if 'waiting_for' in tool_context:
                context += f"- Waiting for: {tool_context['waiting_for']}\n"
            if 'parameters_needed' in tool_context:
                context += f"- Parameters needed: {', '.join(tool_context['parameters_needed'])}\n"
        
        if self.original_prompt:
            context += f"- Original request: {self.original_prompt}\n"
        
        context += f"- Stack depth: {self.get_depth()}\n"
        context += "\nThe user is currently in a tool workflow. Stay focused on completing the current task."
        
        return context
    
    def is_context_switch(self, user_input: str) -> bool:
        """Detect if the user is switching context"""
        if not self.stack or not user_input:
            return False
        
        # Check for explicit context switch indicators
        context_switch_phrases = [
            "forget about",
            "never mind",
            "let's talk about",
            "change the subject",
            "different question",
            "something else",
            "what's the weather",  # Common context switch example
            "tell me a joke",      # Another common context switch
        ]
        
        input_lower = user_input.lower()
        for phrase in context_switch_phrases:
            if phrase in input_lower:
                return True
        
        # If we're collecting parameters and user asks something completely unrelated
        current_tool = self.get_current_tool()
        if current_tool == "collect_tool_parameters":
            # Use simple heuristics - if the question doesn't look like a parameter value
            if len(user_input.split()) > 5:  # Longer questions are likely new requests
                return True
            if user_input.endswith('?'):  # Questions are likely new requests
                return True
        
        return False
    
    def handle_empty_response(self) -> Optional[str]:
        """
        Handle empty user response during tool workflow.
        Returns None if continuing, or a message if cancelled.
        """
        if not self.stack:
            return None
        
        response = Prompt.ask("Continue with current task? [Y/n]", default="y")
        if response.lower() != 'y':
            self.clear()
            return "Tool workflow cancelled."
        
        return None
    
    def process_tool_result(self, tool_name: str, result: Dict[str, Any], success: bool) -> None:
        """Process a tool result and update stack accordingly"""
        # Add missing import
        import os
        import json
        from rich.console import Console
        console = Console()
        
        # Get debug mode from environment variable
        debug_mode = os.environ.get('TACO_DEBUG_LEVEL', 'INFO').upper() in ['DEBUG', 'VERBOSE']
        
        if debug_mode:
            console.print(f"[magenta]DEBUG STACK: Processing result for tool: {tool_name}[/magenta]")
            console.print(f"[magenta]DEBUG STACK: Success: {success}[/magenta]")
            if isinstance(result, dict):
                console.print(f"[magenta]DEBUG STACK: Result status: {result.get('status', 'N/A')}[/magenta]")
                if 'next_tool' in result:
                    console.print(f"[magenta]DEBUG STACK: Next tool: {result['next_tool']}[/magenta]")
        
        if not success:
            # Tool failed - clear the stack
            console.print(f"[red]Tool {tool_name} failed. Clearing tool stack.[/red]")
            self.clear()
            return
        
        if isinstance(result, dict):
            # Check if this is a get_usage_instructions call
            if result.get('status') == 'success' and 'instructions' in result:
                # Tool is starting - push to stack
                self.push(tool_name, {'status': 'initializing'})
                
                if debug_mode:
                    console.print(f"[magenta]DEBUG STACK: Pushed {tool_name} to stack after instructions[/magenta]")
                    console.print(f"[magenta]DEBUG STACK: Stack size: {len(self.stack)}[/magenta]")
            
            # Check if tool needs another tool
            if result.get('next_tool'):
                next_tool = result['next_tool']
                self.push(next_tool, result.get('context', {}))
                
                if debug_mode:
                    console.print(f"[magenta]DEBUG STACK: Pushed next tool {next_tool} to stack[/magenta]")
                    console.print(f"[magenta]DEBUG STACK: Stack size: {len(self.stack)}[/magenta]")
            
            # Check if tool is complete
            if result.get('status') == 'complete':
                popped = self.pop()
                
                if debug_mode:
                    console.print(f"[magenta]DEBUG STACK: Popped {popped['tool'] if popped else 'None'} from stack[/magenta]")
                    console.print(f"[magenta]DEBUG STACK: Stack size: {len(self.stack)}[/magenta]")
