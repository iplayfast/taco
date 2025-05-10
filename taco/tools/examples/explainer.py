"""
TACO Explainer Tool - Explains parameters needed for tools
"""
import json
from typing import Dict, Any, List
from taco.tools.registry import ToolRegistry

def explain_tool(tool_name: str) -> Dict[str, Any]:
    """
    Explain what parameters are needed for a specific tool
    
    Args:
        tool_name: Name of the tool to explain
    
    Returns:
        Dict containing explanation of the tool and its parameters
    """
    registry = ToolRegistry()
    tool_info = registry.get_tool_info(tool_name)
    
    if not tool_info:
        return {
            "error": f"Tool '{tool_name}' not found",
            "available_tools": [tool['name'] for tool in registry.list_tools()]
        }
    
    # Build explanation
    explanation = {
        "tool_name": tool_info['name'],
        "description": tool_info['description'],
        "parameters": []
    }
    
    # Add parameter details
    for param in tool_info['parameters']:
        param_detail = {
            "name": param['name'],
            "type": param['type'],
            "description": param['description'],
            "required": param.get('required', False)
        }
        explanation["parameters"].append(param_detail)
    
    # Add example usage with JSON format for the LLM
    example_params = {}
    for param in tool_info['parameters']:
        if param['type'] == 'number':
            if 'rate' in param['name'].lower():
                example_params[param['name']] = 5.5
            elif 'principal' in param['name'].lower():
                example_params[param['name']] = 300000
            elif 'years' in param['name'].lower() or 'term' in param['name'].lower():
                example_params[param['name']] = 30
            elif 'compounds' in param['name'].lower():
                example_params[param['name']] = 12
            else:
                example_params[param['name']] = 100
        elif param['type'] == 'string':
            if 'unit' in param['name'].lower():
                example_params[param['name']] = "C"
            else:
                example_params[param['name']] = f"example_{param['name']}"
        elif param['type'] == 'boolean':
            example_params[param['name']] = True
        else:
            example_params[param['name']] = f"<{param['name']}>"
    
    # Show how to call this tool in JSON format
    explanation["example_json_call"] = {
        "tool_call": {
            "name": tool_name,
            "parameters": example_params
        }
    }
    
    # Also show manual command format
    param_names = [p['name'] for p in tool_info['parameters']]
    example_args = []
    for param in tool_info['parameters']:
        example_args.append(str(example_params[param['name']]))
    
    explanation["manual_command"] = f"/tools run {tool_name} " + " ".join(example_args)
    
    return explanation

def explain_tools_for_request(request: str) -> Dict[str, Any]:
    """
    Suggest tools that might be useful for a given request and explain their parameters
    
    Args:
        request: User's request or question
    
    Returns:
        Dict containing suggested tools and their parameter explanations
    """
    registry = ToolRegistry()
    all_tools = registry.list_tools()
    
    # Simple keyword matching for tool suggestions
    request_lower = request.lower()
    suggested_tools = []
    
    # Keywords for different tools
    tool_keywords = {
        "calculate_mortgage": ["mortgage", "loan", "payment", "house", "home loan", "monthly payment", "home buying"],
        "calculate_compound_interest": ["interest", "investment", "compound", "savings", "return", "growth"],
        "convert_temperature": ["temperature", "celsius", "fahrenheit", "kelvin", "convert", "degrees", "°"],
        "analyze_text": ["analyze", "text", "word count", "statistics", "length", "sentences"],
        "run_python": ["python", "code", "execute", "run code", "script", "programming"],
        "check_code": ["check", "validate", "code", "syntax", "error", "debug"],
        "explain_tool": ["explain", "help", "parameters", "how to use", "what parameters"],
        "explain_tools_for_request": ["what tool", "which tool", "find tool", "help me find"]
    }
    
    # Find matching tools
    for tool_name, keywords in tool_keywords.items():
        if any(keyword in request_lower for keyword in keywords):
            # Check if tool exists
            if any(tool['name'] == tool_name for tool in all_tools):
                tool_explanation = explain_tool(tool_name)
                if 'error' not in tool_explanation:
                    suggested_tools.append(tool_explanation)
    
    result = {
        "request": request,
        "suggested_tools": suggested_tools,
        "total_tools_available": len(all_tools)
    }
    
    if not suggested_tools:
        result["message"] = "No specific tools found for this request. Here's how to explore available tools:"
        result["suggestions"] = [
            "Use '/list tools' to see all available tools",
            "Use 'explain_tool <tool_name>' to learn about a specific tool",
            "Try rephrasing your request with more specific keywords"
        ]
    else:
        result["message"] = f"Found {len(suggested_tools)} tools that might help with your request."
    
    return result

def what_can_you_calculate() -> Dict[str, Any]:
    """
    Show all calculation and analysis tools available
    
    Returns:
        Dict containing all available calculation tools
    """
    registry = ToolRegistry()
    all_tools = registry.list_tools()
    
    calculation_tools = []
    analysis_tools = []
    code_tools = []
    utility_tools = []
    
    for tool in all_tools:
        tool_name = tool['name']
        if 'calculate' in tool_name or 'convert' in tool_name:
            calculation_tools.append(tool)
        elif 'analyze' in tool_name or 'explain' in tool_name:
            analysis_tools.append(tool)
        elif 'code' in tool_name or 'python' in tool_name:
            code_tools.append(tool)
        else:
            utility_tools.append(tool)
    
    return {
        "calculation_tools": calculation_tools,
        "analysis_tools": analysis_tools,
        "code_tools": code_tools,
        "utility_tools": utility_tools,
        "total_tools": len(all_tools),
        "message": "Here are all the tools I can use to help you:"
    }

def help_with_tool_usage() -> str:
    """
    Provide general help on how to use tools in TACO
    
    Returns:
        Help text for tool usage
    """
    return """
TACO Tool Usage Guide:

1. List all available tools:
   /list tools

2. Understand what a tool does:
   Use explain_tool to see parameters and examples

3. The AI can automatically use tools!
   Just ask naturally, like:
   - "Can you calculate a mortgage for me?"
   - "What's 32°F in Celsius?"
   - "Analyze this text: [your text]"

4. Manual tool usage:
   /tools run <tool_name> <arg1> <arg2> ...

5. Find tools for your task:
   Ask: "What tools can help me with [your task]?"

The AI will automatically choose and use the right tools to answer your questions!
"""

def format_tool_parameters_help(tool_name: str) -> str:
    """
    Format a user-friendly explanation of tool parameters
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Formatted string explaining the parameters
    """
    explanation = explain_tool(tool_name)
    
    if 'error' in explanation:
        return f"Tool '{tool_name}' not found. Available tools: {', '.join(explanation['available_tools'])}"
    
    result = f"**{tool_name}**\n"
    result += f"{explanation['description']}\n\n"
    result += "**Parameters needed:**\n"
    
    for param in explanation['parameters']:
        result += f"- **{param['name']}** ({param['type']}): {param['description']}"
        if param['required']:
            result += " [REQUIRED]"
        result += "\n"
    
    result += f"\n**Example usage:**\n"
    result += f"```json\n{json.dumps(explanation['example_json_call'], indent=2)}\n```"
    
    return result