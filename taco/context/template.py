"""
TACO Context Template Management
"""
import re
from typing import Dict, Any

class ContextTemplate:
    """Manages context templates and their variables"""
    
    def __init__(self, template: str, variables: Dict[str, str]):
        """Initialize a context template"""
        self.template = template
        self.variables = variables
    
    def generate(self) -> str:
        """Generate context by filling in template variables"""
        result = self.template
        
        # Replace variables
        for key, value in self.variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        
        # Replace any remaining placeholders with empty strings
        result = re.sub(r'\{[^}]+\}', '', result)
        
        return result
