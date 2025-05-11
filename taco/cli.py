#!/usr/bin/env python3
"""
TACO - Tool And Context Orchestrator
Main CLI entry point
"""

import sys
import os
from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from taco.core.config import get_config
from taco.core.chat import ChatSession
from taco.core.model import ModelManager
from taco.tools.registry import ToolRegistry
from taco.context.engine import ContextManager
from taco.utils.display import display_logo, format_tool_output

# Create Typer app
app = typer.Typer(help="TACO - Tool And Context Orchestrator")
console = Console()

# Sub-commands
model_app = typer.Typer(help="Model management commands")
tools_app = typer.Typer(help="Tool management commands")
context_app = typer.Typer(help="Context management commands")
config_app = typer.Typer(help="Configuration management commands")

app.add_typer(model_app, name="model")
app.add_typer(tools_app, name="tools")
app.add_typer(context_app, name="context")
app.add_typer(config_app, name="config")

# Main command
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool = typer.Option(False, "--version", "-v", help="Show version and exit")):
    """
    TACO - Tool And Context Orchestrator
    """
    if version:
        from taco import __version__
        console.print(f"TACO version {__version__}")
        raise typer.Exit()
    
    if ctx.invoked_subcommand is None:
        # If no subcommand, enter interactive chat mode
        display_logo()
        chat_session = ChatSession()
        chat_session.start_interactive()

# Chat command
@app.command("chat")
def chat(
    save: Optional[str] = typer.Option(None, "--save", help="Save chat to file"),
    load: Optional[str] = typer.Option(None, "--load", help="Load chat from file"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use")
):
    """Start interactive chat session"""
    display_logo()
    chat_session = ChatSession(model_name=model)
    
    if load:
        chat_session.load_history(load)
        console.print(f"Loaded chat history from {load}")
    
    chat_session.start_interactive(save_path=save)

# Direct query command (default command when string argument is provided)
@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    json: bool = typer.Option(False, "--json", "-j", help="Output in JSON format")
):
    """Ask a single question and exit"""
    chat_session = ChatSession(model_name=model)
    response = chat_session.ask(question)
    
    if json:
        import json as json_lib
        console.print(json_lib.dumps({"question": question, "answer": response}))
    else:
        console.print(response)

# Model commands
@model_app.command("list")
def model_list():
    """List available models"""
    model_manager = ModelManager()
    models = model_manager.list_models()
    
    console.print(Panel("[bold]Available Models[/bold]"))
    for model in models:
        console.print(f"• {model['name']} - {model['description']}")

@model_app.command("use")
def model_use(model_name: str):
    """Select a model to use"""
    model_manager = ModelManager()
    result = model_manager.set_default_model(model_name)
    
    if result:
        console.print(f"[green]Now using model: {model_name}[/green]")
    else:
        console.print(f"[red]Error: Model '{model_name}' not found[/red]")

@model_app.command("info")
def model_info(model_name: str):
    """Show information about a model"""
    model_manager = ModelManager()
    info = model_manager.get_model_info(model_name)
    
    if info:
        console.print(Panel(f"[bold]{model_name}[/bold]"))
        for key, value in info.items():
            console.print(f"{key}: {value}")
    else:
        console.print(f"[red]Error: Model '{model_name}' not found[/red]")

# Tool commands
@tools_app.command("list")
def tools_list():
    """List available tools"""
    registry = ToolRegistry()
    tools = registry.list_tools()
    
    console.print(Panel("[bold]Available Tools[/bold]"))
    for tool in tools:
        console.print(f"• {tool['name']} - {tool['description']}")

@tools_app.command("add")
def tools_add(file_path: str):
    """Add a new tool from a Python file"""
    registry = ToolRegistry()
    result = registry.add_tool_file(file_path)
    
    if result['success']:
        console.print(f"[green]Added {len(result['tools'])} tools from {file_path}[/green]")
        for tool in result['tools']:
            console.print(f"• {tool}")
    else:
        console.print(f"[red]Error: {result['error']}[/red]")

@tools_app.command("run")
def tools_run(tool_name: str, args: List[str] = typer.Argument(None)):
    """Run a tool with arguments"""
    registry = ToolRegistry()
    result = registry.run_tool(tool_name, args)
    
    console.print(format_tool_output(tool_name, result))

@tools_app.command("help")
def tools_help(tool_name: str):
    """Show help for a specific tool"""
    registry = ToolRegistry()
    tool_info = registry.get_tool_info(tool_name)
    
    if tool_info:
        console.print(Panel(f"[bold]{tool_name}[/bold]"))
        console.print(f"Description: {tool_info['description']}")
        console.print("\nParameters:")
        for param in tool_info['parameters']:
            console.print(f"• {param['name']}: {param['type']} - {param['description']}")
    else:
        console.print(f"[red]Error: Tool '{tool_name}' not found[/red]")

