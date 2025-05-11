"""
TACO Parameter Collection Tool
"""
from typing import Dict, Any, List
import sys

def collect_tool_parameters(tool_name: str, questions: List[str]) -> Dict[str, Any]:
    """
    Collect parameters for a tool by asking the user questions.
    
    Args:
        tool_name: Name of the tool we're collecting parameters for
        questions: List of questions to ask the user
    
    Returns:
        Dict containing the collected parameters
    """
    from rich.console import Console
    from rich.prompt import Prompt
    from taco.utils.debug import debug_print
    
    console = Console()
    
    debug_print(f"Starting parameter collection for tool: {tool_name}")
    debug_print(f"Questions to ask: {questions}")
    
    console.print(f"\n[bold blue]I need some information to calculate your {tool_name.replace('_', ' ')}:[/bold blue]")
    
    # Map tool names to expected parameter names
    param_mappings = {
        "calculate_mortgage": ["principal", "annual_rate", "years"],
        "calculate_compound_interest": ["principal", "rate", "time", "compounds_per_year"],
        "convert_temperature": ["value", "from_unit", "to_unit"],
        "analyze_text": ["text"]
    }
    
    parameters = {}
    param_names = param_mappings.get(tool_name, [f"param_{i}" for i in range(len(questions))])
    
    for i, question in enumerate(questions):
        # Ensure we're asking the actual question, not just "W:"
        if not question or question.strip() == "W:":
            debug_print(f"Invalid question detected: '{question}'")
            # Provide default questions based on tool
            if tool_name == "calculate_mortgage":
                default_questions = [
                    "What is the loan amount (principal) in dollars?",
                    "What is the annual interest rate (as a percentage, e.g., 5.5)?",
                    "How many years is the loan term?"
                ]
                if i < len(default_questions):
                    question = default_questions[i]
                else:
                    question = f"Please enter parameter {i+1}:"
            else:
                question = f"Please enter value for {param_names[i] if i < len(param_names) else f'parameter {i+1}'}:"
        
        # Ask the user with a meaningful prompt
        debug_print(f"Asking question {i+1}: {question}")
        answer = Prompt.ask(f"\n[yellow]{question}[/yellow]")
        debug_print(f"User answered: {answer}")
        
        # Determine parameter name
        if i < len(param_names):
            param_name = param_names[i]
        else:
            param_name = f"param_{i}"
        
        # Try to convert to appropriate type
        try:
            # Handle percentage inputs
            if "rate" in param_name.lower() or "interest" in question.lower():
                # Allow both decimal and percentage inputs
                if "%" in answer:
                    value = float(answer.strip("%"))
                else:
                    value = float(answer)
                parameters[param_name] = value
            elif '.' in answer:
                parameters[param_name] = float(answer)
            else:
                parameters[param_name] = int(answer)
        except ValueError:
            # If not a number, keep as string
            parameters[param_name] = answer
        
        debug_print(f"Set parameter {param_name} = {parameters[param_name]}")
    
    debug_print(f"Collected parameters: {parameters}")
    return parameters