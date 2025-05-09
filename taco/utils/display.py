"""
TACO Display Utilities
"""
import os
import sys
import time
from typing import Dict, Any, List, Generator, ContextManager
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_logo():
    """Display the TACO logo"""
    # Get logo path
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(script_dir, 'docs', 'taco_logo.ascii')
    
    # Display logo if it exists
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'r') as f:
                logo = f.read()
            console.print(Panel(logo, style="green"))
        except Exception:
            # Fallback if file can't be read
            console.print(Panel("TACO - Tool And Context Orchestrator", style="green"))
    else:
        # Hardcoded logo as fallback
        logo = """
 _____  _    ____ ___  
|_   _|/ \  / ___/ _ \ 
  | | / _ \| |  | | | |
  | |/ ___ \ |__| |_| |
  |_/_/   \_\____\___/ 
                       
Tool And Context Orchestrator
"""
        console.print(Panel(logo, style="green"))

def format_tool_output(tool_name: str, result: Any) -> str:
    """Format tool output for display"""
    if isinstance(result, dict):
        if "error" in result:
            return f"[red]Error running {tool_name}:[/red] {result['error']}"
        
        # Format dictionary nicely
        output = f"[green]Tool {tool_name} result:[/green]\n"
        for key, value in result.items():
            output += f"  [bold]{key}:[/bold] {value}\n"
        return output
    
    # Default formatting
    return f"[green]Tool {tool_name} result:[/green] {result}"

def display_system_message(message: str):
    """Display a system message"""
    console.print(f"[blue]System:[/blue] {message}")

@contextmanager
def display_thinking() -> Generator[None, None, None]:
    """Context manager to display a thinking animation"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[blue]Thinking...[/blue]"),
        transient=True,
    ) as progress:
        task = progress.add_task("thinking", total=None)
        try:
            yield
        finally:
            progress.update(task, completed=True)