# Context commands
@context_app.command("list")
def context_list():
    """List available contexts"""
    manager = ContextManager()
    contexts = manager.list_contexts()
    
    console.print(Panel("[bold]Available Contexts[/bold]"))
    for ctx in contexts:
        console.print(f"• {ctx['name']} - {ctx['description']}")

@context_app.command("use")
def context_use(context_name: str):
    """Set active context"""
    manager = ContextManager()
    result = manager.set_active_context(context_name)
    
    if result:
        console.print(f"[green]Now using context: {context_name}[/green]")
    else:
        console.print(f"[red]Error: Context '{context_name}' not found[/red]")

@context_app.command("create")
def context_create(name: str, template_str: str = None):
    """Create a new context template"""
    manager = ContextManager()
    
    # If no template string provided, read from stdin
    if not template_str and not sys.stdin.isatty():
        template_str = sys.stdin.read()
    
    if not template_str:
        console.print("[red]Error: No template provided[/red]")
        return
    
    result = manager.create_context(name, template_str)
    
    if result:
        console.print(f"[green]Created context template: {name}[/green]")
    else:
        console.print(f"[red]Error: Could not create context '{name}'[/red]")

@context_app.command("add")
def context_add(name: str, content: str = None):
    """Add content to context"""
    manager = ContextManager()
    
    # If no content provided, read from stdin
    if not content and not sys.stdin.isatty():
        content = sys.stdin.read()
    
    if not content:
        console.print("[red]Error: No content provided[/red]")
        return
    
    result = manager.add_to_context(name, content)
    
    if result:
        console.print(f"[green]Added content to context: {name}[/green]")
    else:
        console.print(f"[red]Error: Could not add to context '{name}'[/red]")

# Config commands
@config_app.command("list")
def config_list():
    """List current configuration"""
    config = get_config()
    
    console.print(Panel("[bold]Current Configuration[/bold]"))
    for section, values in config.items():
        console.print(f"[bold]{section}[/bold]:")
        for key, value in values.items():
            console.print(f"  {key} = {value}")

@config_app.command("set")
def config_set(key: str, value: str):
    """Set a configuration value"""
    from taco.core.config import set_config_value
    
    result = set_config_value(key, value)
    
    if result:
        console.print(f"[green]Set {key} = {value}[/green]")
    else:
        console.print(f"[red]Error: Could not set {key}[/red]")

# Create command
@app.command("create")
def create(
    prompt: str = typer.Argument(..., help="Code generation prompt"),
    workingdir: Optional[str] = typer.Option(None, "--workingdir", "-w", help="Working directory"),
    requirements: Optional[str] = typer.Option(None, "--requirements", "-r", help="Requirements file name"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Automatically confirm")
):
    """Create code based on a prompt - shows configuration before generating"""
    registry = ToolRegistry()
    
    # Prepare arguments
    args = [prompt]
    
    # Add optional arguments if provided
    args.append(workingdir or "")  # Use empty string for default
    args.append(requirements or "")  # Use empty string for default
    args.append(model or "")  # Use empty string for default
    
    # Handle confirmation
    if yes:
        args.append("Y")
        # Run the tool with confirmation
        result = registry.run_tool("create_code", args)
    else:
        # First call with N to show config
        args.append("N")
        result = registry.run_tool("create_code", args)
        
        if isinstance(result, dict) and result.get("status") == "cancelled":
            console.print(result.get("message", ""))
            confirm = typer.confirm("Do you want to proceed with these settings?")
            if confirm:
                # Run again with Y
                args[-1] = "Y"  # Replace the last argument
                result = registry.run_tool("create_code", args)
            else:
                console.print("[yellow]Code generation cancelled[/yellow]")
                return
    
    # Display results
    if isinstance(result, dict):
        if result.get("status") == "success":
            console.print(f"[green]{result['message']}[/green]")
            console.print("\nGenerated files:")
            if "files" in result:
                console.print(f"  • Output: {result['files'].get('output', 'None')}")
                code_files = result['files'].get('code_files', [])
                if code_files:
                    for file in code_files:
                        console.print(f"  • Code: {file}")
        elif result.get("status") == "error":
            console.print(f"[red]Error: {result.get('message', 'Unknown error')}[/red]")
        else:
            console.print(format_tool_output("create_code", result))
    else:
        console.print(format_tool_output("create_code", result))

if __name__ == "__main__":
    app()