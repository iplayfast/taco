"""
TACO Message Handler
Handles parsing, cleaning, and formatting of messages and tool calls.
"""
import json
import re
from typing import Any, Dict, List

class MessageHandler:
    """Handles message processing, parsing, and formatting"""
    
    def __init__(self):
        """Initialize the message handler"""
        # Unicode replacements for common problematic characters
        self.unicode_replacements = {
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
    
    def parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
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
    
    def clean_response_content(self, content: str) -> str:
        """Clean up response content for display"""
        # Handle the Message object format
        if isinstance(content, str) and content.startswith("model=") and "message=Message(" in content:
            # Look for content with single or double quotes
            match = re.search(r'content=(["\'])(.*?)\1(?:,\s*images=|$)', content, re.DOTALL)
            if match:
                actual_content = match.group(2)
                content = actual_content.strip()
        
        # For all string content, fix Unicode issues
        if isinstance(content, str):
            # Apply all replacements
            for unicode_char, replacement in self.unicode_replacements.items():
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
    
    def format_json_for_display(self, data: Any, indent: int = 0) -> str:
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
                    formatted_value = self.format_json_for_display(value, indent + 1)
                    lines.append(f'{spaces}  "{key}": {formatted_value}{comma}')
            lines.append(f"{spaces}}}")
            return "\n".join(lines)
        elif isinstance(data, list):
            if not data:
                return "[]"
            lines = ["["]
            for i, item in enumerate(data):
                comma = "," if i < len(data) - 1 else ""
                formatted_item = self.format_json_for_display(item, indent + 1)
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
    
    def format_for_panel(self, content: str, max_width: int = 80) -> str:
        """Format content for display in a panel with proper line wrapping"""
        # Clean up the content first
        cleaned = self.clean_response_content(content)
        
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
    
    def format_tool_results(self, results: List[Dict[str, Any]]) -> str:
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
                formatted_json = self.format_json_for_display(r['result'])
                formatted_results += f"```\n{formatted_json}\n```\n"
        
        return formatted_results
    
    def strip_tool_calls_from_response(self, response: str, tool_calls: List[Dict[str, Any]]) -> str:
        """Remove tool call blocks from the response"""
        result = response
        for call in tool_calls:
            result = result.replace(call['original_text'], '')
        return result.strip()