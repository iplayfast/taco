"""
TACO Parameter Collector Tool - Helps collect parameters for tools interactively
"""
from typing import Dict, Any, List

def collect_tool_parameters(tool_name: str) -> Dict[str, Any]:
    """
    Create a user-friendly prompt to collect parameters for a specific tool
    
    Args:
        tool_name: Name of the tool to collect parameters for
    
    Returns:
        Dict containing user-friendly prompts for parameter collection
    """
    # Create user-friendly prompts based on the tool
    if tool_name == "calculate_mortgage":
        return {
            "tool_name": tool_name,
            "message": "To calculate your mortgage, I'll need the following information:\n\n" +
                      "1. **Loan Amount**: How much do you want to borrow? (e.g., 300000 for $300,000)\n" +
                      "2. **Interest Rate**: What's the annual interest rate? (e.g., 5.5 for 5.5%)\n" +
                      "3. **Loan Term**: How many years is the loan for? (e.g., 30 for a 30-year mortgage)\n\n" +
                      "Please provide these values and I'll calculate your monthly payment.",
            "next_action": "waiting_for_user_input"
        }
    
    elif tool_name == "calculate_compound_interest":
        return {
            "tool_name": tool_name,
            "message": "To calculate compound interest, I'll need:\n\n" +
                      "1. **Initial Investment**: How much are you investing? (e.g., 10000 for $10,000)\n" +
                      "2. **Interest Rate**: What's the annual rate as a decimal? (e.g., 0.05 for 5%)\n" +
                      "3. **Investment Period**: How many years will you invest?\n" +
                      "4. **Compounding Frequency**: How often is interest compounded per year? (e.g., 12 for monthly)\n\n" +
                      "Please provide these values.",
            "next_action": "waiting_for_user_input"
        }
    
    elif tool_name == "convert_temperature":
        return {
            "tool_name": tool_name,
            "message": "To convert a temperature, I need:\n\n" +
                      "1. **Temperature Value**: What temperature do you want to convert?\n" +
                      "2. **From Unit**: What unit are you converting from? (C, F, or K)\n" +
                      "3. **To Unit**: What unit do you want to convert to? (C, F, or K)\n\n" +
                      "Please provide these values.",
            "next_action": "waiting_for_user_input"
        }
    
    else:
        # Generic response for unknown tools
        return {
            "tool_name": tool_name,
            "message": f"To use {tool_name}, please provide the required parameters.",
            "next_action": "waiting_for_user_input"
        }

def parse_user_parameters(user_input: str, tool_name: str) -> Dict[str, Any]:
    """
    Parse user input to extract parameters for a tool
    
    Args:
        user_input: The user's response with parameter values
        tool_name: Name of the tool these parameters are for
    
    Returns:
        Dict containing parsed parameters or instructions for clarification
    """
    # This is a simplified parser - in a real implementation,
    # you might want to use NLP or more sophisticated parsing
    
    # Try to extract numbers from the input
    import re
    numbers = re.findall(r'-?\d+\.?\d*', user_input)
    
    if tool_name == "calculate_mortgage" and len(numbers) >= 3:
        return {
            "parsed_parameters": {
                "principal": float(numbers[0]),
                "annual_rate": float(numbers[1]),
                "years": int(float(numbers[2]))
            },
            "ready_to_execute": True
        }
    
    elif tool_name == "calculate_compound_interest" and len(numbers) >= 4:
        return {
            "parsed_parameters": {
                "principal": float(numbers[0]),
                "rate": float(numbers[1]),
                "time": float(numbers[2]),
                "compounds_per_year": int(float(numbers[3]))
            },
            "ready_to_execute": True
        }
    
    elif tool_name == "convert_temperature":
        # Look for temperature units
        units = re.findall(r'[CFK]', user_input.upper())
        if len(numbers) >= 1 and len(units) >= 2:
            return {
                "parsed_parameters": {
                    "value": float(numbers[0]),
                    "from_unit": units[0],
                    "to_unit": units[1]
                },
                "ready_to_execute": True
            }
    
    # If we couldn't parse the parameters, ask for clarification
    return {
        "error": "I couldn't understand all the parameters from your input.",
        "suggestion": "Please provide the values in order, separated by spaces or commas.",
        "ready_to_execute": False
    }

def format_tool_result_for_user(tool_name: str, result: Dict[str, Any]) -> str:
    """
    Format tool execution results in a user-friendly way
    
    Args:
        tool_name: Name of the tool that was executed
        result: The result from the tool execution
    
    Returns:
        User-friendly formatted result
    """
    if tool_name == "calculate_mortgage":
        return f"""Here are your mortgage calculation results:

• **Monthly Payment**: ${result.get('monthly_payment', 0):,.2f}
• **Total Payment**: ${result.get('total_payment', 0):,.2f}
• **Total Interest**: ${result.get('total_interest', 0):,.2f}

This calculation assumes a fixed interest rate over the entire loan term."""
    
    elif tool_name == "calculate_compound_interest":
        return f"""Here are your compound interest calculation results:

• **Final Amount**: ${result.get('final_amount', 0):,.2f}
• **Interest Earned**: ${result.get('interest_earned', 0):,.2f}

Your investment will grow from the initial amount to the final amount over the specified period."""
    
    elif tool_name == "convert_temperature":
        return f"The converted temperature is: {result}"
    
    else:
        # Generic formatting
        formatted = f"Results from {tool_name}:\n\n"
        for key, value in result.items():
            formatted += f"• **{key}**: {value}\n"
        return formatted